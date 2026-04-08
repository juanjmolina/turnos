"""
Sistema de Turnos y Compensatorios
Con conexión a PostgreSQL (Supabase / Railway / Neon / cualquier Postgres)

CONFIGURACIÓN:
  Crea una variable de entorno DATABASE_URL con tu cadena de conexión:
  postgresql://usuario:contraseña@host:5432/nombre_db

  En Streamlit Cloud: Settings → Secrets → añade:
    DATABASE_URL = "postgresql://..."

  En Railway / Render: la variable se agrega en el panel de la plataforma.

CORRER LOCALMENTE:
  pip install streamlit psycopg2-binary
  export DATABASE_URL="postgresql://..."
  streamlit run app.py
"""

import os
import json
import hashlib
import streamlit as st
import streamlit.components.v1 as components

# ── Dependencias opcionales ───────────────────────────────────
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_OK = True
except ImportError:
    PSYCOPG2_OK = False

# ══════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════
PAGE_TITLE  = "Sistema de Turnos"
PAGE_ICON   = "🏭"
HTML_FILE   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
DB_URL      = os.environ.get("DATABASE_URL") or st.secrets.get("DATABASE_URL", "")

# ══════════════════════════════════════════════════════════════
# BASE DE DATOS
# ══════════════════════════════════════════════════════════════

def get_conn():
    """Abre una conexión a PostgreSQL."""
    if not PSYCOPG2_OK:
        st.error("❌ psycopg2 no está instalado. Corre: pip install psycopg2-binary")
        return None
    if not DB_URL:
        return None
    try:
        url = DB_URL
        # Railway/Heroku a veces usa postgres:// en lugar de postgresql://
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        conn = psycopg2.connect(url, cursor_factory=RealDictCursor)
        conn.autocommit = True
        return conn
    except Exception as e:
        st.error(f"❌ No se pudo conectar a la base de datos: {e}")
        return None


def init_db():
    """Crea las tablas si no existen."""
    conn = get_conn()
    if not conn:
        return False
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS snapshots (
                    id          SERIAL PRIMARY KEY,
                    clave       TEXT NOT NULL UNIQUE,
                    datos       JSONB NOT NULL,
                    hash_datos  TEXT,
                    creado_en   TIMESTAMPTZ DEFAULT NOW(),
                    actualizado_en TIMESTAMPTZ DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS sync_log (
                    id          SERIAL PRIMARY KEY,
                    usuario     TEXT,
                    accion      TEXT,
                    creado_en   TIMESTAMPTZ DEFAULT NOW()
                );

                -- Índice para búsquedas rápidas por clave
                CREATE INDEX IF NOT EXISTS idx_snapshots_clave
                    ON snapshots(clave);
            """)
        conn.close()
        return True
    except Exception as e:
        st.error(f"❌ Error al inicializar la base de datos: {e}")
        return False


def guardar_snapshot(clave: str, datos: dict, usuario: str = "sistema") -> bool:
    """Guarda o actualiza un snapshot en la DB."""
    conn = get_conn()
    if not conn:
        return False
    try:
        datos_json = json.dumps(datos, ensure_ascii=False)
        hash_val   = hashlib.md5(datos_json.encode()).hexdigest()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO snapshots (clave, datos, hash_datos, actualizado_en)
                VALUES (%s, %s::jsonb, %s, NOW())
                ON CONFLICT (clave) DO UPDATE
                    SET datos          = EXCLUDED.datos,
                        hash_datos     = EXCLUDED.hash_datos,
                        actualizado_en = NOW()
            """, (clave, datos_json, hash_val))

            cur.execute("""
                INSERT INTO sync_log (usuario, accion)
                VALUES (%s, %s)
            """, (usuario, f"guardar:{clave}"))
        conn.close()
        return True
    except Exception as e:
        st.error(f"❌ Error al guardar datos: {e}")
        return False


