# Despliegue de producción: Vercel + PythonAnywhere

Esta guía publica el frontend React/Vite en Vercel y la API FastAPI con SQLite en
PythonAnywhere. Los documentos permanecen comprimidos dentro de SQLite; no se
requiere un directorio público de archivos.

## 1. Arquitectura y dominios

- Frontend: `https://<proyecto>.vercel.app`
- API: `https://<usuario>.pythonanywhere.com`
- Base de datos: `~/SITS/backend/data/trabajo_social.db`
- WSGI: `backend/wsgi.py`, que adapta ASGI mediante `a2wsgi`

Para el esquema anterior, el navegador considera la cookie de sesión de terceros.
Use `COOKIE_SAMESITE=none` y `COOKIE_SECURE=true`. Para máxima confiabilidad a largo
plazo, use dominios propios del mismo sitio, por ejemplo `app.institucion.gob.ec` y
`api.institucion.gob.ec`; después puede cambiar SameSite a `lax`.

## 2. Preparación segura del repositorio

1. Revise y fusione la rama `codex/refactor-production`.
2. No agregue archivos `.env`, la base SQLite, respaldos ni archivos subidos al Git.
3. En producción cree las credenciales únicamente en el panel del proveedor o en
   un `.env` con permisos restringidos.
4. Antes de toda migración, descargue o copie un respaldo verificable de SQLite.
5. No aloje SQLite en almacenamiento efímero ni conecte el mismo archivo desde
   servidores distintos. Esta arquitectura usa una sola instancia de backend.

## 3. Backend en PythonAnywhere

### 3.1 Clonar, crear el entorno e instalar

Abra una consola Bash de PythonAnywhere y ejecute, ajustando la URL y versión de
Python a las disponibles en su cuenta:

```bash
git clone <URL_PRIVADA_DEL_REPOSITORIO> ~/SITS
cd ~/SITS/backend
python3.13 -m venv ~/.virtualenvs/sits
source ~/.virtualenvs/sits/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
mkdir -p data backups
chmod 700 data backups
```

### 3.2 Variables de entorno

Cree `~/SITS/backend/.env` (nunca lo suba a Git):

```dotenv
APP_NAME=Sistema Integral de Gestión de Trabajo Social
ENVIRONMENT=production
DATABASE_URL=sqlite:////home/<usuario>/SITS/backend/data/trabajo_social.db
CORS_ORIGINS=["https://<proyecto>.vercel.app"]
TRUSTED_HOSTS=["<usuario>.pythonanywhere.com"]
TIMEZONE=America/Guayaquil
AUTH_MODE=password
COOKIE_SECURE=true
COOKIE_SAMESITE=none
SESSION_TTL_HOURS=12
LOGIN_MAX_ATTEMPTS=5
LOGIN_WINDOW_SECONDS=300
LOG_LEVEL=INFO
```

Puede partir de `backend/.env.production.example`, sustituyendo todos los marcadores.
La ruta SQLite debe ser absoluta: así se evita crear por error otra base vacía cuando
cambia el directorio de trabajo. `SQLITE_JOURNAL_MODE=wal` mejora la concurrencia entre
lecturas y escrituras dentro del mismo servidor.

`LOGIN_MAX_ATTEMPTS` limita los fallos consecutivos por cuenta durante la ventana
indicada. Mantenga además un límite por IP en el proxy público; la configuración
Docker incluida ya lo aplica en NGINX.

Restrinja el archivo:

```bash
chmod 600 ~/SITS/backend/.env
```

No se necesita un secreto estático de sesión: las sesiones usan tokens aleatorios,
solo su hash se guarda en la base y la cookie es `HttpOnly`.

### 3.3 Respaldo, migraciones y datos base

Si ya existe una base, detenga temporalmente la aplicación web y haga un respaldo
consistente:

```bash
cd ~/SITS/backend
source ~/.virtualenvs/sits/bin/activate
python -m app.cli.backup_sqlite --output-dir backups
python -m alembic current
python -m app.cli.initialize
python -m alembic current
```

Descargue también el respaldo recién creado fuera de PythonAnywhere y compruebe que
abre. `app.cli.initialize` aplica Alembic y crea o completa los
catálogos base de forma idempotente.

Para una instalación vacía, cree el primer administrador; el comando solicita la
contraseña sin mostrarla (mínimo 12 caracteres, mayúscula, minúscula y número):

```bash
python -m app.cli.bootstrap_admin --correo admin@institucion.gob.ec --nombre "Administración"
```

Para asignar o rotar la contraseña de un usuario ya existente:

```bash
python -m app.cli.set_password --correo usuario@institucion.gob.ec
```

Cuando exista al menos un administrador activo con contraseña, ejecute el chequeo
de predespliegue. Es de solo lectura y termina con código distinto de cero si encuentra
una configuración insegura, migraciones pendientes, corrupción, claves foráneas rotas o
ausencia de un administrador utilizable:

