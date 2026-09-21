# Handoff técnico: Correos y seguimiento

## Checkpoint posterior (2026-09-21)

- Producción en `22d09e9` tras PR #13/#14; PythonAnywhere pasó `production_check`, integridad SQLite y Reload successful. La inserción XLSX ahora usa SQL por lotes y la prueba aislada `tests.test_correos` pasó 7/7, incluida carga de 1.001 filas.
- El XLSX real está ya analizado en producción y debe reanudarse desde el lote existente, no volver a transmitirse. Conteos de análisis: 37.591 / 28.276 / 9.314 / 1 (fuente/clasificadas/revisión/error).
- Una única fila parcial existe y el lote sigue `ANALIZADO`. La cookie de SITS se invalidó tras la recarga; iniciar sesión y confirmar una vez incluyendo revisión. Después realizar QA de sólo lectura. No crear seguimiento artificial ni activar n8n.

## Estado Git

- Rama: `codex/correos-n8n-production-readiness`.
- Base antes del checkpoint: `378c2dab040f4a531f561ccfa3af4ae0465bd858` (`merge: actualizar base desde origin/master`).
- Hay cambios locales del módulo Correos, de integración y de este handoff. No ejecutar `reset`, `clean`, merge ni despliegue.
- Se excluyen de cualquier commit `outputs/`, `diagrams/`, `AGENTS.md`, `.env`, bases locales y artefactos de recuperación. `outputs/` contiene el XLSX de prueba real y otros datos potencialmente privados.

## Objetivo actual

Cerrar **Trabajo Social → Correos y seguimiento**: XLSX → validación/importación → deduplicación → SQLite y trazabilidad → dashboard, filtros y detalle → API → n8n con autenticación de mínimo privilegio e idempotencia → pruebas y documentación.

## Trabajo terminado

### Datos y migraciones

- `0025_correos_seguimientos` crea `correos`, `lotes_importacion_correo` y `seguimientos_correo`; `id_externo_correo` (MessageId) e `idempotency_key` tienen restricciones únicas.
- `0026_correos_operational_hardening` amplía lotes con procesadas, duplicadas, omitidas, errores, origen y duración; agrega `correos.estado_categoria`, índice por estado de categoría y `errores_importacion_correo` con índices por lote/fila.
- `backend/app/models/correos.py` define los cuatro modelos. Las filas de error almacenan fila, MessageId, código y detalle, sin cuerpo, token ni secretos.

### Backend

- `backend/app/services/correos.py` lee XLSX con `openpyxl` en `read_only`, limita por `MAX_EMAIL_XLSX_BYTES` configurable (50 MiB por defecto), normaliza fechas a `America/Guayaquil`, conserva registros válidos y persiste errores por fila.
- La confirmación procesa todas las filas aptas, no sólo la vista previa de 100; la vista previa sigue acotada a 100. Duplicados en archivo o base se cuentan y no se insertan en silencio.
- `backend/app/api/correos.py` proporciona resumen, listado con filtros/paginación, detalle protegido, seguimiento, análisis/confirmación, historial/errores de lotes y `POST /api/v1/correos/integraciones/n8n`.
- El endpoint n8n acepta `Authorization: Bearer ...`, compara con `secrets.compare_digest` contra `N8N_SITS_API_KEY`, no usa cookie ni permiso general de SITS, y responde 201 creado o 200 idempotente. Credencial ausente/incorrecta: 401.
- `main.py`, el seed, el catálogo y la navegación registran el módulo `CORREOS`. Los cuerpos se exponen sólo en detalle sensible y el frontend los renderiza con `pre`, no HTML.

### Frontend e infraestructura

- `CorreosDashboardPage.tsx` tiene carga XLSX con extensión/tamaño, resumen de análisis, confirmación, historial, búsqueda/categoría/estado y paginación server-side, más detalle y seguimientos.
- `frontend/nginx.conf` y backend quedan en 50 MiB. Compose pasa `MAX_EMAIL_XLSX_BYTES` y `N8N_SITS_API_KEY`; el tmpfs del proxy se elevó a 96 MiB.
- `README.md` y `.env.example` documentan el entorno aislado y contrato de n8n sin una clave real.

## Trabajo parcialmente terminado

