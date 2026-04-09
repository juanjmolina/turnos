"""
modules/logic.py — Lógica de negocio: turnos, semanas, horas extras.
"""
from datetime import date, timedelta
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────────────

GRUPOS = ["A", "B", "C"]
DIAS = ["Mié", "Jue", "Vie", "Sáb", "Dom", "Lun", "Mar"]

TURNOS = [
    {"id": 0, "nombre": "Mañana", "horario": "6:00-14:00",  "color": "#F59E0B", "bg": "#FEF3C7", "text": "#92400E"},
    {"id": 1, "nombre": "Tarde",  "horario": "14:00-22:00", "color": "#3B82F6", "bg": "#DBEAFE", "text": "#1E3A8A"},
    {"id": 2, "nombre": "Noche",  "horario": "22:00-6:00",  "color": "#8B5CF6", "bg": "#EDE9FE", "text": "#4C1D95"},
]

TIPOS_HE = [
    {"id": "ED",   "label": "Extra Diurna",                  "horario": "6:00am – 7:00pm",             "recargo": 25,  "color": "#F59E0B", "bg": "#FEF3C7", "icon": "☀️",   "art": "Art. 168 CST · +25%"},
    {"id": "EN",   "label": "Extra Nocturna",                "horario": "7:00pm – 6:00am",             "recargo": 75,  "color": "#8B5CF6", "bg": "#EDE9FE", "icon": "🌙",   "art": "Art. 168 CST · +75%"},
    {"id": "RN",   "label": "Recargo Nocturno",              "horario": "7:00pm – 6:00am (ordinaria)", "recargo": 35,  "color": "#6366F1", "bg": "#E0E7FF", "icon": "🌃",   "art": "Art. 168 CST · +35%"},
    {"id": "DOM",  "label": "Dominical / Festivo Diurno",    "horario": "Domingo o festivo día",       "recargo": 80,  "color": "#10B981", "bg": "#D1FAE5", "icon": "📅",   "art": "Ley 2466/2025 · +80%"},
    {"id": "DOMN", "label": "Dominical / Festivo Nocturno",  "horario": "Domingo o festivo noche",     "recargo": 110, "color": "#EC4899", "bg": "#FCE7F3", "icon": "🌙📅", "art": "Art. 168 CST · +110%"},
    {"id": "EDD",  "label": "Extra Diurna en Dominical",     "horario": "HE diurna en dom/festivo",    "recargo": 100, "color": "#EF4444", "bg": "#FEE2E2", "icon": "☀️📅", "art": "Art. 168 CST · +100%"},
    {"id": "END",  "label": "Extra Nocturna en Dominical",   "horario": "HE nocturna en dom/festivo",  "recargo": 150, "color": "#DC2626", "bg": "#FEE2E2", "icon": "🌙🔥", "art": "Art. 168 CST · +150%"},
]

TIPOS_AUS = [
    {"id": "PR",  "label": "Permiso Remunerado",          "color": "#10B981", "bg": "#D1FAE5", "icon": "✅"},
    {"id": "PN",  "label": "Permiso No Remunerado",       "color": "#F59E0B", "bg": "#FEF3C7", "icon": "🟡"},
    {"id": "DS",  "label": "Día de Descanso",             "color": "#6B7280", "bg": "#F3F4F6", "icon": "😴"},
    {"id": "INC", "label": "Incapacidad",                 "color": "#EF4444", "bg": "#FEE2E2", "icon": "🏥"},
    {"id": "VAC", "label": "Vacaciones",                  "color": "#06B6D4", "bg": "#CFFAFE", "icon": "🌴"},
    {"id": "AUS", "label": "Ausencia Injustificada",      "color": "#DC2626", "bg": "#FEE2E2", "icon": "❌"},
    {"id": "CAL", "label": "Calamidad Doméstica",         "color": "#7C3AED", "bg": "#EDE9FE", "icon": "🏠"},
    {"id": "LIC", "label": "Licencia",                    "color": "#0EA5E9", "bg": "#E0F2FE", "icon": "📄"},
    {"id": "MAT", "label": "Lic. Maternidad/Paternidad",  "color": "#EC4899", "bg": "#FCE7F3", "icon": "👶"},
]

ESTADOS_AUS = ["Pendiente", "Aprobado", "Rechazado"]

LIMITE_DIARIO = 2
LIMITE_SEMANAL = 12

# ─────────────────────────────────────────────────────────────────────────────
# Helpers de semana
# ─────────────────────────────────────────────────────────────────────────────

def get_wednesday(offset: int = 0) -> date:
    """Retorna el miércoles de la semana actual ± offset semanas."""
    today = date.today()
    # weekday(): Mon=0 … Sun=6  |  Wed=2
    days_since_wed = (today.weekday() - 2) % 7
    wed = today - timedelta(days=days_since_wed)
    return wed + timedelta(weeks=offset)


def get_rot_week(wed: date) -> int:
    """Índice de rotación basado en el miércoles de referencia (2024-01-03)."""
    base = date(2024, 1, 3)
    return round((wed - base).days / 7)


def week_iso(wed: date) -> str:
    return wed.isoformat()


def get_week_dates(wed: date) -> list[date]:
    return [wed + timedelta(days=i) for i in range(7)]


