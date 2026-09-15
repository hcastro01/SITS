# Avance técnico por bloques — SITS

Actualizado: 15 de septiembre de 2026.

## Contexto verificado

- Rama actual: `feature/sits-expansion` (se conserva; no se cambió de rama).
- Plan reutilizado: `MIGRACION_FASE_1.md`. Su encabezado aún declara la Fase 1 como propuesta y no identifica un bloque en curso.
- La especificación vigente es `Prompt_Codex_SITS_Ejecucion_Por_Bloques.md`; sustituye la navegación anterior descrita en `docs/SITS_EXPANSION_SPEC.md` cuando haya conflicto.
- Hay cambios locales preparados, que no fueron modificados: modelo `ModuloSistema`, migración `0013_catalogo_modulos`, semilla `seed_module_catalog` y su llamada desde `backend/app/start.py`.
- Al inicio del bloque, esos cambios representaban la navegación anterior (por ejemplo, «Gestión Operativa» y «Módulos próximos») y el `Layout.tsx` era plano. El resultado de este bloque se registra más abajo.
- La migración `0013_catalogo_modulos` depende de `0012_integracion_modulos`; esto coincide con el head de migraciones inspeccionado. Antes de aplicarla deberá validarse contra el modelo completo de metadatos y mediante una base temporal.
- No hay Python disponible en PATH (`py`, `python` y `python3` no están instalados), por lo que en este entorno no se ejecutaron pruebas backend.

## Bloque completado

**Fase 1 — Catálogo de navegación y sidebar jerárquico** (autorizado el 15 de septiembre de 2026).

### Implementado

- El sidebar reutiliza `Layout.tsx` y ahora presenta el árbol de Trabajo Social, Repositorio de formularios y Administración. Los grupos se despliegan y contraen, conservan la navegación móvil y el modo colapsado.
- Una ruta hija canónica de Producción deja expandidos Trabajo Social y Producción. El elemento activo sigue marcado mediante `NavLink`.
- Se añadieron rutas canónicas para Inicio y los listados existentes de Producción: `/trabajo-social/inicio`, `/trabajo-social/produccion/atenciones`, `/trabajo-social/produccion/recorridos` y `/trabajo-social/produccion/novedades`. Las rutas anteriores `/`, `/atenciones`, `/recorridos` y `/novedades` se conservan.
- Casos, Personas y Búsqueda mantienen sus rutas compatibles existentes, pero ya no aparecen como accesos principales del sidebar.
- Los subprocesos que aún no tienen persistencia ni pantalla propia se muestran sin enlace: no redirigen a datos de otro proceso ni aparentan estar implementados. Los accesos Formularios reutilizan el repositorio central existente.
- La migración `0013_catalogo_modulos` incluye el campo heredado `motivo_eliminacion`; el modelo y la tabla coinciden. La semilla define el árbol nuevo de forma aditiva e idempotente y añade sólo los permisos de los módulos nuevos.

### Archivos modificados o creados

- `frontend/src/app/Layout.tsx`, `frontend/src/styles.css`, `frontend/src/app/App.tsx` y `frontend/src/app/Layout.test.ts`.
- `backend/app/models/security.py`, `backend/app/services/security_seed.py`, `backend/migrations/versions/0013_catalogo_modulos.py` y `backend/tests/test_navigation_catalog.py`.
- Este documento de avance.

### Pruebas ejecutadas

- `frontend: npm test` — aprobado.
- `frontend: npm run build` — aprobado; TypeScript y Vite completaron el build de producción.
- `git diff --check` y `git diff --cached --check` — aprobados, sin errores de espacios.

### Pruebas no ejecutadas

- `docker compose run --rm --no-deps backend python -m unittest tests.test_navigation_catalog` no se pudo iniciar porque el daemon de Docker Desktop no está activo (`dockerDesktopLinuxEngine` no existe). No hay intérprete Python local disponible. No se ejecutó ninguna migración ni se modificó una base de datos.

## Próximo bloque recomendado

Esperar autorización explícita para el siguiente bloque. No avanzar automáticamente a Fase 2.

## Fase 2 — Actividades

En curso: se confirmó que Compromisos y Seguimientos dependen de Casos y no se reutilizaron. Se creó `Actividad` independiente, con responsable y autor como FK de usuario, Persona opcional, auditoría, versión y archivado lógico.