- La UI compila y construye, pero no se agregó ni ejecutó una suite Vitest específica de Correos. La prueba manual autenticada del navegador sigue pendiente.
- El XLSX real llegó por Nginx y se **analizó** correctamente, pero no se confirmó/importó: la sesión usada para el segundo request no fue reenviada por PowerShell. No afirmar importación E2E completa.
- El importador persiste el XLSX íntegro como BLOB en `lotes_importacion_correo`, herencia de 0025. Funciona en el entorno aislado, pero el siguiente agente debe evaluar coste de almacenamiento antes de cargas repetidas grandes.
- La página consulta historial, pero aún no muestra el detalle de errores de cada lote aunque el endpoint existe.

## Trabajo pendiente, en prioridad

1. Resolver y repetir la sesión HTTP/browser para confirmar el lote real ya analizado (`cb189146-a0c4-4628-8231-97b2bb67d5be`) o crear un lote nuevo; validar dashboard, filtros, detalle y SQL sin duplicados.
2. Configurar una clave efímera sólo en `sits-correos-local` y ejecutar E2E n8n por proxy: sin token 401, inválido 401, válido 201 y replay 200/único. Nunca imprimir la clave.
3. Ejecutar migración limpia `0024 → 0025 → 0026`, downgrade a 0024 y nuevo upgrade; verificar índices/constraints.
4. Añadir y correr tests frontend específicos de importación, errores, historial, filtros, paginación, detalle y KPI. Correr suites completas backend/frontend.
5. Revisar UX de errores por lote y el rendimiento de insertar/auditar decenas de miles de correos antes de declarar el módulo cerrado.

## Base de datos

- Head Alembic local: `0026_correos_operational_hardening`.
- Restricción natural: `correos.id_externo_correo` única; adicionalmente `idempotency_key` única.
- Índices existentes: fecha de recibido, categoría, estado, estado de categoría y errores por lote/fila. No se modificó ninguna base de producción.
- Orígenes guardados: `XLSX`, `N8N` o `MANUAL`; las categorías se distinguen como `VALIDA`, `SIN_CATEGORIA`, `DESCONOCIDA` u `OTROS`.

## Endpoints y n8n

- Sesión SITS: `GET /api/v1/correos/resumen`, `GET /api/v1/correos`, `GET /api/v1/correos/{id}`, `POST /api/v1/correos`, `POST /api/v1/correos/{id}/seguimientos`, `POST /api/v1/correos/importar/analizar`, `POST /api/v1/correos/importar/{lote}/confirmar`, historial y errores.
- Integración: `POST /api/v1/correos/integraciones/n8n`; variable requerida `N8N_SITS_API_KEY`; contrato `MessageId`, `Subject`, `From`, `To`, `CC`, `ReceivedTime`, `Importance`, `Body`, `HasAttachments`, `IsRead`, `Category`.
- No configurar n8n real ni producción durante la continuación sin autorización explícita.

## Docker/Nginx

- Proyecto aislado: `sits-correos-local`; frontend `http://localhost:18081`, backend `http://localhost:18000`.
- Al invocar Compose en una nueva consola, establecer siempre `$env:BACKEND_PORT='18000'` y `$env:FRONTEND_PORT='18081'`; omitirlos intenta ocupar 8000.
- Última comprobación: ambos contenedores saludables; la inicialización aplicó 0026 en el volumen aislado.

## Tests y evidencia

- `docker compose -p sits-correos-local exec -T backend python -m unittest discover -s tests -p 'test_correos*.py' -v`: **8/8 PASS**. Cubre XLSX, errores por fila, duplicación en BD, seguimiento, permisos y n8n sin/incorrecta/válida/idempotente.
- `cd frontend; npm.cmd exec tsc -- -b`: **PASS**.
- `cd frontend; npm.cmd run build`: **PASS**; warning existente de chunk >500 kB, no fallo.
- `git diff --check`: **PASS** antes de crear este handoff.
- XLSX real: 30,189,403 bytes, análisis HTTP por Nginx/backend **201** y lote `ANALIZADO`; 37,591 filas totales/procesadas, 28,276 clasificadas, 9,314 revisión, 1 error, 0 omitidas, duración registrada 21,694 ms. Confirmación/importación y validación visual: **NO VERIFICADAS**.

## NEXT ACTION

