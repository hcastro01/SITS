# SITS — Fase 7: diseño de Producción

**Estado.** Bloques 1 y 2 — diseño y backend contextual implementados. No reclasifica históricos ni inicia el Bloque 3.

## 1. Estado actual

Producción ya figura en el árbol `Trabajo Social / Producción` y cuenta con rutas para Atenciones, Recorridos, Novedades de planta y Formularios. La persistencia existente no es un placeholder: `Atencion`, `Recorrido` y `Novedad` son modelos distintos creados por la migración base de procesos. El problema que debe resolver la Fase 7 no es duplicar esas entidades, sino contextualizar sus operaciones y presentar sus contratos reales bajo Producción.

## 2. Atenciones actual

`Atencion` (`backend/app/models/procesos.py`) tiene ID, fecha/hora, `id_persona` opcional, colaborador, responsable, tipo, motivo, canal, gestión, resultado, flags de seguimiento/caso, observaciones, evidencias y estado. `backend/app/services/atenciones.py` aplica allowlist, permisos `ATENCIONES`, versión esperada, baja lógica y auditoría; `backend/app/api/atenciones.py` expone CRUD, historial y paginación por límite/offset, pero no filtros server-side ni total.

La UI reutiliza `EntityListPage`/`EntityDetailPage` con `atencionesConfig`; la ruta histórica `/atenciones` y la ruta de Producción muestran el mismo listado. Persona no es obligatoria hoy, el autor está en los metadatos comunes y responsable es texto, no FK. No existe clasificación Producción/Oficina.

## 3. Recorridos actual

`Recorrido` contiene ID, Persona opcional, fecha, horas, responsable, planta, área, turno, objetivo, observaciones, personas contactadas, novedades detectadas, acciones y evidencias. `backend/app/services/recorridos.py` declara la entidad en `EntityService`; el router genérico aporta CRUD, versión, baja/restauración, historial y paginación límite/offset. No hay campo de estado. `HallazgoRecorrido` es una entidad hija existente, con referencia opcional a Novedad y Caso; no debe sustituirse ni duplicarse.

La ruta `/trabajo-social/produccion/recorridos` es funcional, pero reutiliza la lista general `/recorridos` y su detalle retorna a la ruta histórica. Persona es opcional: un recorrido general no debe forzar Persona ficticia.

## 4. Novedades actual

`Novedad` contiene ID, Persona opcional, fecha/hora, responsable, fuente, tipo/subtipo, área, turno, lugar, descripción, impacto, prioridad, acción inmediata, flags de generación de Atención/Caso, estado y evidencias. `backend/app/services/novedades.py` usa `EntityService`; `/api/v1/novedades` es CRUD genérico con historial y paginación límite/offset. La pantalla de Producción se etiqueta “Novedades de planta”, pero consume la entidad histórica `Novedad`, igual que `/novedades`.

La etiqueta de planta debe mantenerse como presentación de Producción: no renombrar tabla, IDs ni registros históricos. Persona sigue opcional; área y lugar son datos propios del registro, no una prueba del proceso.

## 5. Arquitectura común y reutilización

Atenciones conserva servicio explícito porque antecede a la fábrica; Recorridos y Novedades usan `EntityService`. Los tres comparten metadatos comunes, versión optimista, baja lógica, restauración, `records`, `audit.log_change`, `get_history`, documento polimórfico y respuesta dinámica contextual. No conviene una mega-tabla: las columnas y relaciones de los procesos ya son distintas.

| Funcionalidad | Archivo/modelo/servicio | Acción | Cambio necesario |
|---|---|---|---|
| Atenciones | `Atencion`, `atenciones.py`, `/api/v1/atenciones` | MODIFICAR | Contexto explícito y consulta contextual de Producción; conservar API transversal compatible. |
| Recorridos | `Recorrido`, `recorridos.py`, `EntityService` | REUTILIZAR | Adaptar presentación/rutas y filtros solo si el contrato de Producción los exige. |
| Novedades de planta | `Novedad`, `novedades.py`, `EntityService` | REUTILIZAR | Presentar como planta bajo Producción, sin renombrar histórico. |
| Persona | `Persona`, FK `id_persona` | REUTILIZAR | Selección del maestro solo donde aplique; mostrar área actual como tal. |
| Formularios | `DestinoFormulario`, `form_destinations.py` | REUTILIZAR | Usar destinos de Producción ya sembrados. |
| Respuestas | `response_contexts.py`, `form_integrations.py` | MODIFICAR | Resolver destino real de Producción sin confundir respuesta y registro. |
| Documentos | `Documento`, `documentos.py` | REUTILIZAR | Tipos `ATENCIONES`, `RECORRIDOS`, `NOVEDADES`; sin ampliar BLOB. |
| Auditoría | `Auditoria`, `audit.py`, `records.py` | REUTILIZAR | Registrar contexto y cambios mediante el historial existente. |
| Permisos | `security_seed.py`, `permissions.py` | MODIFICAR | Diseñar scope de Producción mínimo, sin ampliar matriz ahora. |
| Rutas/componentes | `App.tsx`, `EntityListPage`, `EntityDetailPage` | MODIFICAR | Hacer que las rutas de Producción no sean solo alias de los listados transversales. |

