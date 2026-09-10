# Sistema Integral de Gestión de Trabajo Social (SITS)

Aplicación web para gestionar casos sociales, personas, familias, seguimientos,
compromisos, documentos, formularios, usuarios, permisos e historial de auditoría.

## Desarrollo local

La opción más directa es Docker Compose:

```bash
docker compose up --build
```

El frontend queda en `http://localhost:8080` y el backend en
`http://localhost:8000`. El inicio por correo sin contraseña solo existe para el
entorno local; la configuración de producción impide arrancar si no se activa la
autenticación por contraseña y la cookie segura.

## Despliegue

La guía completa para Vercel, PythonAnywhere, variables, migraciones, respaldo,
verificación y rollback está en [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md).
La configuración aprobada usa un archivo SQLite persistente en una sola instancia de
backend; los comandos `app.cli.backup_sqlite` y `app.cli.production_check` automatizan
el respaldo consistente y la validación previa a publicar.