- Migración nueva: `0014_actividades`, posterior a `0013_catalogo_modulos`; no ejecutada.
- API: `/api/v1/actividades` para listado paginado, creación, detalle, edición y archivado; `/opciones` entrega usuarios activos y Personas.
- Frontend: tabla y registro en las rutas de Actividades. Adjuntos/BLOB y la integración global de destinos de Formularios siguen pendientes de sus bloques específicos.
- Validación realizada: `npm run build` y `npm test` (38 pruebas existentes aprobadas). Las pruebas backend no se ejecutaron por la limitación documentada de Python/Docker.
- Pendientes de Fase 2 completados: filtros combinables por responsable, estado, tipo, fecha desde/hasta y Mis actividades; la tabla conserva filtros al paginar y muestra total/páginas calculadas desde la respuesta backend.
- Revalidación: `npm run build`, `npm test` (9 archivos, 38 pruebas) y `git diff --check` aprobados. Python sigue siendo el alias de Microsoft Store y Docker no devolvió un servidor activo; no se ejecutaron pruebas backend ni migraciones.
- Cierre de pruebas Fase 2: se añadieron `frontend/src/features/actividades/ActividadesPage.test.tsx` y `backend/tests/test_actividades.py`. Docker ya pudo crear una red y un contenedor de prueba; el primer comando falló porque la prueba aún no estaba incluida en la imagen. La ejecución Vitest con las nuevas pruebas quedó bloqueada antes de reportar resultados (el intento sin límite de workers informó un fallo de asignación de memoria).
- La suite aislada de Actividades quedó corregida (mocks hoisted y aserciones sobre `URLSearchParams`): 4 pruebas aprobadas con un worker. El build posterior detectó sólo nulabilidad estática en esas aserciones y se corrigió; queda pendiente su ejecución final junto con la reconstrucción y prueba backend de la imagen.
- Cierre final: imagen backend reconstruida y `test_actividades.py` visible/ejecutado en Docker (1/1 aprobado). `alembic upgrade 0014_actividades` se ejecutó contra `sqlite:////tmp/activities-test.db` dentro de un contenedor desechable. La suite aislada frontend Actividades pasó 4/4; la suite completa no alcanzó a finalizar en esta ejecución.
- Cierre técnico reanudado: `npm test` volvió a agotarse por memoria del entorno antes de informar resultados. Con un worker, los 10 archivos se ejecutaron de forma aislada: 42/42 pruebas aprobadas (incluidas Actividades 4/4). `npm run build` aprobó. Se amplió `backend/tests/test_actividades.py` para cubrir creación, sesión/autorización, responsable, persona, filtros, listado, edición, finalización, archivado y vencimiento. Su ejecución y la validación nueva de 0014 quedaron pendientes: Docker Desktop no pudo iniciar (`Docker Desktop is unable to start`) y el Python local no tiene Alembic instalado (`ModuleNotFoundError: alembic`). La sintaxis de la prueba nueva fue validada con `py_compile`.
- Cierre final: Docker Desktop operativo; imagen backend reconstruida para incluir los 8 casos de Actividades. `tests.test_actividades` aprobó 8/8. La suite backend ejecutó 208 pruebas: 206 aprobadas y 2 fallos ajenos a Actividades por expectativas heredadas de 90 permisos frente a los 125 del catálogo vigente (`test_admin_service` y `test_bootstrap`). Se corrigió la declaración ORM del índice compuesto `ix_actividades_estado_fecha_objetivo` para que coincida con 0014; la comprobación de metadatos ya aprueba. Sobre `/tmp/phase2-0014.db` dentro de un contenedor desechable, 0014 hizo upgrade con estructura e índice verificados, downgrade a 0013 y upgrade final correctamente. Frontend: los 10 archivos se ejecutaron secuencialmente con un worker (42/42) y build aprobado; se evitó el OOM de `npm test` paralelo.
- Cierre validado: las dos expectativas heredadas de permisos fueron actualizadas de 90 a 125, el valor real de `len(MODULES) * len(ROLES)` (25 módulos por 5 roles), sin modificar el seed ni la lógica de autorización. Las dos pruebas y Actividades aprobaron 10/10; la suite backend completa aprobó 208/208. Se mantienen aprobados frontend 42/42, build, ciclo temporal de 0014 y `git diff --check`.

