# SITS — Fase 7: diseño de Producción

**Estado.** Bloque 1 — auditoría técnica y diseño funcional. No crea migraciones, no modifica código funcional, no reclasifica históricos y no inicia el Bloque 2.

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

Riesgos reales: clasificar históricos por inferencia; usar un formulario como sustituto de registro; convertir área actual en contexto o historia; ocultar la separación Producción/Oficina detrás del mismo endpoint; y crear una infraestructura paralela de documentos o formularios. Ninguno se implementa en este bloque.