Instalar el navegador local solicitado por la herramienta, autenticar en `http://localhost:18081` con una cuenta QA local autorizada y verificar visualmente historial, filtros, detalle y móvil. El lote `cb189146-a0c4-4628-8231-97b2bb67d5be` ya está confirmado, por lo que no debe reconfirmarse ni incluir revisión de nuevo. Después, crear el PR cuando exista autenticación GitHub.

## Cierre productivo 2026-09-21

- El usuario autorizó la publicación completa; la especificación vigente es `docs/CODEX_PRODUCTION_MASTER.md`.
- Recuperación actual: candidata `e6bd629`, base `08246df`, GitHub autenticado y sin PR abierto. Vercel `hector-f6fc/sits` y PythonAnywhere `hector00999` están disponibles.
- PythonAnywhere fue comprobado en modo solo lectura, respaldado y luego actualizado por avance rápido a `c857995`; dependencias fijadas, `app.cli.initialize`, Alembic `0026_correos_operational_hardening`, `production_check` y Reload pasaron. La referencia privada del respaldo está fuera de Git.
- El PR #12 fue integrado mediante commit de merge `c857995`. Vercel lo publicó como Production `Ready`; el dominio habitual abrió con sesión administrativa y el módulo Correos disponible. No volver a confirmar ni reimportar el lote local.
- La importación productiva aún no se ejecutó: la extensión de Chrome bloqueó el acceso al XLSX antes de enviar bytes. Habilitar el acceso a URLs de archivo de la extensión y continuar sólo con el XLSX prevalidado, una vez; revisar el lote antes de confirmarlo. n8n permanece inactivo hasta identificar una instancia autenticada y un flujo exclusivamente de ingesta.

## Actualización 2026-09-21

- Estado SQL comprobado: lote `CONFIRMADO`, 37.591 procesadas, 37.590 importadas, 0 duplicadas, 0 omitidas, 1 error; 37.592 correos activos en total y 0 grupos `MessageId` duplicados. La confirmación consta en auditoría a las `2026-09-21T05:39:07Z`, anterior a esta continuación.
- El historial UI permite ahora abrir incidencias y confirmar sólo lotes aún `ANALIZADO`; se expusieron todos los filtros que el backend ya ofrece. Las pruebas de componente de Correos son 4/4 PASS.
- Se corrigieron dos regresiones: metadata de índices ORM versus migraciones, y permiso sensible implícito para roles no administradores. No se reescribieron 0025/0026.
- Validaciones finales: backend 324/324 PASS; frontend 156/156 PASS; TypeScript y build PASS; migración desechable ida/vuelta PASS; n8n HTTP local: 401/401/201/200/422/401 según escenario.
- No se completó QA visual autenticado porque el navegador requerido no está instalado. No existe PR abierto y `gh` no está autenticado. No hubo producción, merge ni workflow n8n real.
- Los cambios de esta actualización se publicaron en `f139c6d` sobre `origin/codex/correos-n8n-production-readiness`.

## Actualización de cierre QA 2026-09-21

- Se usó el navegador integrado aislado como alternativa válida al wrapper gstack defectuoso en Windows. Login local normal, navegación accesible, dashboard, historial, incidencia, filtros combinados, orden, vacío, paginación, detalle y seguimiento fueron comprobados. La vista 390×844 también mostró el módulo y un resultado sintético; la consola quedó sin errores ni advertencias.
- Se corrigieron dos defectos detectados por QA: el login local no reflejaba `development_email`, y un seguimiento exitoso mostraba falso error después de recibir `201`. Ambos tienen pruebas unitarias/regresión.
- El fixture XLSX sintético, no versionado, produjo un lote `CONFIRMADO` con 3 procesadas, 1 importada, 1 revisión y 1 error. El lote real se preservó sin reimportar ni alterar.
- Pruebas posteriores al cambio: backend 325/325, frontend 158/158, TypeScript/build y smoke Docker PASS. Los logs y fixture locales están en `outputs/`, excluidos de Git.
- El checkpoint `35860b5` quedó publicado y coincide en local/upstream/remoto. Próxima acción externa: iniciar sesión en GitHub con el usuario autorizado, crear/actualizar el PR hacia `master`, y revisar checks de ese SHA. No merge ni producción.