### Cierre formal de Fase 2

**FASE 2 VALIDADA.** Backend completo 208/208; Actividades backend 8/8; frontend completo 42/42; build frontend aprobado; migración `0014_actividades` validada mediante upgrade, downgrade y upgrade final sobre SQLite temporal; `git diff --check` aprobado. No existen pendientes técnicos conocidos dentro del alcance de la Fase 2.

## Revisión técnica de Fase 1

Resultado: **FASE 1 VALIDADA — lista para pasar a Fase 2.**

### Correcciones de la revisión

- Cada destino del árbol tiene ahora una ruta canónica. Los listados ya existentes de Producción reutilizan sus componentes actuales; Formularios reutiliza el repositorio único existente; los destinos sin flujo operativo usan una vista base honesta y no consultan ni muestran datos de otro proceso.
- Se sincronizaron las rutas del catálogo `MODULOS_ARQUITECTURA` con las rutas del sidebar.
- En móvil, abrir el menú muestra los niveles hijos incluso si el sidebar se había colapsado previamente en escritorio.

### Inventario de rutas de la jerarquía

| Destino | Ruta | Estado |
|---|---|---|
| Inicio | `/trabajo-social/inicio` | Dashboard existente |
| Actividades / Tabla | `/trabajo-social/actividades` | Vista base |
| Actividades / Registrar | `/trabajo-social/actividades/registrar` | Vista base |
| Actividades / Formularios | `/trabajo-social/actividades/formularios` | Repositorio único |
| Departamento Médico / Riesgos | `/trabajo-social/departamento-medico/riesgos` | Vista base |
| Departamento Médico / Ausentismos | `/trabajo-social/departamento-medico/ausentismos` | Vista base |
| Departamento Médico / Accidentes | `/trabajo-social/departamento-medico/accidentes` | Vista base |
| Departamento Médico / Formularios | `/trabajo-social/departamento-medico/formularios` | Repositorio único |
| Producción / Atenciones | `/trabajo-social/produccion/atenciones` | Listado existente |
| Producción / Recorridos | `/trabajo-social/produccion/recorridos` | Listado existente |
| Producción / Novedades | `/trabajo-social/produccion/novedades` | Listado existente |
| Producción / Formularios | `/trabajo-social/produccion/formularios` | Repositorio único |
| Oficina / Beneficios | `/trabajo-social/oficina/beneficios` | Vista base |
| Oficina / Atenciones | `/trabajo-social/oficina/atenciones` | Vista base |
| Oficina / Préstamos | `/trabajo-social/oficina/prestamos` | Vista base |
| Oficina / Seguro | `/trabajo-social/oficina/seguro` | Vista base |
| Oficina / Formularios | `/trabajo-social/oficina/formularios` | Repositorio único |
| Repositorio de formularios | `/formularios` | Existente |
| Usuarios | `/admin/usuarios` | Existente |
| Roles y permisos | `/admin/permisos` | Existente |

Las rutas históricas `/`, `/atenciones`, `/recorridos`, `/novedades`, `/casos`, `/personas` y `/busqueda` permanecen declaradas. No se eliminaron enlaces internos. No existían breadcrumbs en el `Layout` anterior, por lo que no hubo ninguno que conservar o modificar.

### Validación estática y pruebas

- Revisados modelo, semilla, referencias padre-hijo, identificadores `sits-*`, `revision`, `down_revision`, `upgrade()` y `downgrade()` de `0013_catalogo_modulos`.
- La migración crea exclusivamente la tabla nueva `modulos` y sus índices sobre `0012_integracion_modulos`; no modifica migraciones anteriores ni elimina datos. La semilla pobladora es aditiva y sólo inserta IDs inexistentes.
- `npm test`: 9 archivos, 38 pruebas aprobadas.
- `npm run build`: aprobado.
- `git diff --check` y `git diff --cached --check`: aprobados; sólo quedaron advertencias de normalización LF/CRLF.
- La prueba backend sigue sin ejecutarse: Python no está disponible localmente y el daemon Docker no estaba activo. No se reintentó ni se ejecutó una migración.

## Fase 3 — Bloque 2: importación de Ausentismos