def get_turno(grupo: str, rot_week: int) -> dict:
    idx = (GRUPOS.index(grupo) + rot_week % 3 + 300) % 3
    return TURNOS[idx]


def fmt_date(d: date) -> str:
    meses = ["", "ene", "feb", "mar", "abr", "may", "jun",
             "jul", "ago", "sep", "oct", "nov", "dic"]
    return f"{d.day:02d} {meses[d.month]}"


def fmt_full(s: str) -> str:
    if not s:
        return ""
    d = date.fromisoformat(s)
    meses = ["", "enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    return f"{d.day:02d} {meses[d.month]} {d.year}"


def days_between(a: str, b: str) -> int:
    return (date.fromisoformat(b) - date.fromisoformat(a)).days + 1


def week_label(offset: int) -> str:
    if offset == 0:
        return "Semana actual"
    if offset == 1:
        return "Próxima semana"
    if offset == -1:
        return "Semana anterior"
    return f"+{offset} semanas" if offset > 0 else f"{offset} semanas"


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de horas extras
# ─────────────────────────────────────────────────────────────────────────────

def total_he_worker(he: dict) -> float:
    return sum(he.get(t["id"], 0) for t in TIPOS_HE)


def get_he_for_worker(worker_id: int, he_semana: dict) -> dict:
    base = {t["id"]: 0.0 for t in TIPOS_HE}
    base.update(he_semana.get(worker_id, {}))
    return base


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de ausencias
# ─────────────────────────────────────────────────────────────────────────────

def get_tipo_aus(tipo_id: str) -> Optional[dict]:
    return next((t for t in TIPOS_AUS if t["id"] == tipo_id), None)


def get_ausencia_dia(worker_id: int, day_str: str, ausencias: list[dict]) -> Optional[dict]:
    """Retorna la ausencia Aprobada que cubre ese día, o None."""
    for a in ausencias:
        if (a["worker_id"] == worker_id
                and a["estado"] == "Aprobado"
                and a["fecha_inicio"] <= day_str <= a["fecha_fin"]):
            return a
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Export CSV
# ─────────────────────────────────────────────────────────────────────────────

def build_csv(workers, ausencias, celdas, he_semana, week_offset) -> bytes:
    wed = get_wednesday(week_offset)
    rot_w = get_rot_week(wed)
    dates = get_week_dates(wed)

    lines = ["\ufeff"]  # BOM para Excel
    lines.append("SISTEMA DE ROTACIÓN DE TURNOS")
    lines.append(f"Semana:,{fmt_date(dates[0])} - {fmt_date(dates[6])}")
    lines.append("")

    header = ["Trabajador", "Grupo", "Máquina", "Turno"] + \
             [f"{DIAS[i]} {fmt_date(dates[i])}" for i in range(7)] + ["Total HE"]
    lines.append(",".join(header))

    for w in workers:
        t = get_turno(w["grupo"], rot_w)
        he = get_he_for_worker(w["id"], he_semana)
        tot = total_he_worker(he)
        dia_cols = []
        for di, d in enumerate(dates):
            day_str = d.isoformat()
            aus_dia = get_ausencia_dia(w["id"], day_str, ausencias)
            if aus_dia:
                dia_cols.append(aus_dia["tipo"])
            else:
                val = celdas.get((w["id"], di), "")
                dia_cols.append(val)
        row = [f'"{w["nombre"]}"', f'"Grupo {w["grupo"]}"',
               f'"{w["maquina"] or ""}"', f'"{t["nombre"]} ({t["horario"]})"'] + \
              [f'"{c}"' for c in dia_cols] + [str(tot)]
        lines.append(",".join(row))

    lines.append("")
    lines.append(f"HORAS EXTRAS DETALLADAS — {fmt_date(dates[0])} al {fmt_date(dates[6])}")
    he_header = ["Trabajador", "Grupo"] + \
                [f'{t["label"]} (+{t["recargo"]}%)' for t in TIPOS_HE] + ["TOTAL"]
    lines.append(",".join(he_header))
    for w in workers:
        he = get_he_for_worker(w["id"], he_semana)
        tot = total_he_worker(he)
        if tot > 0:
            row = [f'"{w["nombre"]}"', f'"Grupo {w["grupo"]}"'] + \
                  [str(he.get(t["id"], 0)) for t in TIPOS_HE] + [str(tot)]
            lines.append(",".join(row))

    lines.append("")
    lines.append("AUSENCIAS")
    lines.append("Trabajador,Tipo,Inicio,Fin,Días,Estado,Observación")
    worker_map = {w["id"]: w for w in workers}
    for a in ausencias:
        w = worker_map.get(a["worker_id"])
        tipo = get_tipo_aus(a["tipo"])
        dias = days_between(a["fecha_inicio"], a["fecha_fin"])
        row = [
            f'"{w["nombre"] if w else "N/A"}"',
            f'"{tipo["label"] if tipo else a["tipo"]}"',
            f'"{a["fecha_inicio"]}"', f'"{a["fecha_fin"]}"',
            str(dias), f'"{a["estado"]}"', f'"{a["observacion"] or ""}"',
        ]
        lines.append(",".join(row))

    return "\n".join(lines).encode("utf-8-sig")
