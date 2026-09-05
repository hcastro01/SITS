# Inicio de la migración — Docker local

Esta entrega crea dos servicios ejecutables y la base de persistencia. Todavía no reemplaza la aplicación Apps Script: faltan autenticación, administración de usuarios, módulos de negocio, importación histórica y almacenamiento de adjuntos. Los archivos legacy permanecen en la raíz como referencia.

## Arranque

Requiere Docker Desktop iniciado con contenedores Linux. Desde la raíz del proyecto:

```powershell
docker compose up --build -d --wait
docker compose ps
```

- Interfaz: http://localhost:8080
- API: http://localhost:8000/api/v1/health/ready
- Contrato OpenAPI de esta base: http://localhost:8000/docs

La interfaz consulta la API a través del proxy de Nginx. La pantalla de preparación muestra el resultado real de la comprobación de SQLite. No presenta formularios de registro ni simula autenticación.

Los puertos se vinculan únicamente a la máquina local. Para cambiarlos, copiar `.env.example` a `.env` y ajustar FRONTEND_PORT/BACKEND_PORT. El `.env` de raíz configura Compose; `backend/.env.example` sirve para ejecución Python fuera de Docker. Ninguno contiene secretos.

## Base de datos y permisos

El backend ejecuta Alembic al arrancar y crea `roles`, `permisos`, `usuarios` y la tabla de versión de migración. Inserta los cinco roles y las 90 combinaciones rol/módulo iniciales de Setup.gs. Solo añade combinaciones faltantes; no sobrescribe cambios existentes ni crea usuarios.

Estos seeds son la matriz del código original, no una exportación de los permisos productivos. El esquema de usuarios es una base inicial: los metadatos y el resto de las tablas se incorporarán mediante migraciones posteriores, antes de importar información real.

SQLite se guarda en `/data/trabajo_social.db`, dentro del volumen nombrado `sqlite_data` de este proyecto. Recrear imágenes o contenedores conserva ese volumen. No usar `docker compose down -v` si se desea conservar la base: esa opción elimina los volúmenes.

La app solo expone endpoints de salud en esta etapa. Los usuarios se darán de alta únicamente desde administración, con autorización en el backend cuando se implemente ese módulo. No hay cuenta o contraseña predeterminada ni modo de autenticación de prueba. El primer administrador se conservará mediante la futura migración de cuentas existentes; falta acordar el arranque si no se dispone de esas cuentas.

## Operación y comprobaciones

```powershell
docker compose logs --tail=100 backend frontend
docker compose exec backend python -m unittest discover -s tests -v
docker compose exec backend alembic current
docker compose stop
docker compose start --wait
```

Para reconstruir después de cambios: `docker compose up --build -d --wait`.

El proceso Python y Nginx se ejecutan como usuarios no-root, con filesystem de contenedor de solo lectura, directorios temporales acotados y capacidades eliminadas. El backend dispone de un volumen escribible para SQLite. Una comprobación de salud verifica la revisión de la base antes de arrancar el frontend.

## Dependencias y desarrollo

`backend/requirements.txt` fija dependencias transitivas y hashes; `requirements.in` declara las dependencias directas. El archivo de bloqueo se genera con pip-tools y debe actualizarse deliberadamente. `frontend/package-lock.json` fija el árbol npm; Docker utiliza npm ci. Las imágenes base se fijan por versión de familia, no por digest; una reconstrucción puede incorporar revisiones del proveedor.

Para desarrollar React con recarga automática, levantar backend con Compose y ejecutar `npm ci` seguido de `npm run dev` en frontend. Vite usa el puerto 5173 y envía `/api` al backend local. Esta configuración de desarrollo no es el servidor del contenedor final: el contenedor sirve el build con Nginx.

`VITE_API_URL` es público y se incorpora durante el build; nunca colocar secretos en variables VITE. El Compose usa `/api/v1`. La configuración de Vercel/PythonAnywhere y del inicio de sesión se preparará en su fase correspondiente.

## Continuación

1. Cerrar el mecanismo de identificación y la recuperación/importación del administrador actual.
2. Migrar autorización, administración y auditoría con pruebas de denegación.
3. Incorporar modelos y servicios de dominio, formularios y matriz institucional.
4. Completar las pantallas React y la importación histórica.
5. Verificar paridad por rol y preparar el despliegue.