**BLOQUE 2 FASE 3 VALIDADO.** Se implementó la importación XLSX de Ausentismos con lotes e incidencias persistentes, análisis/previsualización sin inserciones y confirmación transaccional TODO-O-NADA. El historial, detalle y errores paginados están disponibles bajo `/api/v1/importaciones/ausentismos`.

- Migración `0016_lotes_importacion_ausentismo` validada en SQLite temporal mediante upgrade, downgrade a `0015_ausentismos` y upgrade final.
- Pruebas específicas de importación: 18/18 aprobadas.
- Suite backend: 234/234 aprobadas.

Próximo bloque previsto: frontend del flujo de importación de Ausentismos.

## Fase 3 — Bloque 3: frontend de importación de Ausentismos

**BLOQUE 3 FASE 3 VALIDADO.** La ruta de Ausentismos ahora consume los endpoints reales de importación para analizar XLSX, consultar incidencias paginadas, confirmar mediante el identificador del lote e inspeccionar historial/detalle. No se modificó el backend, migraciones ni permisos globales.

- Pruebas específicas de Ausentismos frontend: 7/7 aprobadas.
- Suite frontend completa: 49/49 aprobadas en 11 archivos, ejecutados secuencialmente con un worker para evitar el OOM conocido de la ejecución paralela.
- Build frontend y `git diff --check`: aprobados.

Pendientes reales dentro de Fase 3: ninguno para este bloque. Siguiente bloque previsto: tabla operativa de registros de Ausentismos; requiere autorización explícita.

## Fase 3 — Bloque 4A: backend de registros operativos de Ausentismos

**BLOQUE 4A FASE 3 VALIDADO.** Se agregó la consulta operativa individual sin implementar frontend. Los Ausentismos confirmados desde XLSX conservan en adelante un vínculo verificable con su lote; los históricos no se reclasifican y devuelven autor, lote y origen como `null` cuando no existen.

- Endpoints protegidos por `AUSENTISMO:read`: `GET /api/v1/ausentismos` y `GET /api/v1/ausentismos/{ausentismo_id}`.
- Listado paginado por `limite` y `offset`, con total; ordena por `fecha_inicio` descendente e `id_ausentismo` descendente. Filtros combinables: nombre, cédula textual, área actual de Persona, tipo, fecha desde/hasta, `lote_id` y origen verificable `IMPORTACION_XLSX`.
- El contrato devuelve solo datos operativos: Persona, cédula, área, fechas, tipo, motivo, observación, fecha de registro, lote y autor del lote cuando la relación real existe. No devuelve BLOB ni información médica adicional.
- Migración `0017_registros_operativos_ausentismos`: agrega `ausentismos.lote_id` opcional con FK e índice, posterior a `0016`; validada en SQLite temporal mediante upgrade, downgrade a `0016` y upgrade final.
- Pruebas HTTP específicas nuevas: 4/4 aprobadas; cubren listado, paginación, total, detalle, no encontrado, Persona/cédula/área, filtros combinables, lote, origen, autor y permisos. Regresión de importación: 18/18 aprobadas, incluida la asignación de `lote_id` al confirmar.
- Suite backend completa: 238/238 aprobadas. `git diff --check`: aprobado.

Pendientes reales dentro de Bloque 4A: ninguno. Siguiente bloque previsto: frontend de registros operativos de Ausentismos; requiere autorización explícita. No se inició Bloque 4B.

## Fase 3 — Bloque 4B: frontend de registros operativos de Ausentismos

**BLOQUE 4B FASE 3 VALIDADO.** La pestaña Registros consulta Ausentismos individuales; ya no presenta lotes confirmados como si fueran registros operativos. Importar XLSX y el Historial de cargas conservan sus flujos separados.

- Cliente nuevo `frontend/src/api/ausentismos.ts` conectado a `GET /api/v1/ausentismos` y `GET /api/v1/ausentismos/{ausentismo_id}`.
- Tabla responsive con Persona, cédula textual, área actual, tipo, fechas, motivo, registrado por, origen y acción de detalle. Los datos no verificables se presentan como “Sin información”, sin inventar autor, origen ni área histórica.
- Filtros server-side combinables: nombre, cédula, área, tipo, fecha desde/hasta, origen y lote; incluye limpiar filtros y reinicia el offset al aplicarlos.
- Paginación compatible con `items`, `total`, `limite` y `offset`, con rango actual, anterior/siguiente y conservación de filtros.
- El detalle usa el Modal accesible existente y muestra observación, lote y metadatos reales. Al confirmar una importación, la consulta de Registros se refresca.
- Pruebas específicas de Ausentismos frontend: 12/12 aprobadas. Suite frontend completa: 54/54 aprobadas en 11 archivos con un worker. `npm run build` y `git diff --check`: aprobados.

