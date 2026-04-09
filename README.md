# 🏭 Sistema de Rotación de Turnos

Aplicación Streamlit para gestión de turnos rotativos (Mañana / Tarde / Noche),
ausencias, horas extras (CST Colombia / Ley 2466 de 2025) y personal.

## Estructura

```
turnos-app/
├── app.py                  # Punto de entrada Streamlit
├── requirements.txt
├── .gitignore
├── database/
│   └── db.py               # CRUD SQLite (fácilmente migrable a PostgreSQL)
├── modules/
│   ├── logic.py            # Lógica de negocio pura
│   └── ui_helpers.py       # Componentes UI por pestaña
└── .streamlit/
    └── config.toml         # Tema y configuración
```

## Instalación

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Migración a PostgreSQL

1. `pip install psycopg2-binary`
2. En `database/db.py`, reemplaza `get_connection()`:

```python
import psycopg2, os

def get_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"])
```

3. Cambia los placeholders `?` → `%s` en todas las consultas de `db.py`.
4. Ajusta `ON CONFLICT` a la sintaxis PostgreSQL (ya es compatible).