```bash
python -m app.cli.production_check
```

Los usuarios activos que aún no tengan contraseña aparecen como aviso; así se pueden
regularizar con `set_password` antes de abrir el sistema a operación.

### 3.4 Configurar la aplicación web

En **Web > Add a new web app**, elija configuración manual y la misma versión de
Python del entorno virtual. Configure:

- Source code: `/home/<usuario>/SITS/backend`
- Working directory: `/home/<usuario>/SITS/backend`
- Virtualenv: `/home/<usuario>/.virtualenvs/sits`

Reemplace el contenido del archivo WSGI de PythonAnywhere por:

```python
import os
import sys

project = "/home/<usuario>/SITS/backend"
if project not in sys.path:
    sys.path.insert(0, project)
os.chdir(project)

from wsgi import application
```

No configure mapeos estáticos para documentos. Pulse **Reload** y revise el log de
errores. La comprobación esperada es:

```bash
curl https://<usuario>.pythonanywhere.com/api/v1/health/ready
```

Debe responder HTTP 200. `/docs` debe responder 404 en producción.

## 4. Frontend en Vercel

1. Importe el repositorio en Vercel.
2. Defina **Root Directory** como `frontend`.
3. Framework preset: **Vite**.
4. Install command: `npm install`.
5. Build command: `npm run build`.
6. Output directory: `dist`.
7. Agregue para Production y Preview:

```dotenv
VITE_API_URL=https://<usuario>.pythonanywhere.com/api/v1
```

Puede copiar `frontend/.env.production.example` como referencia. La URL se integra
durante el build, por lo que cambiarla requiere un nuevo despliegue del frontend.

8. Despliegue. `frontend/vercel.json` mantiene las rutas de React Router al recargar
   y agrega cabeceras defensivas.
9. Copie la URL definitiva de Vercel en `CORS_ORIGINS` del backend y recargue la app
   de PythonAnywhere. Si habilita previews, agregue solo orígenes exactos que vaya a
   usar; no use `*` con credenciales.

## 5. Actualizaciones posteriores

En PythonAnywhere:

```bash
cd ~/SITS
git pull --ff-only
source ~/.virtualenvs/sits/bin/activate
python -m pip install -r backend/requirements.txt
cd backend
python -m app.cli.backup_sqlite --output-dir backups
python -m app.cli.initialize
python -m app.cli.production_check
```

Después pulse **Reload**. Vercel puede desplegar automáticamente la misma revisión
al recibir el cambio en la rama configurada.

## 6. Verificación posterior al despliegue

- Iniciar y cerrar sesión; confirmar que la cookie aparece como `Secure`, `HttpOnly`
  y con el SameSite configurado.
- Probar un usuario sin permisos administrativos y comprobar que API y UI rechazan
  acciones no autorizadas.
- Crear y editar un caso; recargar su URL directa; cerrar el caso con confirmación.
- Crear un seguimiento y verificar el historial de auditoría.
- Subir, descargar y eliminar justificadamente un PDF permitido.
- Probar desktop y móvil; confirmar que menú, tablas, formularios y modales no
  producen desplazamiento horizontal.
- Revisar `/api/v1/health/ready`, logs de PythonAnywhere y consola del navegador.
- Confirmar la fecha local ecuatoriana cerca de medianoche UTC.
- Descargar un respaldo y abrirlo con `PRAGMA integrity_check;`.
- Confirmar que el respaldo también existe fuera de la cuenta de alojamiento.

## 7. Backup y rollback

Conserve respaldos diarios fuera del servidor y aplique retención institucional.
`app.cli.backup_sqlite` usa la API de respaldo en línea y valida la copia con
`PRAGMA quick_check`; no copie únicamente el archivo principal mientras WAL está activo.

SQLite es apropiado para esta instalación de una sola instancia y carga moderada. Vigile
el crecimiento del archivo, la duración de escrituras y los errores `database is locked`.
Si en el futuro se requieren varias instancias de API, alta concurrencia de escritura o
alta disponibilidad, planifique una migración no destructiva a un motor cliente-servidor;
no comparta el archivo SQLite por red.

Si falla el frontend, promueva en Vercel el despliegue anterior. Si falla el backend:

1. Active modo de mantenimiento o detenga la aplicación.
2. Guarde aparte la base fallida y los logs para diagnóstico.
3. Vuelva al commit anterior (`git switch --detach <commit-verificado>`).
4. Reinstale `requirements.txt` y pulse **Reload**.
5. Mantenga la columna aditiva `password_hash`: el código anterior puede ignorarla y
   así no se pierden credenciales. Solo restaure el respaldo si la integridad o los
   datos fueron afectados.
6. Si debe restaurar, reemplace la base únicamente con la app detenida, valide
   `PRAGMA integrity_check;`, arranque y ejecute la lista de verificación.

La migración `0009_password_auth` es aditiva. Evitar su downgrade es el rollback más
seguro; bajarla eliminaría los hashes de contraseña.