Pendientes reales dentro de Bloque 4B: ninguno. Siguiente bloque previsto: Bloque 5 — integración y cierre de Ausentismos; requiere autorización explícita. No se inició Bloque 5.

## Fase 3 — Bloque 5: integración y cierre de Ausentismos

**FASE 3 — AUSENTISMOS COMPLETADA.** Se cerró la integración de los bloques 1 a 4B sin iniciar módulos nuevos ni modificar la matriz global de permisos.

- Bloque 1: análisis y reglas canónicas de importación de Ausentismos.
- Bloque 2: importación XLSX persistente, lotes, incidencias, confirmación transaccional y historial.
- Bloque 3: frontend de análisis, confirmación e historial de cargas.
- Bloque 4A: API de registros individuales, filtros, detalle y trazabilidad lote/autor/origen.
- Bloque 4B: tabla frontend de registros individuales, filtros server-side, paginación y detalle operativo.
- Integración validada en SQLite temporal: XLSX válido crea Ausentismos vinculados al lote y a su autor; errores y duplicados bloquean confirmación sin inserciones parciales; la doble confirmación es rechazada. Registros y detalle exponen lote, autor y origen verificables; los históricos sin procedencia permanecen en `null` y la UI muestra “Sin información”.
- Migraciones verificadas: `0015_ausentismos` → `0016_lotes_importacion_ausentismo` → `0017_registros_operativos_ausentismos` → head, con tablas, FK e índice `ix_ausentismos_lote_id`; downgrade a 0016 y upgrade final aprobados en SQLite temporal.
- Pruebas específicas de integración backend existentes: 22/22 aprobadas (`test_importaciones_ausentismos` y `test_ausentismos_operativos`). Suite backend completa: 238/238 aprobadas.
- Frontend: 54/54 pruebas aprobadas en 11 archivos con un worker; `npm run build` aprobado. La regresión de navegación y sidebar está cubierta por la suite existente.
- `git diff --check`: aprobado.

Pendientes reales de Ausentismos en Fase 3: ninguno. No se inició Fase 4.

## Módulo actual posterior a Fase 3 — Accidentes

**ACCIDENTES COMPLETADA Y COMMITTEADA EN `5491b66`.** Se implementó el módulo de Accidentes del Departamento Médico sin renumerar el histórico previo. Esta denominación identifica el siguiente bloque funcional tras el cierre de Fase 3; la numeración futura deberá continuar desde este punto de forma explícita.

- Backend: registro manual, listado paginado, detalle, edición, filtros combinables, vínculo con Persona, estados, clasificación y autorización por módulo.
- Importación XLSX: análisis previo sin crear Accidentes, validación de columnas y archivo, incidencias persistentes, duplicados dentro del archivo y contra la base, confirmación atómica, bloqueo de doble confirmación e historial de lotes.
- Frontend: pantalla integrada en Departamento Médico para registros, filtros, paginación, detalle, registro manual, análisis XLSX, confirmación e historial de importaciones.
- Migración `0018_accidentes`: validada en SQLite temporal.
- Permisos: validados en backend; usuario sin permiso recibe rechazo de autorización.
- Pruebas específicas de Accidentes: 2/2 aprobadas. Validación funcional controlada: aprobada.
- Frontend: 54/54 pruebas aprobadas; build de producción aprobado.
- Suite backend global: 231/240 aprobadas y 1 error de teardown. Los 9 fallos y el error también ocurren en el baseline `3a79689bb05af52fbda4d80b105554fee8ac9e6f` (229/238 y 1 error), por lo que son preexistentes y no atribuibles a Accidentes.
- `git diff --check`: aprobado.

## Fase 5 — Repositorio central y asignación de Formularios

### Bloque 1 — Auditoría y diseño técnico

**Estado: VALIDADO.**