## 6. Persona, trazabilidad y área

Atención admite Persona y normalmente la necesita para una operación individual, pero el modelo actual permite `null`; el Bloque 2 debe confirmar la regla de negocio antes de volverla obligatoria. Recorrido y Novedad permiten Persona opcional y deben conservar esa posibilidad. En todos los casos el autor verificable es `creado_por`; responsable es un campo de negocio independiente y no sustituye al autor ni a Persona.

La cédula, nombre y área provienen del maestro Persona cuando exista relación. El área disponible es actual; nunca debe inferir Producción/Oficina ni presentarse como área histórica sin evidencia.

## 7. Gap Producción/Oficina en Atenciones

No hay hoy `modulo`, `contexto`, `proceso`, `origen` ni `destino` en `atenciones`. `/trabajo-social/produccion/atenciones` y la futura Oficina comparten `ATENCIONES`, `/api/v1/atenciones`, permisos y datos. Por tanto, la clasificación futura debe ser un discriminador explícito, por ejemplo `contexto_operativo` nullable con valores cerrados `PRODUCCION` y `OFICINA` (o catálogo equivalente), validado por el servicio y recibido solo por rutas contextuales. No se debe deducir de área, texto libre, nombre de usuario o Persona.

Los registros históricos sin discriminador quedan `null`, visibles por la ruta transversal vigente y excluidos de listados contextuales salvo decisión posterior explícita. Este es el único cambio de datos necesario identificado para separar Atenciones sin duplicarlas.

## 8. Formularios, respuestas y documentos

El catálogo ya tiene `destino-produccion-atenciones` (`PRODUCCION_ATENCIONES`), `destino-recorridos` (`RECORRIDOS`) y `destino-novedades-planta` (`NOVEDADES_PLANTA`), además de destinos distintos para Oficina. Formularios se asignan en el Repositorio central; no se creará otro motor. Las respuestas preservan `contexto_tipo` (`ATENCIONES`, `RECORRIDOS` o `NOVEDADES`), `contexto_id`, Persona derivable y `id_destino_respuesta`.

Una respuesta no equivale automáticamente a un registro. `response_contexts.create_dynamic_context` puede crear un contexto solo por una integración explícita, y los listados generales excluyen esos contextos dinámicos. El Bloque 4 deberá forzar y validar el destino contextual apropiado; no usar el código genérico de módulo como si distinguiera Oficina/Producción para Atenciones.

`documentos.py` ya admite los tres tipos y exige permiso del módulo padre más `DOCUMENTOS`; existe carga, metadata, descarga, baja lógica y auditoría. El almacenamiento actual es BLOB comprimido SQLite y queda sin cambios.

## 9. Auditoría y permisos

Creación, edición, eliminación y restauración se auditan con `log_change`; el historial exige permiso del módulo y `AUDITORIA:read`. La versión esperada evita conflictos de actualización. Los permisos actuales son `ATENCIONES`, `RECORRIDOS`, `NOVEDADES`, `PERSONAS`, `FORMULARIOS`, `RESPUESTAS`, `DOCUMENTOS` y `AUDITORIA`; no existe scope específico `PRODUCCION`.

El cambio mínimo a evaluar en Bloque 2 es un scope `PRODUCCION` para las rutas contextuales, junto con las dependencias existentes, sin conceder automáticamente acceso transversal ni cambiar derechos globales. Alternativamente, si el contrato aprobado mantiene los módulos existentes, el router contextual debe exigir sus permisos de proceso y limitar por contexto. La decisión requiere pruebas 401/403 y no se aplica en este bloque.

## 10. Modelos, tablas y detalle futuros

