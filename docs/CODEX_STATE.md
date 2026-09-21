# Estado operativo

## Checkpoint posterior de cierre (2026-09-21, 11:50 UTC)

- `master` productivo está en `22d09e9fbfccefaa3138320f096b4d170b48b58e` (PR #14, merge commit). PythonAnywhere avanzó sólo con `git pull --ff-only`, pasó `production_check` y confirmó `Reload successful`; Vercel terminó los checks observados.
- Se verificaron respaldos privados consistentes antes de cada actualización productiva, `PRAGMA integrity_check = ok`, Alembic `0026_correos_operational_hardening (head)` y 1 registro existente en `correos`.
- El XLSX histórico ya fue analizado una vez en producción: 37.591 fuente, 28.276 clasificadas, 9.314 en revisión y 1 error. El lote permanece `ANALIZADO`, con 0 importadas y 0 duplicadas; no se debe volver a analizar ni crear un lote nuevo.
- El intento inicial detectó E/S de SQLite y dejó una única fila parcial, conservada para deduplicación. PR #13 redujo escrituras ORM por fila y PR #14 usa inserción SQL por bloques; ambos pasaron Vercel. La reanudación posterior no escribió porque la sesión del navegador fue invalidada tras la recarga.
- Bloqueo actual: iniciar sesión nuevamente en el dominio habitual para confirmar exactamente ese lote; después validar conteos, filtros, paginación y detalle sin crear seguimientos de prueba. n8n sigue sin instancia autenticada.

## Cierre productivo en curso (2026-09-21)

- La misión vigente está en `docs/CODEX_PRODUCTION_MASTER.md`; sustituye los límites locales históricos dentro de su alcance.
- GitHub, Vercel y PythonAnywhere fueron autenticados y comprobados. El PR #12 se integró con commit de merge `c857995d8203d39e43a0b16e8fbf46a85b3255c9`; la rama de recuperación permanece publicada.
- El backend productivo avanzó con `git pull --ff-only` a `c857995`, las dependencias fijadas se sincronizaron y el esquema avanzó de `0024_contexto_medico_atenciones` a `0026_correos_operational_hardening (head)`. El inicializador idempotente y el chequeo de producción posterior pasaron.
- El respaldo SQLite previo al cambio fue consistente, abrió en solo lectura y pasó `integrity_check`. Sus identificadores privados permanecen en `recovery/production-deployment-manifest.md`, ignorado por Git.
- PythonAnywhere confirmó `Reload successful`. Vercel publicó `c857995` como Production `Ready`; el dominio habitual cargó con sesión administrativa y el módulo Correos mostró correctamente su estado inicial vacío.
- Siguiente acción bloqueada localmente: permitir a la extensión de Chrome acceso a archivos y volver a analizar el XLSX histórico en producción; no se ha transmitido el archivo ni creado un lote productivo.

- Rama: `codex/correos-n8n-production-readiness`; checkpoint de código y QA publicado en `35860b5` (HEAD local, upstream y remoto coinciden).
- Entorno aislado saludable: backend `18000`, frontend `18081`, SQLite local en revisión `0026_correos_operational_hardening`.
- El lote real `cb189146-a0c4-4628-8231-97b2bb67d5be` está confirmado desde `2026-09-21T05:39:07Z`: 37.591 procesadas, 37.590 importadas, 0 duplicadas, 0 omitidas y 1 error. Incluyó las filas en revisión antes de esta continuación; no se revierte ni se repite.
- Integridad local comprobada: 37.593 correos activos, 0 grupos `MessageId` duplicados, 1 error del lote histórico y 0 seguimientos huérfanos. Dos correos son pruebas n8n locales y uno proviene del fixture UI sintético.
- UI ampliada: historial permite ver errores y confirmar sólo lotes `ANALIZADO`; filtros server-side completos expuestos. Las pruebas de componente pasan 4/4.
- Validación final automatizada de código: backend 325/325 PASS; frontend 158/158 PASS; TypeScript PASS; build PASS con advertencia existente de chunk de 535.81 kB.
- QA visual autenticado completado en el navegador aislado integrado: login por flujo normal local, navegación accesible al módulo, dashboard, historial y error, detalle sensible sintético, seguimientos, filtros, vacío, orden, paginación, recarga y viewport 390×844. Consola sin errores/advertencias. No se guardaron capturas ni trazas con datos reales.
- Un fixture XLSX sintético fue analizado y confirmado desde UI: 3 procesadas, 1 clasificada importada, 1 revisión preservada y 1 error persistido. Es independiente del lote histórico.
- GitHub: PR abierto=0. La única comprobación pública observada fue `Vercel Preview Comments`, finalizada con `success` tanto para `35860b5` (código) como para `da18465` (documentación); no se interpreta como sustituto de un PR ni de una suite CI completa.
- Producción y merge: realizados. n8n real: no realizado; no existe una instancia autenticada ni un workflow de ingesta aislado identificado. La clave del backend fue generada exclusivamente en la configuración productiva, sin exposición ni activación de workflows.
