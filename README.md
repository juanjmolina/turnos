# Sistema de Turnos y Compensatorios

## Archivos necesarios
```
├── app.py          ← aplicación Python principal
├── index.html      ← interfaz completa del sistema
├── requirements.txt
└── README.md
```

## Configuración de la base de datos

### Variable de entorno
```bash
DATABASE_URL=postgresql://usuario:contraseña@host:5432/nombre_db
```

### Streamlit Cloud
En el panel de tu app → **Settings → Secrets**:
```toml
DATABASE_URL = "postgresql://usuario:contraseña@host:5432/nombre_db"
```

### Supabase (recomendado — gratis)
1. Crea cuenta en supabase.com
2. Nuevo proyecto → Settings → Database → Connection String → URI
3. Copia la URL y reemplaza `[YOUR-PASSWORD]` con tu contraseña

### Railway
La variable `DATABASE_URL` se agrega automáticamente al crear un plugin de PostgreSQL.

### Neon (gratis)
1. neon.tech → New Project
2. Copia la cadena de conexión

## Correr localmente
```bash
pip install -r requirements.txt
export DATABASE_URL="postgresql://..."
streamlit run app.py
```

## Despliegue en Streamlit Cloud
1. Sube app.py, index.html, requirements.txt a GitHub
2. share.streamlit.io → New app → selecciona el repo
3. Agrega DATABASE_URL en Secrets

## Cómo funciona la sincronización
- Al abrir la app, carga los datos de PostgreSQL automáticamente
- El botón 💾 Datos → "Guardar en base de datos" sincroniza todos los módulos
- Al Exportar datos también guarda una copia en la DB
- Múltiples usuarios ven los mismos datos al recargar la página

## Credenciales del sistema
- admin / admin123
- super / super123
