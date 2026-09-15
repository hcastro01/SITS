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