La tabla futura de Atenciones de Producción debe mostrar ID, fecha, Persona, cédula textual, área actual, motivo/descripción disponible, registrado por, responsable, estado y acciones. Recorridos: ID, fecha, descripción/objetivo, responsable/autor, estado solo si se incorpora con requisito real y acciones. Novedades: ID, fecha, Persona opcional, área/lugar disponibles, descripción, registrado por, estado y acciones.

Se recomienda mantener `EntityDetailPage` como base y sustituirlo por detalle contextual solo si las integraciones de Bloque 4 requieren tabs explícitas para Formularios, Documentos e Historial. No se justifica una página nueva en Bloque 2. Atenciones requerirá filtros/paginación con total para el contrato objetivo; Recorridos y Novedades deben diseñarlos contra campos existentes, no contra GPS ni tipos de incidente inventados.

## 11. Migración propuesta y compatibilidad

La cabeza actual es `0020_indice_casos_riesgos`. No se crea migración en Bloque 1. La única migración potencial identificada es posterior a 0020 y aditiva para `atenciones.contexto_operativo` nullable, con check o catálogo de valores, índice compuesto conforme al patrón real de listado, downgrade que retire únicamente el índice/columna nueva y sin backfill. Antes de implementarla se debe validar en SQLite temporal upgrade, downgrade, upgrade final y `alembic check`.

No se reclasifican Atenciones, Recorridos ni Novedades históricos. Las rutas históricas y sus APIs se conservan hasta que un contrato explícito defina su transición.

## 12. Bloques siguientes y riesgos

1. **Bloque 2 — Backend operativo:** decidir y aplicar el discriminador mínimo de Atenciones, rutas contextuales, filtros/paginación y permisos; validar migración si procede.
2. **Bloque 3 — Frontend operativo:** tablas y detalles contextuales de Producción sobre contratos reales, sin romper rutas históricas.
3. **Bloque 4 — Integración:** Persona, Formularios con destino real, respuestas, documentos, historial y trazabilidad.
4. **Bloque 5 — Cierre:** seguridad, regresión, migraciones e integración punta a punta.

Riesgos reales: clasificar históricos por inferencia; usar un formulario como sustituto de registro; convertir área actual en contexto o historia; ocultar la separación Producción/Oficina detrás del mismo endpoint; y crear una infraestructura paralela de documentos o formularios.

## 13. Bloque 2 implementado: backend contextual

Se añadió `PRODUCCION` como scope aditivo y los wrappers `/api/v1/produccion/atenciones`, `/recorridos` y `/novedades`. El usuario que tiene solo `PRODUCCION` puede operar las rutas contextuales, pero no recibe automáticamente el permiso de las rutas transversales `ATENCIONES`, `RECORRIDOS` o `NOVEDADES`. Todos los wrappers delegan en los modelos, versionado, baja lógica y auditoría existentes.

La migración `0021_contexto_operativo_atenciones` es posterior a `0020`. Agrega `atenciones.contexto_operativo` nullable, restringido a `PRODUCCION` u `OFICINA`, más el índice `ix_atenciones_contexto_fecha`; no modifica filas existentes ni hace backfill. El wrapper de creación elimina cualquier contexto del request y fuerza `PRODUCCION`; edición no puede cambiarlo. El listado, detalle, edición, historial y baja contextual rechazan con 404 las Atenciones históricas `NULL` y las de `OFICINA`.

Recorridos y Novedades se confirmaron conceptualmente exclusivos de Producción en la arquitectura vigente. Sus wrappers contextuales reutilizan `EntityService`, no añaden columnas ni modelos y conservan Persona opcional. Novedades de planta sigue siendo la presentación de `Novedad`; no existe una entidad paralela. Los filtros se ejecutan server-side con paginación `items`, `total`, `limite`, `offset`, sobre fecha, Persona/nombre, cédula, área actual, responsable y estado cuando ese campo existe.

No se modificaron Formularios, respuestas ni BLOB. Documentos e historial conservan la infraestructura existente; el siguiente Bloque 3 solo podrá consumir estos contratos backend desde una interfaz contextual. La validación focalizada cubre autenticación, scope aislado, contexto forzado, NULL/OFICINA excluidos, filtro, paginación, Persona textual, edición inmutable, Recorridos/Novedades, auditoría y ciclo de migración. Resultado: Producción 3/3, regresión focalizada 36/36 y backend completo 255/255, sin fallos ni errores; `alembic check` aprobado tras `0020 → 0021 → 0020 → 0021` en SQLite temporal.

