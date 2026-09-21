# Sistema Integral de Gestión de Trabajo Social (SITS)

Aplicación web para gestionar casos sociales, personas, familias, seguimientos,
compromisos, documentos, formularios, usuarios, permisos e historial de auditoría.

## Desarrollo local

La opción más directa es Docker Compose:

```bash
docker compose up --build
```

El frontend queda en `http://localhost:8081` y el backend en
`http://localhost:8000`. El inicio por correo sin contraseña solo existe para el
entorno local; la configuración de producción impide arrancar si no se activa la
autenticación por contraseña y la cookie segura.

### Prueba local aislada de correos

Para probar la carga sin tocar la instancia local que ya use los puertos 8000 y
8081, inicie un proyecto Compose separado en PowerShell:

```powershell
$env:BACKEND_PORT = '18000'
$env:FRONTEND_PORT = '18081'
docker compose -p sits-correos-local up -d --build
```

Abra `http://localhost:18081`. En una base vacía cree primero el administrador
local; el comando pide la contraseña de forma interactiva y no la deja en el
historial:

```powershell
docker compose -p sits-correos-local exec backend python -m app.cli.bootstrap_admin --correo correo@empresa.com --nombre "Nombre Administrador"
```

Inicie sesión y abra **Trabajo Social > Correos y seguimiento**. Cargue el XLSX
con la hoja `Correos_POST`; el sistema analiza todas las filas, conserva una
vista previa de las 100 más recientes y permite incluir o excluir las que
requieren revisión. Las filas con error quedan trazadas por lote y no invalidan
las demás. La carga de correos admite archivos de hasta 50 MB en frontend,
Nginx y backend.

### Integración segura n8n

La integración no usa ni simula una cookie de navegador. Configure
`N8N_SITS_API_KEY` solamente en el entorno local/servidor que ejecuta SITS y en
el almacén de credenciales de n8n; no la confirme ni la incluya en un workflow
exportado. El único endpoint habilitado por esa clave es:

```text
POST /api/v1/correos/integraciones/n8n
Authorization: Bearer {{$env.N8N_SITS_API_KEY}}
Content-Type: application/json
```

Ejemplo de cuerpo (sin secretos):

```json
{
  "MessageId": "<mail-123@example.test>",
  "Subject": "Solicitud de vacaciones",
  "From": "persona@example.test",
  "To": "trabajo-social@example.test",
  "ReceivedTime": "2026-09-21T08:30:00-05:00",
  "Importance": "normal",
  "Body": "Contenido del correo",
  "HasAttachments": false,
  "IsRead": false,
  "Category": "PERMISOS_VACACIONES_LICENCIAS"
}
```

La respuesta es `201` si se crea y `200` con `duplicate: true` si el mismo
`MessageId` se reintenta. Sin clave o con una incorrecta devuelve `401`; el
token no concede permisos a ningún endpoint administrativo. `MessageId` es
único en la base de datos y los cuerpos se muestran como texto, no HTML activo.

Para detener exclusivamente esta prueba y conservar sus datos locales:

```powershell
docker compose -p sits-correos-local down
```

## Despliegue

La guía completa para Vercel, PythonAnywhere, variables, migraciones, respaldo,
verificación y rollback está en [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md).
La configuración aprobada usa un archivo SQLite persistente en una sola instancia de
backend; los comandos `app.cli.backup_sqlite` y `app.cli.production_check` automatizan
el respaldo consistente y la validación previa a publicar.
