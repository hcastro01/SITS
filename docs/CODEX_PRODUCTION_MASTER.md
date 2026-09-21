# Cierre productivo SITS

## Autorización vigente

El usuario autorizó el 2026-09-21 el cierre completo de la versión de Correos y seguimiento: correcciones, pruebas, PR, merge controlado, Vercel, PythonAnywhere, migraciones, carga histórica deduplicada, n8n de ingesta y QA en el dominio productivo. Esta autorización reemplaza las restricciones locales históricas, sin omitir protecciones de plataforma, controles de seguridad ni reglas de recuperación.

## Versión candidata y alcance

- Candidata: `e6bd6298f33df6e285e852ccd009595371c799b9` en `codex/correos-n8n-production-readiness`.
- Base comprobada: `08246dfbff1db6dcb63d4fb560fc18e3ce556a99` (`origin/master`); candidata 11 commits por delante y 0 por detrás.
- Código funcional: `35860b5`; los commits posteriores son exclusivamente documentación de evidencia.
- Incluye Correos y seguimiento, las migraciones `0025_correos_seguimientos` y `0026_correos_operational_hardening`, catálogo/permiso `CORREOS`, endpoint n8n de mínimo privilegio y las correcciones heredadas de catálogo autorizadas.

## Preflight de producción

- GitHub autenticado como `hcastro01`, con acceso administrador a `hcastro01/SITS`; no hay PR abierto ni protección de rama configurada.
- Vercel existente: equipo `hector-f6fc`, proyecto `sits`, dominio productivo válido `sits-wheat.vercel.app`. El candidato tiene un deployment Preview `Ready`; el deployment productivo actual corresponde a `08246df`.
- PythonAnywhere existente: aplicación ASGI de `hector00999.pythonanywhere.com`; checkout limpio, en `master` y alineado a `08246df`.
- El preflight de solo lectura pasó: configuración productiva, SQLite persistente, integridad, revisión Alembic actual, administrador con contraseña y credenciales de usuarios.
- Se creó un respaldo SQLite consistente y se validó su apertura e integridad en modo solo lectura. La referencia y evidencia privada están en el manifiesto ignorado de recuperación.

## Secuencia aprobada

1. Terminar la revisión del candidato y crear un único PR hacia `master`.
2. Verificar los checks del SHA del PR y el estado justo antes del merge.
3. Hacer merge con commit de merge, conservando la rama de recuperación.
4. Actualizar PythonAnywhere mediante avance rápido, dependencias fijadas, migraciones y semillas explícitas idempotentes; validar catálogo, permisos y backend cargado.
5. Esperar y verificar el deployment Production de Vercel generado desde `master`, incluido el dominio habitual y la conexión HTTPS al backend.
6. Cargar únicamente el histórico productivo faltante mediante el importador validado, con trazabilidad e idempotencia.
7. Configurar y verificar n8n solo si se identifica un workflow de ingesta aislado y una credencial de mínimo privilegio; nunca activar acciones sobre el buzón.
8. Ejecutar QA autenticado en producción y actualizar los documentos de cierre.

## Recuperación

El backend anterior y el deployment Production anterior se conservan como puntos de recuperación. No se restaurará la base automáticamente: ante regresión se preservarán escrituras posteriores y se preferirá un arreglo hacia delante o una reversión de código compatible.

## Estado actual

`IN_PROGRESS`: preflight, acceso y respaldo productivo completos. Siguiente acción: crear y revisar el PR del SHA candidato.