- Documento técnico: `docs/SITS_FASE5_FORMULARIOS_DISENO.md`.
- Arquitectura reutilizable verificada: Formulario, FormularioDestino, FormularioVersion, EnvioFormulario, RespuestaFormulario, constructor visual, renderizador dinámico, integraciones por módulo/contexto, códigos, auditoría y permisos existentes.
- Gaps identificados: destinos planos por módulo, ausencia de catálogo Macroproceso → Proceso → Subproceso y ausencia de un destino real persistido por respuesta.
- Modelo objetivo acordado: catálogo jerárquico de destinos, asignaciones permitidas por plantilla sin duplicarla y destino real nullable por envío, separado del contexto existente.
- Compatibilidad: los formularios, envíos, IDs, versiones, códigos, Personas, auditoría y contextos históricos permanecen sin reclasificación automática; los ambiguos quedan sin clasificación nueva.
- Siguiente bloque: implementación backend/modelo de destinos de formularios, incluida nueva migración posterior a `0018_accidentes`, sin iniciar todavía frontend jerárquico.

Fase 5 no está completada: este registro cierra únicamente su Bloque 1.

### Bloque 2 — Backend/modelo de destinos jerárquicos

**Estado: VALIDADO.**

- Se creó `DestinoFormulario` / `destinos_formulario`, catálogo autorreferente con macroproceso, procesos y subprocesos funcionales; no incluye elementos de interfaz.
- La migración `0019_destinos_jerarquicos_formularios`, posterior a `0018_accidentes`, agregó el catálogo, FKs e índices, una referencia nullable desde `formulario_destinos` y `id_destino_respuesta` nullable en `envios_formulario`.
- `formulario_destinos` conserva el campo textual histórico y ahora admite varias asignaciones jerárquicas sin duplicar la plantilla; el retiro es lógico y no afecta respuestas previas.
- Las respuestas nuevas validan destino existente, activo, subproceso de Trabajo Social y asignado a la plantilla; el destino real se devuelve y una respuesta no se consulta bajo otro destino.
- La semilla de 16 destinos es aditiva e idempotente. No se realizó backfill ni reclasificación histórica.
- Endpoints backend añadidos bajo `/api/v1/formularios` para árbol, destinos activos, asignaciones por plantilla y respuestas por destino.
- Validación: pruebas relacionadas 46/46, suite backend completa 247/247, `alembic check` sobre SQLite temporal sin operaciones nuevas, ciclo SQLite 0018 → 0019 → 0018 → 0019 aprobado y `git diff --check` pendiente de la comprobación final del bloque.

Fase 5 no está completada: el siguiente bloque será el frontend jerárquico, filtros/vistas por rama y regresión integral.

### Bloque 3 — Frontend del Repositorio central y gestión visual de destinos jerárquicos

**Estado: VALIDADO.**

- El único acceso sigue siendo el Repositorio central de Formularios; se reutilizan `FormulariosAdminPage` y `FormBuilderPage`, sin crear otro motor, constructor ni repositorios por módulo.
- El repositorio carga el árbol real desde `/formularios/destinos`, presenta los destinos de cada plantilla con nombres legibles y filtra por macroproceso, proceso y subproceso mediante IDs del catálogo.
- El constructor carga asignaciones desde `/formularios/{id_formulario}/destinos` y las sincroniza por PUT con IDs reales. Permite varios subprocesos en una plantilla, retiro lógico, loading, error, guardado sin doble envío y refresco tras éxito.
- Los textos heredados siguen visibles como «Destino histórico sin clasificación jerárquica» y no se infieren ni reclasifican.
- La gestión visual respeta `FORMULARIOS:edit`; lectura, errores 401/403 y estado vacío se comunican sin sustituir la autorización backend.
- Validación frontend específica: 26/26 aprobadas. Regresión frontend completa: 77/77 aprobadas en 13 archivos con un worker; build y `git diff --check` aprobados.

Fase 5 no está completada: el siguiente bloque previsto es la vista contextual por rama; no se inició en este bloque.

### Bloque 4 — Vistas contextuales de Formularios por rama

**Estado: VALIDADO.**