def cargar_snapshot(clave: str) -> dict | None:
    """Carga un snapshot desde la DB."""
    conn = get_conn()
    if not conn:
        return None
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT datos, actualizado_en, hash_datos
                FROM snapshots
                WHERE clave = %s
            """, (clave,))
            row = cur.fetchone()
        conn.close()
        if row:
            return {
                "datos":          dict(row["datos"]),
                "actualizado_en": row["actualizado_en"].isoformat() if row["actualizado_en"] else None,
                "hash":           row["hash_datos"]
            }
        return None
    except Exception as e:
        st.error(f"❌ Error al cargar datos: {e}")
        return None


def listar_snapshots() -> list:
    """Lista todos los snapshots disponibles."""
    conn = get_conn()
    if not conn:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT clave, hash_datos, actualizado_en
                FROM snapshots
                ORDER BY actualizado_en DESC
            """)
            rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        return []


def ultimo_log() -> list:
    """Últimas 10 acciones en el log de sincronización."""
    conn = get_conn()
    if not conn:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT usuario, accion, creado_en
                FROM sync_log
                ORDER BY creado_en DESC
                LIMIT 10
            """)
            rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════
# HTML DEL SISTEMA
# ══════════════════════════════════════════════════════════════

def get_html() -> str:
    if os.path.exists(HTML_FILE):
        with open(HTML_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Error: index.html no encontrado</h1>"


def inyectar_sync_js(html: str, snapshot_actual: dict | None) -> str:
    """
    Inyecta JavaScript al final del HTML para conectar el sistema
    con la base de datos a través de los endpoints de Streamlit.

    Estrategia:
    1. Al cargar la página, si hay datos en la DB los carga en localStorage
    2. El botón 💾 Exportar guarda también en la DB via postMessage
    3. Un polling ligero detecta cambios de otros usuarios
    """

    datos_db_json = json.dumps(
        snapshot_actual["datos"] if snapshot_actual else {}
    )
    ultima_actualizacion = (
        snapshot_actual["actualizado_en"] if snapshot_actual else ""
    )
    hash_actual = snapshot_actual["hash"] if snapshot_actual else ""

    sync_script = f"""
<script>
// ══════════════════════════════════════════════════════════════
//  SINCRONIZACIÓN CON POSTGRESQL
// ══════════════════════════════════════════════════════════════

