"""
database/db.py — Capa de acceso a datos con SQLite.
Para migrar a PostgreSQL, reemplaza get_connection() y ajusta los
placeholders de ?  a  %s  (psycopg2).
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "db.sqlite3"

# ─────────────────────────────────────────────────────────────────────────────
# Conexión
# ─────────────────────────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Retorna una conexión a SQLite con row_factory configurado."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ─────────────────────────────────────────────────────────────────────────────
# Inicialización de tablas
# ─────────────────────────────────────────────────────────────────────────────

def init_db():
    """Crea las tablas si no existen e inserta datos de ejemplo."""
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS workers (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre  TEXT    NOT NULL,
            grupo   TEXT    NOT NULL CHECK(grupo IN ('A','B','C')),
            maquina TEXT    DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS ausencias (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id    INTEGER NOT NULL REFERENCES workers(id) ON DELETE CASCADE,
            tipo         TEXT    NOT NULL,
            fecha_inicio TEXT    NOT NULL,
            fecha_fin    TEXT    NOT NULL,
            estado       TEXT    NOT NULL DEFAULT 'Pendiente',
            observacion  TEXT    DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS celdas_estado (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id   INTEGER NOT NULL,
            week_offset INTEGER NOT NULL,
            day_index   INTEGER NOT NULL,
            tipo_aus    TEXT    NOT NULL,
            UNIQUE(worker_id, week_offset, day_index)
        );

        CREATE TABLE IF NOT EXISTS horas_extras (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            worker_id   INTEGER NOT NULL,
            week_iso    TEXT    NOT NULL,
            tipo_he     TEXT    NOT NULL,
            horas       REAL    NOT NULL DEFAULT 0,
            UNIQUE(worker_id, week_iso, tipo_he)
        );
    """)

    # Datos de ejemplo si workers está vacío
    count = cur.execute("SELECT COUNT(*) FROM workers").fetchone()[0]
    if count == 0:
        cur.executemany(
            "INSERT INTO workers (nombre, grupo, maquina) VALUES (?,?,?)",
            [
                ("Juan Pérez",    "A", ""),
                ("María López",   "B", ""),
                ("Carlos Gómez",  "C", ""),
                ("Ana Torres",    "A", ""),
                ("Luis Ramírez",  "B", ""),
            ],
        )

    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# WORKERS
# ─────────────────────────────────────────────────────────────────────────────

def get_workers() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM workers ORDER BY nombre").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_worker(nombre: str, grupo: str) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO workers (nombre, grupo, maquina) VALUES (?,?,?)",
        (nombre.strip(), grupo, ""),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_worker_grupo(worker_id: int, grupo: str):
    conn = get_connection()
    conn.execute("UPDATE workers SET grupo=? WHERE id=?", (grupo, worker_id))
    conn.commit()
    conn.close()


def update_worker_maquina(worker_id: int, maquina: str):
    conn = get_connection()
    conn.execute("UPDATE workers SET maquina=? WHERE id=?", (maquina, worker_id))
    conn.commit()
    conn.close()


def delete_worker(worker_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM workers WHERE id=?", (worker_id,))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# AUSENCIAS
# ─────────────────────────────────────────────────────────────────────────────

def get_ausencias() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM ausencias ORDER BY fecha_inicio DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_ausencia(worker_id: int, tipo: str, fecha_inicio: str,
                 fecha_fin: str, estado: str, observacion: str) -> int:
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO ausencias
           (worker_id, tipo, fecha_inicio, fecha_fin, estado, observacion)
           VALUES (?,?,?,?,?,?)""",
        (worker_id, tipo, fecha_inicio, fecha_fin, estado, observacion),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_ausencia(aus_id: int, worker_id: int, tipo: str,
                    fecha_inicio: str, fecha_fin: str,
                    estado: str, observacion: str):
    conn = get_connection()
    conn.execute(
        """UPDATE ausencias
           SET worker_id=?, tipo=?, fecha_inicio=?, fecha_fin=?,
               estado=?, observacion=?
           WHERE id=?""",
        (worker_id, tipo, fecha_inicio, fecha_fin, estado, observacion, aus_id),
    )
    conn.commit()
    conn.close()


def update_ausencia_estado(aus_id: int, estado: str):
    conn = get_connection()
    conn.execute("UPDATE ausencias SET estado=? WHERE id=?", (estado, aus_id))
    conn.commit()
    conn.close()


def delete_ausencia(aus_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM ausencias WHERE id=?", (aus_id,))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# CELDAS ESTADO (marcas en la tabla semanal)
# ─────────────────────────────────────────────────────────────────────────────

def get_celdas_estado(week_offset: int) -> dict:
    """Retorna dict {(worker_id, day_index): tipo_aus}."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT worker_id, day_index, tipo_aus FROM celdas_estado WHERE week_offset=?",
        (week_offset,),
    ).fetchall()
    conn.close()
    return {(r["worker_id"], r["day_index"]): r["tipo_aus"] for r in rows}


def set_celda_estado(worker_id: int, week_offset: int, day_index: int, tipo_aus: str | None):
    conn = get_connection()
    if tipo_aus is None:
        conn.execute(
            "DELETE FROM celdas_estado WHERE worker_id=? AND week_offset=? AND day_index=?",
            (worker_id, week_offset, day_index),
        )
    else:
        conn.execute(
            """INSERT INTO celdas_estado (worker_id, week_offset, day_index, tipo_aus)
               VALUES (?,?,?,?)
               ON CONFLICT(worker_id, week_offset, day_index)
               DO UPDATE SET tipo_aus=excluded.tipo_aus""",
            (worker_id, week_offset, day_index, tipo_aus),
        )
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# HORAS EXTRAS
# ─────────────────────────────────────────────────────────────────────────────

def get_horas_extras_semana(week_iso: str) -> dict:
    """Retorna dict {worker_id: {tipo_he: horas}}."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT worker_id, tipo_he, horas FROM horas_extras WHERE week_iso=?",
        (week_iso,),
    ).fetchall()
    conn.close()
    result: dict = {}
    for r in rows:
        wid = r["worker_id"]
        if wid not in result:
            result[wid] = {}
        result[wid][r["tipo_he"]] = r["horas"]
    return result


def set_hora_extra(worker_id: int, week_iso: str, tipo_he: str, horas: float):
    horas = max(0.0, round(horas * 2) / 2)
    conn = get_connection()
    conn.execute(
        """INSERT INTO horas_extras (worker_id, week_iso, tipo_he, horas)
           VALUES (?,?,?,?)
           ON CONFLICT(worker_id, week_iso, tipo_he)
           DO UPDATE SET horas=excluded.horas""",
        (worker_id, week_iso, tipo_he, horas),
    )
    conn.commit()
    conn.close()


def reset_horas_extras_worker(worker_id: int, week_iso: str):
    conn = get_connection()
    conn.execute(
        "DELETE FROM horas_extras WHERE worker_id=? AND week_iso=?",
        (worker_id, week_iso),
    )
    conn.commit()
    conn.close()
