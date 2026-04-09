"""
modules/ui_helpers.py — Componentes UI para cada pestaña.
"""
import streamlit as st
from datetime import date

from modules.logic import (
    GRUPOS, DIAS, TURNOS, TIPOS_HE, TIPOS_AUS, ESTADOS_AUS,
    LIMITE_SEMANAL,
    get_wednesday, get_rot_week, week_iso, get_week_dates,
    get_turno, fmt_date, fmt_full, days_between, week_label,
    total_he_worker, get_he_for_worker, get_tipo_aus,
    get_ausencia_dia, build_csv,
)
from database.db import (
    get_workers, add_worker, update_worker_grupo, update_worker_maquina,
    delete_worker,
    get_ausencias, add_ausencia, update_ausencia, update_ausencia_estado,
    delete_ausencia,
    get_celdas_estado, set_celda_estado,
    get_horas_extras_semana, set_hora_extra, reset_horas_extras_worker,
)


# ─────────────────────────────────────────────────────────────────────────────
# CSS global
# ─────────────────────────────────────────────────────────────────────────────

def render_header_css():
    st.markdown("""
    <style>
    .header-box{background:linear-gradient(135deg,#1E3A8A,#3B82F6);border-radius:14px;
        padding:18px 24px;color:#fff;margin-bottom:16px}
    .header-box h1{font-size:22px;font-weight:800;margin:0}
    .header-box p{opacity:.85;font-size:13px;margin:4px 0 0}
    .grupo-badge{background:rgba(255,255,255,.15);border-radius:8px;padding:6px 14px;
        font-size:13px;display:inline-flex;align-items:center;gap:8px;margin:4px 2px}
    .grupo-badge span{background:#fff;color:#1E3A8A;border-radius:5px;
        padding:1px 8px;font-weight:700;font-size:12px}
    .stat-box{border-radius:10px;padding:12px 16px;margin-bottom:4px}
    .stat-val{font-size:22px;font-weight:800}
    .stat-lbl{font-size:11px;color:#64748B;margin-top:2px}
    .badge{border-radius:6px;padding:2px 9px;font-weight:700;font-size:11px;display:inline-block}
    .aus-item{border-radius:10px;padding:12px 16px;border-left:4px solid #CBD5E1;
        margin-bottom:8px;background:#fff;box-shadow:0 1px 4px rgba(0,0,0,.06)}
    .he-worker-card{background:#fff;border-radius:12px;padding:14px 16px;
        box-shadow:0 1px 6px rgba(0,0,0,.07);margin-bottom:10px;border-left:4px solid #F59E0B}
    .norm-table-wrap table{width:100%;border-collapse:collapse;font-size:13px}
    .norm-table-wrap th{background:#1E3A8A;color:#fff;padding:8px 12px;text-align:left}
    .norm-table-wrap td{padding:7px 12px;border-bottom:1px solid #E2E8F0}
    .norm-table-wrap tr:nth-child(even) td{background:#F8FAFC}
    .alerta{background:#FEF9C3;border:1px solid #FDE68A;border-radius:8px;
        padding:8px 14px;font-size:13px;color:#92400E;margin-bottom:14px}
    .tip{background:#F0FDF4;border-radius:7px;padding:6px 12px;
        font-size:12px;color:#16A34A;font-weight:600}
    div[data-testid="stHorizontalBlock"] > div {align-items: flex-start;}
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Header principal
# ─────────────────────────────────────────────────────────────────────────────

def render_header():
    wed = get_wednesday(st.session_state.week_offset)
    rot_w = get_rot_week(wed)
    dates = get_week_dates(wed)
    lbl = week_label(st.session_state.week_offset)

    badges_html = " ".join(
        f'<span class="grupo-badge"><span>Grupo {g}</span>{get_turno(g, rot_w)["nombre"]} · {get_turno(g, rot_w)["horario"]}</span>'
        for g in GRUPOS
    )

    st.markdown(f"""
    <div class="header-box">
        <h1>🏭 Rotación de Turnos</h1>
        <p>Semana laboral: <strong>Miércoles → Martes</strong> · {lbl}</p>
        <div style="margin-top:10px">{badges_html}</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns([1, 2, 1, 1, 2])
    with c1:
        if st.button("‹ Anterior", use_container_width=True):
            st.session_state.week_offset -= 1
            st.rerun()
    with c2:
        st.markdown(
            f"<div style='text-align:center;padding:6px;font-weight:600;font-size:14px;color:#1E3A8A'>"
            f"{fmt_date(dates[0])} – {fmt_date(dates[6])}</div>",
            unsafe_allow_html=True,
        )
    with c3:
        if st.button("Hoy", use_container_width=True):
            st.session_state.week_offset = 0
            st.rerun()
    with c4:
        if st.button("Siguiente ›", use_container_width=True):
            st.session_state.week_offset += 1
            st.rerun()
    with c5:
        workers = get_workers()
        ausencias = get_ausencias()
        celdas = get_celdas_estado(st.session_state.week_offset)
        he_semana = get_horas_extras_semana(week_iso(wed))
        csv_bytes = build_csv(workers, ausencias, celdas, he_semana, st.session_state.week_offset)
        st.download_button(
            "⬇️ Exportar CSV",
            data=csv_bytes,
            file_name=f"Turnos_{wed.isoformat()}.csv",
            mime="text/csv",
            use_container_width=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Tab: TABLA
# ─────────────────────────────────────────────────────────────────────────────

def render_tabla():
    wed = get_wednesday(st.session_state.week_offset)
    rot_w = get_rot_week(wed)
    dates = get_week_dates(wed)

    workers = get_workers()
    ausencias = get_ausencias()
    celdas = get_celdas_estado(st.session_state.week_offset)

    # Búsqueda y filtro
    col_s, col_f = st.columns([3, 2])
    with col_s:
        st.session_state.search_query = st.text_input(
            "🔍 Buscar", value=st.session_state.search_query,
            placeholder="Nombre, máquina o grupo…", label_visibility="collapsed"
        )
    with col_f:
        grupo_opts = ["Todos"] + [f"Grupo {g}" for g in GRUPOS]
        sel_idx = 0
        if st.session_state.filter_grupo != "Todos":
            try:
                sel_idx = grupo_opts.index(f"Grupo {st.session_state.filter_grupo}")
            except ValueError:
                pass
        sel = st.selectbox("Filtrar grupo", grupo_opts, index=sel_idx, label_visibility="collapsed")
        st.session_state.filter_grupo = "Todos" if sel == "Todos" else sel.split(" ")[1]

    q = st.session_state.search_query.lower()
    fg = st.session_state.filter_grupo

    fil = [
        w for w in workers
        if (fg == "Todos" or w["grupo"] == fg)
        and (not q or q in w["nombre"].lower() or q in (w["maquina"] or "").lower() or q in w["grupo"].lower())
    ]

    if not fil:
        st.info("🔍 Sin resultados")
        return

    # Tabla
    header_cols = st.columns([2, 1, 1, 1] + [1] * 7)
    headers = ["Trabajador", "Grupo", "Máquina", "Turno"] + [
        f"{DIAS[i]}\n{fmt_date(dates[i])}" for i in range(7)
    ]
    for col, h in zip(header_cols, headers):
        col.markdown(f"**{h}**")

    st.divider()

    for w in fil:
        turno = get_turno(w["grupo"], rot_w)
        row_cols = st.columns([2, 1, 1, 1] + [1] * 7)

        with row_cols[0]:
            st.write(w["nombre"])
        with row_cols[1]:
            st.markdown(
                f'<span class="badge" style="background:#E0E7FF;color:#3730A3">Grupo {w["grupo"]}</span>',
                unsafe_allow_html=True,
            )
        with row_cols[2]:
            new_maq = st.text_input(
                f"maq_{w['id']}", value=w["maquina"] or "",
                placeholder="Sin asignar", label_visibility="collapsed",
                key=f"maq_{w['id']}"
            )
            if new_maq != (w["maquina"] or ""):
                update_worker_maquina(w["id"], new_maq)
                st.rerun()
        with row_cols[3]:
            st.markdown(
                f'<span class="badge" style="background:{turno["bg"]};color:{turno["text"]}">{turno["nombre"]}</span>',
                unsafe_allow_html=True,
            )

        for di in range(7):
            with row_cols[4 + di]:
                day_str = dates[di].isoformat()
                aus_dia = get_ausencia_dia(w["id"], day_str, ausencias)
                if aus_dia:
                    tipo = get_tipo_aus(aus_dia["tipo"])
                    st.markdown(
                        f'<div title="{tipo["label"] if tipo else aus_dia["tipo"]}" '
                        f'style="text-align:center;font-size:18px">{tipo["icon"] if tipo else "📋"}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    actual = celdas.get((w["id"], di))
                    tipo_actual = get_tipo_aus(actual) if actual else None
                    opciones = ["—"] + [f'{t["icon"]} {t["id"]}' for t in TIPOS_AUS]
                    sel_idx = 0
                    if tipo_actual:
                        try:
                            sel_idx = [t["id"] for t in TIPOS_AUS].index(actual) + 1
                        except ValueError:
                            pass
                    sel = st.selectbox(
                        f"celda_{w['id']}_{di}",
                        opciones,
                        index=sel_idx,
                        label_visibility="collapsed",
                        key=f"celda_{w['id']}_{di}_{st.session_state.week_offset}",
                    )
                    nuevo_tipo = None if sel == "—" else sel.split(" ")[1]
                    if nuevo_tipo != actual:
                        set_celda_estado(w["id"], st.session_state.week_offset, di, nuevo_tipo)
                        st.rerun()

    # Leyenda
    st.markdown("---")
    legend = " ".join(
        f'<span style="background:{t["bg"]};color:{t["color"]};border-radius:20px;'
        f'padding:3px 11px;font-size:11px;font-weight:600;border:1px solid {t["color"]};margin:2px">'
        f'{t["icon"]} {t["id"]} · {t["label"]}</span>'
        for t in TIPOS_AUS
    )
    st.markdown(f'<div style="margin-top:8px">{legend}</div>', unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Tab: HORAS EXTRAS
# ─────────────────────────────────────────────────────────────────────────────

def render_horas():
    wed = get_wednesday(st.session_state.week_offset)
    rot_w = get_rot_week(wed)
    dates = get_week_dates(wed)
    w_iso = week_iso(wed)

    workers = get_workers()
    he_semana = get_horas_extras_semana(w_iso)

    # Búsqueda
    st.session_state.search_he = st.text_input(
        "🔍 Buscar trabajador", value=st.session_state.search_he,
        placeholder="Nombre, máquina o grupo…", label_visibility="collapsed",
        key="search_he_input",
    )
    q = st.session_state.search_he.lower()
    fil = [
        w for w in workers
        if not q or q in w["nombre"].lower() or q in (w["maquina"] or "").lower()
        or q in w["grupo"].lower()
    ]

    # Stats globales
    total_horas = sum(total_he_worker(get_he_for_worker(w["id"], he_semana)) for w in fil)
    con_he = sum(1 for w in fil if total_he_worker(get_he_for_worker(w["id"], he_semana)) > 0)
    en_limite = sum(
        1 for w in fil
        if total_he_worker(get_he_for_worker(w["id"], he_semana)) >= LIMITE_SEMANAL
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("⏱️ Total HE semana", f"{total_horas}h")
    c2.metric("✅ Con horas extras", con_he)
    c3.metric("⚠️ En límite legal", en_limite)
    c4.metric("📋 Límite semanal (CST)", f"{LIMITE_SEMANAL}h")

    # Alerta normativa
    st.markdown(
        f'<div class="alerta">⚠️ Según el <strong>Art. 167A del CST</strong> y la '
        f'<strong>Ley 2466 de 2025</strong>: máximo <strong>2 HE por día</strong> y '
        f'<strong>12 HE por semana</strong>. Jornada nocturna desde las <strong>7:00 p.m.</strong> · '
        f'Semana: <strong>{fmt_date(dates[0])} – {fmt_date(dates[6])}</strong></div>',
        unsafe_allow_html=True,
    )

    # Tabla normativa (desplegable)
    with st.expander("📋 Ver tabla de recargos (CST — Vigente 2026)"):
        st.markdown('<div class="norm-table-wrap">', unsafe_allow_html=True)
        rows_html = "".join(
            f"<tr><td>{t['icon']} <strong>{t['label']}</strong></td>"
            f"<td style='color:#64748B'>{t['horario']}</td>"
            f"<td><span style='background:{t['bg']};color:{t['color']};border-radius:6px;"
            f"padding:2px 8px;font-weight:700'>+{t['recargo']}%</span></td>"
            f"<td style='color:#94A3B8;font-size:11px'>{t['art']}</td></tr>"
            for t in TIPOS_HE
        )
        st.markdown(
            f"<table><thead><tr><th>Tipo</th><th>Horario</th><th>Recargo</th><th>Base legal</th></tr></thead>"
            f"<tbody>{rows_html}</tbody></table>"
            f"<p style='font-size:11px;color:#94A3B8;margin-top:8px'>* Recargo dominical/festivo: "
            f"80% jul 2025, 90% jul 2026, 100% jul 2027 (implementación gradual).</p>"
            "</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    if not fil:
        st.info("🔍 Sin resultados")
        return

    for w in fil:
        he = get_he_for_worker(w["id"], he_semana)
        total = total_he_worker(he)
        turno = get_turno(w["grupo"], rot_w)
        pct = min(100, (total / LIMITE_SEMANAL) * 100)
        border_color = "#EF4444" if total >= LIMITE_SEMANAL else ("#F59E0B" if total > 0 else "#CBD5E1")

        with st.container():
            st.markdown(
                f'<div style="border-left:4px solid {border_color};background:#fff;'
                f'border-radius:12px;padding:14px 16px;box-shadow:0 1px 6px rgba(0,0,0,.07);margin-bottom:4px">',
                unsafe_allow_html=True,
            )
            h1, h2 = st.columns([3, 1])
            with h1:
                iniciales = "".join(p[0] for p in w["nombre"].split())[:2].upper()
                st.markdown(
                    f'<div style="display:flex;align-items:center;gap:10px">'
                    f'<div style="background:#1E3A8A;color:#fff;border-radius:50%;width:36px;height:36px;'
                    f'display:inline-flex;align-items:center;justify-content:center;font-weight:700;font-size:13px">{iniciales}</div>'
                    f'<div><strong style="font-size:14px">{w["nombre"]}</strong><br>'
                    f'<span style="font-size:12px;color:#64748B">Grupo {w["grupo"]} · '
                    f'<span style="color:{turno["color"]};font-weight:600">{turno["nombre"]}</span></span></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with h2:
                badge_bg = "#FEF3C7" if total > 0 else "#F1F5F9"
                badge_col = "#92400E" if total > 0 else "#94A3B8"
                st.markdown(
                    f'<div style="text-align:right">'
                    f'<span style="background:{badge_bg};color:{badge_col};border-radius:8px;'
                    f'padding:5px 14px;font-weight:800;font-size:15px">{total}h / {LIMITE_SEMANAL}h</span>'
                    f'<div style="background:#E2E8F0;border-radius:4px;height:8px;margin-top:5px;overflow:hidden">'
                    f'<div style="background:{"#EF4444" if pct>=100 else "#F59E0B"};width:{pct}%;height:100%"></div></div>'
                    f'<div style="font-size:10px;color:{"#EF4444" if pct>=100 else "#94A3B8"};margin-top:2px">'
                    f'{"⚠️ Límite alcanzado" if pct>=100 else f"{LIMITE_SEMANAL-total:.1f}h disponibles"}'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

            # Controles por tipo de HE
            for tipo in TIPOS_HE:
                tc1, tc2, tc3, tc4, tc5 = st.columns([0.4, 2.5, 1, 2, 0.8])
                with tc1:
                    st.markdown(f'<div style="font-size:20px;padding-top:8px">{tipo["icon"]}</div>', unsafe_allow_html=True)
                with tc2:
                    st.markdown(
                        f'<div style="font-weight:700;font-size:12px">{tipo["label"]}</div>'
                        f'<div style="font-size:10px;color:#94A3B8">{tipo["horario"]}</div>',
                        unsafe_allow_html=True,
                    )
                with tc3:
                    st.markdown(
                        f'<span style="background:{tipo["bg"]};color:{tipo["color"]};border-radius:12px;'
                        f'padding:2px 8px;font-weight:700;font-size:11px">+{tipo["recargo"]}%</span>',
                        unsafe_allow_html=True,
                    )
                with tc4:
                    val = he.get(tipo["id"], 0.0)
                    new_val = st.number_input(
                        f"he_{w['id']}_{tipo['id']}",
                        min_value=0.0, max_value=float(LIMITE_SEMANAL),
                        value=float(val), step=0.5, format="%.1f",
                        label_visibility="collapsed",
                        key=f"he_{w['id']}_{tipo['id']}_{w_iso}",
                    )
                    if new_val != val:
                        set_hora_extra(w["id"], w_iso, tipo["id"], new_val)
                        st.rerun()
                with tc5:
                    cur = he.get(tipo["id"], 0.0)
                    st.markdown(
                        f'<div style="background:{tipo["bg"] if cur>0 else "#F1F5F9"};'
                        f'color:{tipo["color"] if cur>0 else "#94A3B8"};border-radius:7px;'
                        f'padding:4px 8px;font-weight:800;text-align:center">{cur}h</div>',
                        unsafe_allow_html=True,
                    )

            if total > 0:
                if st.button(f"↺ Reiniciar HE", key=f"reset_he_{w['id']}_{w_iso}"):
                    reset_horas_extras_worker(w["id"], w_iso)
                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("")


# ─────────────────────────────────────────────────────────────────────────────
# Tab: AUSENCIAS
# ─────────────────────────────────────────────────────────────────────────────

def render_ausencias():
    workers = get_workers()
    ausencias = get_ausencias()

    # Stats
    total = len(ausencias)
    aprobadas = sum(1 for a in ausencias if a["estado"] == "Aprobado")
    pendientes = sum(1 for a in ausencias if a["estado"] == "Pendiente")
    dias = sum(
        days_between(a["fecha_inicio"], a["fecha_fin"])
        for a in ausencias if a["estado"] == "Aprobado"
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📋 Total registradas", total)
    c2.metric("✅ Aprobadas", aprobadas)
    c3.metric("🕐 Pendientes", pendientes)
    c4.metric("📆 Días ausentes", dias)

    # Filtros
    f1, f2, f3, f4 = st.columns([2, 2, 2, 1])
    with f1:
        wk_opts = ["Todos"] + [w["nombre"] for w in workers]
        wk_sel = st.selectbox("Trabajador", wk_opts, key="filter_aus_wk_sel", label_visibility="collapsed")
        st.session_state.filter_aus_wk = "Todos" if wk_sel == "Todos" else str(next(w["id"] for w in workers if w["nombre"] == wk_sel))
    with f2:
        tipo_opts = ["Todos los tipos"] + [f'{t["icon"]} {t["label"]}' for t in TIPOS_AUS]
        tipo_sel = st.selectbox("Tipo", tipo_opts, key="filter_aus_tipo_sel", label_visibility="collapsed")
        st.session_state.filter_aus_tipo = "Todos" if tipo_sel == "Todos los tipos" else TIPOS_AUS[tipo_opts.index(tipo_sel) - 1]["id"]
    with f3:
        est_opts = ["Todos los estados"] + ESTADOS_AUS
        est_sel = st.selectbox("Estado", est_opts, key="filter_aus_est_sel", label_visibility="collapsed")
        st.session_state.filter_aus_est = "Todos" if est_sel == "Todos los estados" else est_sel
    with f4:
        if st.button("➕ Nueva Ausencia", use_container_width=True):
            st.session_state.aus_form_open = True
            st.session_state.edit_aus_id = None
            st.rerun()

    # Formulario nueva / editar ausencia
    if st.session_state.aus_form_open:
        _render_aus_form(workers, ausencias)

    # Lista filtrada
    fil = [
        a for a in ausencias
        if (st.session_state.filter_aus_tipo == "Todos" or a["tipo"] == st.session_state.filter_aus_tipo)
        and (st.session_state.filter_aus_est == "Todos" or a["estado"] == st.session_state.filter_aus_est)
        and (st.session_state.filter_aus_wk == "Todos" or str(a["worker_id"]) == st.session_state.filter_aus_wk)
    ]

    if not fil:
        st.info("📭 No hay ausencias registradas con los filtros seleccionados.")
        return

    worker_map = {w["id"]: w for w in workers}
    for a in fil:
        w = worker_map.get(a["worker_id"])
        tipo = get_tipo_aus(a["tipo"])
        dias_a = days_between(a["fecha_inicio"], a["fecha_fin"])
        border_color = tipo["color"] if tipo else "#CBD5E1"

        with st.container():
            ac1, ac2, ac3 = st.columns([0.5, 5, 2])
            with ac1:
                st.markdown(f'<div style="font-size:24px;padding-top:6px">{tipo["icon"] if tipo else "📋"}</div>', unsafe_allow_html=True)
            with ac2:
                nombre_w = w["nombre"] if w else "Trabajador eliminado"
                st.markdown(
                    f'<div style="border-left:4px solid {border_color};padding-left:10px">'
                    f'<strong style="font-size:14px">{nombre_w}</strong><br>'
                    f'<span style="font-size:12px;color:#64748B">'
                    f'{tipo["label"] if tipo else a["tipo"]} · '
                    f'{fmt_full(a["fecha_inicio"])} → {fmt_full(a["fecha_fin"])} · '
                    f'<strong>{dias_a} día(s)</strong></span>'
                    + (f'<br><em style="font-size:12px;color:#94A3B8">"{a["observacion"]}"</em>' if a["observacion"] else "")
                    + "</div>",
                    unsafe_allow_html=True,
                )
            with ac3:
                # Estado
                est_cols = st.columns(3)
                for ei, est in enumerate(ESTADOS_AUS):
                    colors = {"Aprobado": ("#D1FAE5", "#10B981"),
                              "Pendiente": ("#FEF3C7", "#F59E0B"),
                              "Rechazado": ("#FEE2E2", "#DC2626")}
                    bg, fg = colors[est]
                    is_active = a["estado"] == est
                    with est_cols[ei]:
                        if st.button(
                            est, key=f"est_{a['id']}_{est}",
                            use_container_width=True,
                            type="primary" if is_active else "secondary",
                        ):
                            update_ausencia_estado(a["id"], est)
                            st.rerun()
                act1, act2 = st.columns(2)
                with act1:
                    if st.button("✏️", key=f"edit_aus_{a['id']}"):
                        st.session_state.aus_form_open = True
                        st.session_state.edit_aus_id = a["id"]
                        st.rerun()
                with act2:
                    if st.button("🗑️", key=f"del_aus_{a['id']}"):
                        delete_ausencia(a["id"])
                        st.rerun()
        st.divider()


def _render_aus_form(workers, ausencias):
    edit_id = st.session_state.edit_aus_id
    editing = edit_id is not None
    f = next((a for a in ausencias if a["id"] == edit_id), {}) if editing else {}

    title = "✏️ Editar Ausencia" if editing else "➕ Nueva Ausencia"
    with st.expander(title, expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            worker_names = ["Seleccionar…"] + [w["nombre"] for w in workers]
            pre_idx = 0
            if f.get("worker_id"):
                try:
                    pre_idx = next(i + 1 for i, w in enumerate(workers) if w["id"] == f["worker_id"])
                except StopIteration:
                    pass
            w_sel = st.selectbox("Trabajador *", worker_names, index=pre_idx)
        with c2:
            tipo_labels = [f'{t["icon"]} {t["label"]}' for t in TIPOS_AUS]
            pre_tipo = 0
            if f.get("tipo"):
                try:
                    pre_tipo = next(i for i, t in enumerate(TIPOS_AUS) if t["id"] == f["tipo"])
                except StopIteration:
                    pass
            tipo_sel_label = st.selectbox("Tipo *", tipo_labels, index=pre_tipo)

        c3, c4, c5 = st.columns(3)
        with c3:
            fi_val = date.fromisoformat(f["fecha_inicio"]) if f.get("fecha_inicio") else date.today()
            fecha_inicio = st.date_input("Fecha Inicio *", value=fi_val)
        with c4:
            ff_val = date.fromisoformat(f["fecha_fin"]) if f.get("fecha_fin") else date.today()
            fecha_fin = st.date_input("Fecha Fin *", value=ff_val)
        with c5:
            pre_est = ESTADOS_AUS.index(f.get("estado", "Pendiente"))
            estado = st.selectbox("Estado", ESTADOS_AUS, index=pre_est)

        obs = st.text_area("Observación", value=f.get("observacion", ""), height=68)

        if fecha_inicio and fecha_fin and fecha_fin >= fecha_inicio:
            dias_dur = days_between(fecha_inicio.isoformat(), fecha_fin.isoformat())
            st.markdown(f'<div class="tip">📆 Duración: {dias_dur} día(s)</div>', unsafe_allow_html=True)

        btn1, btn2 = st.columns([1, 4])
        with btn1:
            if st.button("💾 Guardar", type="primary"):
                if w_sel == "Seleccionar…":
                    st.error("Selecciona un trabajador.")
                    return
                worker_id = next(w["id"] for w in workers if w["nombre"] == w_sel)
                tipo_id = TIPOS_AUS[tipo_labels.index(tipo_sel_label)]["id"]
                if editing:
                    update_ausencia(edit_id, worker_id, tipo_id,
                                    fecha_inicio.isoformat(), fecha_fin.isoformat(),
                                    estado, obs)
                else:
                    add_ausencia(worker_id, tipo_id,
                                 fecha_inicio.isoformat(), fecha_fin.isoformat(),
                                 estado, obs)
                st.session_state.aus_form_open = False
                st.session_state.edit_aus_id = None
                st.rerun()
        with btn2:
            if st.button("Cancelar"):
                st.session_state.aus_form_open = False
                st.session_state.edit_aus_id = None
                st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# Tab: GESTIONAR PERSONAL
# ─────────────────────────────────────────────────────────────────────────────

def render_gestionar():
    wed = get_wednesday(st.session_state.week_offset)
    rot_w = get_rot_week(wed)
    workers = get_workers()
    ausencias = get_ausencias()
    he_semana = get_horas_extras_semana(week_iso(wed))

    st.subheader(f"👥 Personal ({len(workers)})")

    # Formulario agregar
    with st.expander("➕ Agregar nuevo trabajador", expanded=st.session_state.show_add_worker):
        nc1, nc2, nc3 = st.columns([3, 1, 1])
        with nc1:
            new_name = st.text_input("Nombre *", placeholder="Ej: Juan Pérez", key="new_worker_name")
        with nc2:
            grupo_opts = [f"Grupo {g}" for g in GRUPOS]
            new_grupo_sel = st.selectbox("Grupo", grupo_opts, key="new_worker_grupo")
            new_grupo = new_grupo_sel.split(" ")[1]
        with nc3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("➕ Agregar", type="primary", use_container_width=True):
                if new_name.strip():
                    add_worker(new_name.strip(), new_grupo)
                    st.session_state.show_add_worker = False
                    st.rerun()
                else:
                    st.warning("Ingresa el nombre.")

    st.markdown("---")

    if not workers:
        st.info("No hay trabajadores registrados.")
        return

    # Lista de trabajadores
    for w in workers:
        turno = get_turno(w["grupo"], rot_w)
        aus_count = sum(1 for a in ausencias if a["worker_id"] == w["id"])
        he = get_he_for_worker(w["id"], he_semana)
        he_total = total_he_worker(he)
        iniciales = "".join(p[0] for p in w["nombre"].split())[:2].upper()

        lc1, lc2, lc3, lc4 = st.columns([3, 1, 1, 0.5])
        with lc1:
            badges = ""
            if aus_count > 0:
                badges += f'<span style="background:#DBEAFE;color:#1E3A8A;border-radius:10px;padding:1px 7px;font-size:11px;margin-left:5px">{aus_count} aus.</span>'
            if he_total > 0:
                badges += f'<span style="background:#FEF3C7;color:#92400E;border-radius:10px;padding:1px 7px;font-size:11px;margin-left:4px">⏱️ {he_total}h</span>'
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:10px">'
                f'<div style="background:#1E3A8A;color:#fff;border-radius:50%;width:32px;height:32px;'
                f'display:inline-flex;align-items:center;justify-content:center;font-weight:700;font-size:13px">{iniciales}</div>'
                f'<div><strong style="font-size:14px">{w["nombre"]}</strong>{badges}<br>'
                f'<span style="font-size:12px;color:#64748B">Grupo {w["grupo"]} · '
                f'<span style="color:{turno["color"]};font-weight:600">{turno["nombre"]} ({turno["horario"]})</span>'
                + (f' · {w["maquina"]}' if w["maquina"] else "")
                + "</span></div></div>",
                unsafe_allow_html=True,
            )
        with lc2:
            new_g = st.selectbox(
                f"grupo_{w['id']}",
                GRUPOS, index=GRUPOS.index(w["grupo"]),
                label_visibility="collapsed",
                key=f"grupo_sel_{w['id']}",
            )
            if new_g != w["grupo"]:
                update_worker_grupo(w["id"], new_g)
                st.rerun()
        with lc3:
            new_maq = st.text_input(
                f"maq_g_{w['id']}", value=w["maquina"] or "",
                placeholder="Máquina", label_visibility="collapsed",
                key=f"maq_g_{w['id']}",
            )
            if new_maq != (w["maquina"] or ""):
                update_worker_maquina(w["id"], new_maq)
                st.rerun()
        with lc4:
            if st.button("✕", key=f"del_w_{w['id']}", help="Eliminar trabajador"):
                delete_worker(w["id"])
                st.rerun()

        st.divider()