- Las rutas existentes de Formularios de Actividades, Departamento Médico, Producción y Oficina reutilizan una única vista contextual configurable; no se crearon rutas paralelas, plantillas nuevas ni repositorios por módulo.
- El catálogo real resuelve cada rama por código estable y filtra exclusivamente asignaciones jerárquicas explícitas a sus subprocesos autorizados. No hay herencia desde procesos ni inferencia desde nombres, rutas, destinos textuales históricos o formularios sin destino.
- El filtro Todos realiza la unión sin duplicados por formulario; los filtros específicos preservan el comportamiento multidestino. Las asignaciones de otras ramas no se muestran.
- La vista conserva loading, estados vacíos, errores HTTP incluidos 401/403, acceso al Repositorio central y administración solo con `FORMULARIOS:edit`. El destino real de la respuesta no se modificó.
- Validación frontend específica: 5/5 aprobadas. Regresión frontend completa: 82/82 aprobadas en 14 archivos. Build y `git diff --check` aprobados.

Fase 5 no está completada: el siguiente bloque previsto es Bloque 5 — destino real de respuesta y respuestas contextualizadas; no se inició en este bloque.

### Bloque 5 — Destino real de respuesta y respuestas contextualizadas

**Estado: VALIDADO.**

- `DynamicResponsePage` reutiliza el motor y renderizador existentes y envía `id_destino_respuesta` con el request de respuesta cuando corresponde.
- Un único destino jerárquico activo se selecciona automáticamente y se muestra con ruta legible. En vistas contextuales se conserva el subproceso ya determinado; desde Todos, un formulario multidestino exige elegir exactamente un destino permitido, activo y compatible con la rama.
- Formularios y respuestas históricas sin clasificación jerárquica conservan `id_destino_respuesta = null`; no hay inferencia desde texto, contexto, Persona, URL ni nombres. La edición conserva el destino original.
- La vista contextual consulta las respuestas solo por el endpoint existente del subproceso seleccionado; no mezcla respuestas de otros destinos ni históricos sin destino.
- Validación frontend específica: 24/24 aprobadas. Regresión frontend completa: 101/101 aprobadas en 15 archivos. Build y `git diff --check` aprobados. No hubo cambios backend; las pruebas backend específicas no se ejecutaron porque el entorno Python local no tiene `pytest` disponible.

### Bloque 6 — Integración, regresión y cierre

**Estado: VALIDADO Y COMPLETADO.**

- Se confirmó que el Repositorio central sigue siendo único: las vistas de Actividades, Departamento Médico, Producción y Oficina son filtros contextuales de las mismas plantillas, sin repositorios ni duplicación física por rama.
- La integración existente cubre una plantilla asignada a Recorridos y Novedades de planta: una respuesta enviada a Recorridos persiste `id_destino_respuesta` de Recorridos, se lista allí y no bajo Novedades; tras el retiro lógico, el histórico se conserva y nuevos envíos a Recorridos se rechazan. La misma validación de asignación, aislamiento y retiro se aplica a los demás subprocesos explícitos.
- Se verificaron catálogo real, códigos únicos, relación padre-hijo, 16 destinos activos e idempotencia. En SQLite temporal y desechable: `0018_accidentes → 0019_destinos_jerarquicos_formularios → head`, tabla `destinos_formulario`, FK autorreferente `padre_id_destino`, FKs de asignación/respuesta, índice `ix_envios_formulario_id_destino_respuesta` y segunda siembra sin duplicados.
- Históricos con destinos textuales o respuestas sin destino jerárquico permanecen sin clasificación nueva. Persona, contexto, versiones/snapshots, códigos/correlativos, idempotencia y auditoría se preservan por las pruebas de integración de Formularios.
- Seguridad: las pruebas reutilizan los permisos de `FORMULARIOS`, `RESPUESTAS` y el módulo contextual; la autorización de administración de destinos rechaza al usuario sin `FORMULARIOS:edit`. La regresión API conserva cobertura de autenticación, 401 y 403.
- Validación backend: 52/52 pruebas específicas de Formularios y 247/247 en la suite completa mediante `python -m unittest discover -s tests` dentro de Docker.
- Validación frontend: 52/52 específicas de Fase 5, 101/101 en la suite completa con un worker y build de producción aprobado.
- Regresión de navegación, Actividades, Ausentismos y Accidentes incluida en las suites completas. `git diff --check` aprobado.

### Cierre formal de Fase 5

**FASE 5 — REPOSITORIO CENTRAL Y ASIGNACIÓN DE FORMULARIOS COMPLETADA.**