## 14. Bloque 3 implementado: frontend contextual

Las rutas de Producción ya no son alias de los listados transversales: Atenciones, Recorridos y Novedades de planta usan clientes separados bajo `/api/v1/produccion/*`, sus detalles vuelven a la ruta contextual y las rutas históricas conservan sus clientes y URLs anteriores. Los clientes contextuales consumen la página real `{items,total,limite,offset}` y los filtros server-side de nombre, cédula, responsable, estado cuando existe y fechas.

Atenciones de Producción solo presenta lo que el wrapper entrega; por ello las Atenciones `NULL` u `OFICINA` no aparecen ni pueden abrirse desde esa vista. El formulario no muestra ni envía `contexto_operativo`; el wrapper de backend lo fija a `PRODUCCION`. Persona es opcional y se reutiliza la búsqueda existente cuando se asocia una Persona. Las tablas muestran Persona, cédula, área actual, responsable y autor/registrado por como campos distintos, sin sustituir el autor histórico.

Recorridos y Novedades reutilizan el mismo componente contextual, con creación, detalle, edición, filtros y paginación. Novedad conserva su entidad y se etiqueta como “Novedades de planta”. Formularios permanece en su ruta contextual ya existente y no se alteraron respuestas, Documentos, BLOB ni la integración profunda del Bloque 4. Los estados de carga, vacío y errores API (incluidos 401/403) se distinguen antes de mostrar el vacío.

La validación visual manual final fue confirmada en el entorno local `http://127.0.0.1:8081`, en viewports `1440x900`, `768x1024` y `390x844`. Las cuatro rutas contextuales de Producción —Atenciones, Recorridos, Novedades de planta y Formularios—, junto con sidebar, navegación, filtros, tablas, paginación y modales, se observaron correctas y sin solapamientos, controles fuera de pantalla ni errores visuales bloqueantes. **BLOQUE 3 FASE 7 VALIDADO — FRONTEND DE PRODUCCIÓN LISTO.**

## 15. Bloque 4 — Integraciones de Producción

Las integraciones contextuales se realizan exclusivamente desde los registros de Producción. Los wrappers de Atenciones, Recorridos y Novedades consultan el catálogo por código y resuelven el ID real de `PRODUCCION_ATENCIONES`, `RECORRIDOS` o `NOVEDADES_PLANTA`; solamente incluyen formularios publicados asignados al subproceso exacto. Una plantilla multidestino continúa siendo una sola plantilla y cada respuesta conserva el ID del destino desde el que se respondió.

El guardado se hace por la ruta contextual de Producción: ignora contexto, Persona y destino enviados por el cliente y fija el registro real, `contexto_tipo` y `id_destino_respuesta`. Por ello una respuesta no crea Atención, Recorrido ni Novedad. La respuesta conserva formulario, versión publicada, usuario, código, correlativo y auditoría del motor existente. Persona sigue siendo opcional y, cuando pertenece al registro, permanece separada de responsable, autor y respondedor.

Atenciones de Producción sigue excluyendo registros `NULL` y `OFICINA`; no hay inferencia, backfill ni reclasificación. Historial reutiliza la ruta contextual existente y exige `PRODUCCION` junto con `AUDITORIA`. Formularios exige además `FORMULARIOS`; el guardado exige `RESPUESTAS`, sin que `PRODUCCION` conceda acceso transversal por sí solo.

Documentos reutiliza la infraestructura existente sin ampliar BLOB ni crear tablas: sus wrappers de Producción validan primero el registro contextual y luego delegan con módulo padre `PRODUCCION` y permiso `DOCUMENTOS`. En Atenciones rechazan `NULL`, `OFICINA` e inexistentes; en Recorridos y Novedades validan existencia antes de acceder a un documento asociado. Un ID de documento de otro registro también se rechaza. Las rutas documentales transversales permanecen intactas.

Validación del Bloque 4: frontend focalizado 35/35, suite frontend 124/124 en 19 archivos con `--maxWorkers=1`, backend focalizado Producción 7/7 y suite backend completa 259/259. El build frontend y `git diff --check` aprobaron. **BLOQUE 4 FASE 7 VALIDADO — INTEGRACIONES DE PRODUCCIÓN LISTAS.**

El siguiente bloque es exclusivamente Bloque 5 — Integración, regresión y cierre de Producción.
