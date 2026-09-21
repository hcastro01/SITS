# Cierre productivo SITS

## Resultado de cierre (2026-09-21)

- PR #15 redujo el lote SQL a 25 correos tras localizar el error de E/S en `executemany` de 500 filas. Se verificó en 7/7 pruebas aisladas, se fusionó como `1a28076` y se desplegó por fast-forward en PythonAnywhere con Reload successful. Vercel informó éxito.
- El lote histórico productivo `351a817e-772f-4cf1-8083-1b6ba674e5c5` está `CONFIRMADO`: 37.591 procesadas, 37.589 incorporadas, 1 registro del intento inicial reconocido por deduplicación y 1 error trazado. La tabla contiene 37.590 correos, todos vinculados al lote; hay 0 grupos MessageId duplicados y 9.314 filas en revisión.
- Respaldo privado previo, `integrity_check`, `production_check` y Alembic `0026` fueron verificados. No se restauró, sustituyó ni vació la SQLite productiva.
- QA web del dominio habitual PASS para sesión, dashboard, filtros, paginación, orden, detalle, historial y persistencia. La vista móvil queda `PENDIENTE QA MANUAL`, pues el navegador integrado no aplicó la emulación solicitada.
- n8n queda explícitamente fuera de este cierre y pendiente como trabajo independiente.

## Autorización vigente

El usuario autorizó el 2026-09-21 el cierre completo de la versión de Correos y seguimiento: correcciones, pruebas, PR, merge controlado, Vercel, PythonAnywhere, migraciones, carga histórica deduplicada, n8n de ingesta y QA en el dominio productivo. Esta autorización reemplaza las restricciones locales históricas, sin omitir protecciones de plataforma, controles de seguridad ni reglas de recuperación.

## Versión candidata y alcance

- La candidata `e6bd6298f33df6e285e852ccd009595371c799b9` fue integrada mediante el PR #12 con commit de merge `c857995d8203d39e43a0b16e8fbf46a85b3255c9`.
- Código funcional: `35860b5`; los cambios posteriores que llegaron mediante el merge son documentación de evidencia.
- Incluye Correos y seguimiento, las migraciones `0025_correos_seguimientos` y `0026_correos_operational_hardening`, catálogo/permiso `CORREOS`, endpoint n8n de mínimo privilegio y las correcciones heredadas de catálogo autorizadas.

## Preflight de producción y despliegue realizado

- GitHub autenticado como `hcastro01`, con acceso administrador a `hcastro01/SITS`. El PR #12 pasó sus checks observados, era mergeable y fue integrado con commit de merge; la rama de recuperación se preservó.
- Vercel existente: equipo `hector-f6fc`, proyecto `sits`, dominio productivo válido `sits-wheat.vercel.app`. El deployment Production de `c857995` está `Ready`.
- PythonAnywhere existente: aplicación ASGI de `hector00999.pythonanywhere.com`; el checkout avanzó con `git pull --ff-only` a `c857995`, se sincronizaron dependencias fijadas, se aplicaron las migraciones y se recargó la aplicación correctamente.
- El preflight de solo lectura pasó: configuración productiva, SQLite persistente, integridad, revisión Alembic actual, administrador con contraseña y credenciales de usuarios.
- Se creó un respaldo SQLite consistente antes de escribir en producción y se validó su apertura e integridad en modo solo lectura. La referencia y evidencia privada están en el manifiesto ignorado de recuperación.
- Alembic avanzó de `0024_contexto_medico_atenciones` a `0026_correos_operational_hardening (head)`. El inicializador confirmó las semillas idempotentes y el chequeo posterior de producción pasó.

## Pendiente controlado

1. Habilitar una vez el acceso local de la extensión de Chrome a archivos para que el navegador pueda transmitir el XLSX histórico verificado al importador productivo. El intento no llegó a enviar el archivo ni creó lote alguno.
2. Analizar y confirmar el lote en la UI; comprobar conteos, deduplicación, filtros, paginación, detalle y seguimiento con datos productivos.
3. Identificar una instancia autenticada de n8n y un workflow exclusivamente de ingesta. La clave de backend ya fue generada y guardada sólo en el entorno productivo; no se activará ningún workflow que opere el buzón.

## Recuperación

El backend anterior y el deployment Production anterior se conservan como puntos de recuperación. No se restaurará la base automáticamente: ante regresión se preservarán escrituras posteriores y se preferirá un arreglo hacia delante o una reversión de código compatible.

## Estado actual

`BLOCKED_EXTERNAL`: código y despliegues productivos completados. Faltan la transferencia controlada del XLSX por el permiso local de Chrome y el acceso a una instancia/workflow n8n aislado; no declarar cierre total hasta verificarlos.