- Bloque 1: auditoría y diseño técnico.
- Bloque 2: backend y migración 0019 de destinos jerárquicos.
- Bloque 3: Repositorio central y administración visual de destinos.
- Bloque 4: vistas contextuales sin duplicación ni herencia implícita.
- Bloque 5: respuestas con destino real contextualizado.
- Bloque 6: integración, regresión y cierre.

Pendientes reales de Fase 5: ninguno. No se inició Fase 6, Producción funcional completa ni Oficina funcional completa.

## Fase 6 — Riesgos de trabajo

### Bloque 1 — Auditoría y diseño técnico

**Estado: VALIDADO.**

- Se auditó la arquitectura existente de Casos, Persona, seguimientos, compromisos, documentos, auditoría, permisos, Formularios, Accidentes y Ausentismos.
- Decisión técnica: Riesgos de trabajo será una especialización explícita de `Caso` mediante `tipo_caso=RIESGOS_TRABAJO`, no una copia de Accidentes ni una nueva tabla de casos. No se reclasifican Casos históricos.
- El modelo base ya conserva Persona, responsable, estados, seguimiento, compromisos, cierre, versionado, historial, documentos y auditoría. El Bloque 2 deberá incorporar scope de Riesgos y autorización contextual sin contaminar el listado de Casos.
- El destino jerárquico de Formularios `RIESGOS_TRABAJO` ya existe; las respuestas futuras usarán el Caso como contexto real y el destino real de respuesta, sin repositorio paralelo.
- No se encontró relación real que justifique una FK hacia Accidentes o Ausentismos. Cualquier vínculo futuro será opcional, explícito y no inferirá históricos.
- Se verificó `0019_destinos_jerarquicos_formularios` como cabeza Alembic. No se requiere migración de tabla por el modelo elegido; un posible índice compuesto se evaluará con el query real del Bloque 2.
- Documento técnico: `docs/SITS_FASE6_RIESGOS_TRABAJO_DISENO.md`.

Fase 6 no está completada. El siguiente bloque autorizado será únicamente el Bloque 2 — backend/modelo operativo de Riesgos de trabajo.

## ROADMAP VIGENTE A PARTIR DE `5491b66`

Esta sección es la única fuente de verdad para el orden de trabajo futuro de SITS. El histórico anterior se conserva como evidencia de su ejecución; `docs/SITS_EXPANSION_SPEC.md` no se usa como roadmap vigente.

| Módulo | Estado | Commit de cierre | Siguiente acción |
|---|---|---|---|
| Navegación y estructura | COMPLETADA | `98e512d` | Ninguna; conservar y validar en regresiones. |
| Actividades | COMPLETADA | `98e512d` | Ninguna; conservar y validar en regresiones. |
| Ausentismos | COMPLETADA | `3a79689` | Ninguna; conservar y validar en regresiones. |
| Accidentes | COMPLETADA | `5491b66` | Ninguna; conservar y validar en regresiones. |
| Repositorio central y asignación de Formularios | SIGUIENTE | — | Definir y ejecutar el bloque transversal de Formularios. |
| Riesgos de trabajo | PENDIENTE | — | Iniciar después de Formularios. |
| Producción | PENDIENTE | — | Implementar Atenciones, Recorridos, Novedades de planta y Formularios. |
| Oficina | PENDIENTE | — | Implementar Beneficios, Atenciones, Préstamos, Seguro y Formularios. |
| Imágenes y adjuntos BLOB | PENDIENTE | — | Definir integración reutilizable para módulos que lo requieran. |
| Administración | PENDIENTE | — | Revisar Usuarios y Roles y permisos. |
| Dashboard | PENDIENTE | — | Definir indicadores soportados por datos implementados. |
| Integración final, regresión y cierre | PENDIENTE | — | Ejecutar al completar los módulos anteriores. |

Orden funcional de ejecución:

1. Navegación y estructura — COMPLETADA.
2. Actividades — COMPLETADA.
3. Ausentismos — COMPLETADA.
4. Accidentes — COMPLETADA.
5. Repositorio central y asignación de Formularios — SIGUIENTE.
6. Riesgos de trabajo.
7. Producción: Atenciones, Recorridos, Novedades de planta y Formularios.
8. Oficina: Beneficios, Atenciones, Préstamos, Seguro y Formularios.
9. Imágenes y adjuntos BLOB.
10. Administración: Usuarios; Roles y permisos.
11. Dashboard.
12. Integración final, regresión y cierre.