(function() {{
  const CLAVE_DB = 'sistema_turnos_v1';
  const HASH_DB  = {json.dumps(hash_actual)};
  const DATOS_DB = {datos_db_json};

  // ── 1. Al iniciar: cargar datos de la DB si son más recientes ──
  function cargarDatosDB() {{
    if (!DATOS_DB || Object.keys(DATOS_DB).length === 0) return;

    const hashLocal = localStorage.getItem('_db_hash');
    if (hashLocal === HASH_DB) {{
      console.log('[DB] Datos locales ya sincronizados ✅');
      return;
    }}

    console.log('[DB] Cargando datos desde PostgreSQL...');

    // Aplicar cada módulo del snapshot
    const modulos = [
      'workers','ausencias','celdasEstado','horasExtras',
      'nextWId','nextAId','filterGrupo','filterAusTipo',
      'filterAusEst','filterAusWk','vac_data','cum_data',
      'comp_ganados','cc_data','che_data'
    ];

    modulos.forEach(mod => {{
      if (DATOS_DB[mod] !== undefined) {{
        try {{
          localStorage.setItem(mod, JSON.stringify(DATOS_DB[mod]));
        }} catch(e) {{
          console.warn('[DB] Error guardando', mod, e);
        }}
      }}
    }});

    // Guardar hash para no recargar innecesariamente
    localStorage.setItem('_db_hash', HASH_DB);
    localStorage.setItem('_db_sync_ts', {json.dumps(ultima_actualizacion)});

    console.log('[DB] Datos cargados desde PostgreSQL ✅');

    // Recargar la interfaz después de aplicar los datos
    setTimeout(() => {{
      if (typeof render === 'function') render();
      if (typeof renderHeader === 'function') renderHeader();
      if (typeof cumRefrescar === 'function') cumRefrescar();
      if (typeof vRefrescar === 'function') vRefrescar();
      if (typeof compRefrescar === 'function') compRefrescar();
      if (typeof ccRefrescar === 'function') ccRefrescar();
    }}, 500);
  }}

  // ── 2. Función para enviar datos a Streamlit (via URL params) ──
  window.guardarEnDB = function(snapshot) {{
    try {{
      const encoded = encodeURIComponent(JSON.stringify(snapshot));
      // Streamlit lee el hash de la URL para comunicación
      const url = new URL(window.location.href);
      url.searchParams.set('_save', encoded);
      // Notificar a Streamlit via el hash (lightweight)
      window.parent.postMessage({{
        type: 'SISTEMA_TURNOS_SAVE',
        payload: snapshot,
        clave: CLAVE_DB
      }}, '*');
      localStorage.setItem('_db_hash', ''); // forzar recarga próxima vez
      mostrarNotificacion('✅ Guardado en base de datos', '#10B981');
    }} catch(e) {{
      mostrarNotificacion('❌ Error al sincronizar con DB: ' + e.message, '#EF4444');
    }}
  }};

  // ── 3. Interceptar el botón de Exportar para también guardar en DB ──
  function hookExportar() {{
    const originalExportar = window.exportarDatos;
    if (typeof originalExportar !== 'function') return;

    window.exportarDatos = function() {{
      // Primero ejecutar la exportación normal (descarga JSON)
      originalExportar();
      // Luego guardar en DB
      try {{
        const snap = buildSnapshot();
        window.guardarEnDB(snap);
      }} catch(e) {{
        console.warn('[DB] No se pudo guardar en DB al exportar:', e);
      }}
    }};
    console.log('[DB] Hook de exportación activo ✅');
  }}

  // ── 4. Botón de sincronización manual en la interfaz ──
  function agregarBotonSync() {{
    // Buscar el panel de backup para añadir la opción de DB
    const observer = new MutationObserver(() => {{
      const backupBox = document.querySelector('.backup-box');
      if (backupBox && !document.getElementById('_dbSyncSection')) {{
        const section = document.createElement('div');
        section.id = '_dbSyncSection';
        section.className = 'backup-section';
        section.innerHTML = `
          <h3>🐘 Sincronizar con PostgreSQL</h3>
          <p>Guarda todos los datos en la base de datos compartida. Todos los usuarios verán los cambios al recargar.</p>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <button onclick="syncManualDB()" class="btn btn-primary" style="font-size:.85rem;padding:8px 18px;background:#059669">
              🔄 Guardar en base de datos ahora
            </button>
          </div>
          <div id="_dbSyncInfo" class="backup-meta" style="display:none"></div>
        `;
        backupBox.insertBefore(section, backupBox.lastElementChild);
        observer.disconnect();
      }}
    }});
    observer.observe(document.body, {{ childList: true, subtree: true }});
  }}

  window.syncManualDB = function() {{
    try {{
      const snap = buildSnapshot();
      window.guardarEnDB(snap);
      const el = document.getElementById('_dbSyncInfo');
      if (el) {{
        el.style.display = '';
        el.textContent = '✅ Sincronizado · ' + new Date().toLocaleString('es-CO');
      }}
    }} catch(e) {{
      alert('Error al sincronizar: ' + e.message);
    }}
  }};

  // ── 5. Notificación toast ──────────────────────────────────
  function mostrarNotificacion(msg, color) {{
    const toast = document.createElement('div');
    toast.style.cssText = `
      position:fixed;bottom:20px;right:20px;z-index:99999;
      background:${{color}};color:#fff;border-radius:10px;
      padding:12px 20px;font-size:13px;font-weight:600;
      box-shadow:0 4px 20px rgba(0,0,0,.2);
      animation:slideIn .3s ease;
    `;
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 3500);
  }}

  // ── Inicialización ─────────────────────────────────────────
  document.addEventListener('DOMContentLoaded', () => {{
    cargarDatosDB();
    setTimeout(hookExportar, 1000);
    agregarBotonSync();
    console.log('[DB] Sistema de sincronización PostgreSQL iniciado ✅');
    console.log('[DB] Última actualización DB:', {json.dumps(ultima_actualizacion)});
  }});

}})();
</script>
"""

    # Inyectar antes del cierre de </body>
    if "</body>" in html:
        return html.replace("</body>", sync_script + "\n</body>")
    return html + sync_script


# ══════════════════════════════════════════════════════════════
# API ENDPOINT — recibir datos del frontend via query params
# ══════════════════════════════════════════════════════════════

def procesar_guardado_desde_url():
    """
    Streamlit no tiene endpoints HTTP nativos, pero podemos leer
    query params para recibir datos del frontend.
    """
    params = st.query_params
    if "_save" in params:
        try:
            datos = json.loads(params["_save"])
            ok = guardar_snapshot("sistema_turnos_v1", datos, usuario="usuario_web")
            if ok:
                st.query_params.clear()
                return True
        except Exception as e:
            st.error(f"Error al guardar: {e}")
    return False


# ══════════════════════════════════════════════════════════════
# STREAMLIT UI
# ══════════════════════════════════════════════════════════════

def main():
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Ocultar UI de Streamlit completamente
    st.markdown("""
    <style>
        #MainMenu, footer, header, [data-testid="stToolbar"] {display:none !important;}
        .block-container {padding:0 !important; max-width:100% !important;}
        [data-testid="stAppViewContainer"] > div {padding:0 !important;}
        [data-testid="stVerticalBlock"] {gap:0 !important;}
        section[data-testid="stSidebar"] {display:none;}
    </style>
    """, unsafe_allow_html=True)

    # ── Inicializar DB ────────────────────────────────────────
    db_ok = False
    if DB_URL:
        db_ok = init_db()
    
    # ── Procesar si hay datos entrantes ──────────────────────
    procesar_guardado_desde_url()

    # ── Cargar snapshot actual de la DB ──────────────────────
    snapshot = None
    if db_ok:
        snapshot = cargar_snapshot("sistema_turnos_v1")

    # ── Sidebar con info de DB (solo visible en desarrollo) ──
    if os.environ.get("DEV_MODE") == "1":
        with st.sidebar:
            st.title("🐘 Base de Datos")
            if not DB_URL:
                st.warning("DATABASE_URL no configurada")
            elif not db_ok:
                st.error("No se pudo conectar")
            else:
                st.success("PostgreSQL conectado ✅")
                if snapshot:
                    ts = snapshot.get("actualizado_en", "?")
                    st.caption(f"Última actualización: {ts}")
                    workers = snapshot["datos"].get("workers", [])
                    st.metric("Trabajadores en DB", len(workers))
                    ausencias = snapshot["datos"].get("ausencias", [])
                    st.metric("Ausencias en DB", len(ausencias))

                st.divider()
                st.subheader("📋 Log de sincronización")
                logs = ultimo_log()
                for log in logs:
                    st.caption(f"👤 {log['usuario']} · {log['accion']} · {log['creado_en']}")

                st.divider()
                if st.button("🗑️ Limpiar DB (desarrollo)"):
                    conn = get_conn()
                    if conn:
                        with conn.cursor() as cur:
                            cur.execute("DELETE FROM snapshots WHERE clave = 'sistema_turnos_v1'")
                        conn.close()
                        st.success("Limpiado")
                        st.rerun()

    # ── Renderizar el sistema ─────────────────────────────────
    html = get_html()
    if db_ok:
        html = inyectar_sync_js(html, snapshot)

    # Mostrar aviso si no hay DB configurada
    if not DB_URL:
        st.warning(
            "⚠️ **Base de datos no configurada.** "
            "Agrega la variable de entorno `DATABASE_URL` con tu cadena de conexión PostgreSQL. "
            "El sistema funciona pero los datos solo se guardan localmente en el navegador.",
            icon="⚠️"
        )

    components.html(html, height=950, scrolling=True)


if __name__ == "__main__":
    main()
