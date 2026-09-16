# SITS — Fase 6: diseño de Riesgos de trabajo

**Estado.** Bloque 1 — auditoría técnica y diseño. No crea migraciones, no modifica código funcional, no reclasifica históricos y no inicia los bloques de implementación.

## 1. Estado actual

La ruta canónica `/trabajo-social/departamento-medico/riesgos` existe, está protegida visualmente por el permiso `RIESGOS_TRABAJO` y hoy muestra una vista base, no un módulo operativo. El permiso y el destino jerárquico `TRABAJO_SOCIAL / DEPARTAMENTO_MEDICO / RIESGOS_TRABAJO` ya fueron sembrados; no existe modelo, router, servicio, contrato ni contexto dinámico específico de Riesgos.

Accidentes y Ausentismos son procesos distintos y ya implementados. No hay relación entre ellos y Riesgos de trabajo en el modelo actual.

## 2. Arquitectura encontrada

SITS usa FastAPI, SQLAlchemy y Alembic en backend; React/Vite/TypeScript en frontend. Las entidades operativas reutilizan `MetadatosComunes` (creación, actualización, versión y borrado lógico), servicios con allowlists, autorización por módulo, `expected_version` para edición y `Auditoria` transaccional. El frontend reutilizable ya incluye listado, detalle con pestañas, modal de edición, panel de documentos y panel de formularios contextuales.

## 3. Modelo actual de Casos

`Caso` (`backend/app/models/casos.py`) es el candidato base: tiene ID y `codigo_caso` único, fecha de apertura, FK opcional a Persona, colaborador, responsable, `tipo_caso`, subtipo, prioridad, sensibilidad, estado, área, turno, condición laboral, restricción, cierre, resultado y evidencias. `backend/app/services/casos.py` limita los campos admitidos, genera `CAS-<año>-...`, audita, versiona y aplica borrado lógico.

Los estados no están definidos en un catálogo cerrado por el servicio; el cierre operativo sí fija `estado_caso="CERRADO"` y rechaza doble cierre. Por compatibilidad, el estado mínimo propuesto para Riesgos es reutilizar `ABIERTO`, `EN_SEGUIMIENTO` y `CERRADO`, ya usados por Accidentes y por los flujos actuales, sin crear catálogo en este bloque.

**Decisión de diseño: A — especialización explícita de Caso.** Un Riesgo de trabajo será un Caso con `tipo_caso="RIESGOS_TRABAJO"`, creado exclusivamente por el futuro servicio de Riesgos y consultado solo por sus rutas. Es la opción de menor duplicación y conserva trazabilidad, Persona, seguimiento, compromiso, cierre, historial y documentos. No se deben inferir ni reclasificar Casos históricos: solo los nuevos creados explícitamente por el flujo de Riesgos pertenecerán a la especialización.

## 4. Persona

`Persona` (`backend/app/models/personas.py`) es el maestro único. Mantiene `id_persona`, nombre, cédula como texto indexado, código de empleado, cargo, área, departamento, centro, turno y estado laboral. `Caso.id_persona` ya es FK a Persona. Riesgos debe exigir una Persona activa y reutilizar la búsqueda existente por nombre/cédula; la cédula sigue siendo texto, sin conversión numérica ni copia de datos maestros. El área visible deberá ser la actual de Persona, distinguiéndola de los datos históricos del Caso cuando corresponda.

## 5. Seguimientos y compromisos

`Seguimiento`, `Compromiso` y `Cierre` ya dependen de `Caso` mediante FK. Los seguimientos guardan fecha, responsable, descripción, resultado, próxima acción, fecha de próxima acción y estado; al crearlos actualizan `Caso.ultimo_seguimiento` y auditan ambos cambios. Los compromisos pueden vincularse opcionalmente a un seguimiento y guardan responsable, vencimiento, cumplimiento y estado. La pantalla `CasoDetailProductionPage` ya ofrece pestañas de resumen, seguimientos, documentos, formularios e historial.

Riesgos debe reutilizar exactamente estas tablas y mecanismos, sin crear un sistema paralelo. El Bloque 2 deberá encapsular la autorización contextual para que solo los Casos `tipo_caso=RIESGOS_TRABAJO` se administren desde rutas de Riesgos.

## 6. Formularios

Fase 5 ya creó el destino activo `destino-riesgos-trabajo` con código `RIESGOS_TRABAJO`. Las plantillas asignadas a ese destino se reutilizan desde el Repositorio central; las respuestas mantienen `id_destino_respuesta`, Persona, versión, código y auditoría.

La integración propuesta para un riesgo basado en Caso es: `contexto_tipo="CASOS"`, `contexto_id=<id_caso del riesgo>` e `id_destino_respuesta="destino-riesgos-trabajo"`. Así no se inventa un contexto ni se duplica Persona. Actualmente `response_contexts.py` y `form_integrations.py` solo admiten `CASOS`, `ATENCIONES`, `NOVEDADES`, `RECORRIDOS` y `PERSONAS`; el Bloque 2/4 debe añadir la capa de autorización y filtrado por destino, no crear un repositorio de formularios paralelo ni forzar `contexto_tipo="RIESGOS_TRABAJO"` sin modelo real.

## 7. Documentos

Existe `Documento` con relación polimórfica validada por servicio, metadatos, hash, límites, firma MIME/extensión, autorización del módulo padre más `DOCUMENTOS`, descarga auditada y eliminación lógica. Para Casos, el tipo admitido es `CASOS`; por la decisión de reutilizar Caso, un Riesgo podrá usar posteriormente el mismo `DocumentosPanel` con ese tipo e ID del Caso.

El almacenamiento actual ya usa BLOB comprimido en SQLite. Fase 6 no debe cambiarlo, ampliarlo ni crear una infraestructura BLOB nueva; cualquier normalización general prevista para Fase 9 queda fuera de alcance y deberá decidirse sin romper documentos existentes.

## 8. Historial y auditoría

`Auditoria` es append-only, indexada por tabla/registro/fecha y se escribe en la misma transacción. `get_history` exige lectura del módulo y `AUDITORIA:read`. Para Riesgos se reutilizarán eventos `CREATE`, `UPDATE`, `DELETE` y los eventos existentes de seguimientos, compromisos, cierres y documentos; no se crea otra tabla de auditoría.

La implementación deberá auditar creación, edición, responsable, cambio de estado, seguimiento, compromiso y cierre/reapertura (si se autoriza reapertura). Las reglas de redacción de campos sensibles se mantienen.

## 9. Permisos

La matriz ya contiene `RIESGOS_TRABAJO`, además de `CASOS`, `SEGUIMIENTOS`, `COMPROMISOS`, `FORMULARIOS`, `RESPUESTAS`, `DOCUMENTOS` y `AUDITORIA`, con acciones create/read/edit/delete/sensitive/export. Sin embargo, `RIESGOS_TRABAJO` no forma parte de los conjuntos operativos/base que conceden permisos por defecto en `security_seed.py`; el menú puede existir sin que roles no administradores tengan operación efectiva.

Bloque 1 no modifica la matriz. El diseño para Bloque 2 debe definir permisos de Riesgos de forma aditiva y preservar el control de sensibilidad: para una especialización de Caso, la operación deberá exigir `RIESGOS_TRABAJO:<acción>` y las dependencias ya necesarias (`PERSONAS:read`, `SEGUIMIENTOS`, `COMPROMISOS`, `DOCUMENTOS`, `FORMULARIOS`/`RESPUESTAS`, `AUDITORIA`). Se debe decidir y probar explícitamente si `CASOS` seguirá siendo requisito adicional interno; nunca se debe permitir eludir sensibilidad mediante la ruta de Riesgos.

## 10. Relación con Accidentes

`Accidente` es una entidad independiente con FK obligatoria a Persona, fecha, clasificación, descripción, estado, importación XLSX, auditoría y permisos `ACCIDENTES`. No tiene FK ni asociación a Caso o Riesgo. Un Riesgo no es un Accidente y no se debe duplicar ningún registro.

No se propone `accidente_id` en esta fase. Si un caso de Riesgo requiere una referencia posterior, debe ser opcional, explícita, validada contra `accidentes.id_accidente` y no usada para crear registros ni inferir relación histórica. La necesidad funcional no está demostrada aún.

## 11. Relación con Ausentismos

`Ausentismo` es independiente, vinculado a Persona y a su lote opcional de importación, con fechas, tipo y motivo. No hay FK a Caso, Accidente ni Riesgo. No se requiere relación automática: coincidencia de Persona o fecha no es evidencia suficiente. Una integración futura solo podrá agregarse con un caso de uso explícito y una relación opcional auditable.

## 12. Gaps verificados

- Falta servicio/API/modelo de vista que delimite los Casos de Riesgos sin contaminar el listado genérico de Casos.
- Los servicios de Casos autorizan de forma fija `CASOS`; no conocen el permiso `RIESGOS_TRABAJO`.
- La matriz define el módulo Riesgos pero no le asigna permisos operativos por defecto a los roles no administradores.
- Los contextos dinámicos de Formularios no reconocen Riesgos como módulo; la integración debe mantener el contexto Caso y validar el destino real Riesgos.
- No hay contrato de tabla operativa, filtros ni detalle dedicado. Tampoco relación demostrada con Accidentes o Ausentismos.

## 13. Modelo objetivo mínimo

Un Riesgo de trabajo es un Caso explícitamente clasificado `RIESGOS_TRABAJO`, con `id_caso`/`codigo_caso`, Persona obligatoria, fecha de apertura, descripción operativa en los campos existentes, estado, responsable, autor y metadatos/versionado. Sus relaciones son los seguimientos, compromisos, cierre, formularios destinados a Riesgos, documentos de Caso e historial ya existentes.

No se agregan datos clínicos, legales ni médicos especializados sin una definición funcional posterior. Tampoco se agrega una tabla `riesgos_trabajo` ni una segunda tabla de casos mientras el modelo Caso satisfaga el flujo.

## 14. Tabla operativa futura

La futura consulta paginada de Riesgos deberá listar únicamente `Caso.tipo_caso="RIESGOS_TRABAJO"`, excluyendo eliminados y respetando sensibilidad. Contrato mínimo: código/ID, fecha de apertura, Persona, cédula textual, área actual de Persona, estado, responsable, registrado por, último seguimiento/actualización y acciones de ver/editar. Filtros: nombre, cédula, área, estado, responsable, fecha desde/hasta y posiblemente prioridad. Debe ordenar de forma estable por fecha de apertura e ID y no mostrar Accidentes, Ausentismos ni Casos históricos de otra clasificación.

## 15. Detalle futuro

Se reutilizará la composición de `CasoDetailProductionPage`, adaptada a una ruta de Riesgos y validada contra la clasificación: Resumen, Seguimientos, Formularios, Documentos e Historial. El resumen deberá mostrar Persona, responsable, estado, fecha y versión; no inventar información médica. Formularios se limitarán a plantillas asignadas a `RIESGOS_TRABAJO`; documentos e historial reutilizarán los servicios existentes.

## 16. Migración propuesta

La cabeza verificada es `0019_destinos_jerarquicos_formularios`. Con la decisión de especializar Caso, no es necesaria una migración de tabla para el Bloque 2: `casos.tipo_caso`, las FKs a Persona y las tablas hijas ya existen. La necesidad de un índice compuesto por `tipo_caso`, `estado_caso` y `fecha_apertura` debe comprobarse con el query final y volumen real; si se crea, será una migración posterior a 0019, aditiva y reversible mediante `drop_index`.

No habrá backfill: los Casos históricos permanecen tal cual. No se crearán FKs hacia Accidentes/Ausentismos sin requisito funcional. Si una futura necesidad demuestra atributos propios que no caben en Caso, se evaluará una extensión uno-a-uno con FK única a `casos.id_caso`, índices explícitos y downgrade que elimine solo esa extensión, nunca el Caso padre.

## 17. Bloques de implementación propuestos

1. **Bloque 1 — Auditoría y diseño:** completado en este documento.
2. **Bloque 2 — Backend Riesgos:** servicio y API de Caso especializado, filtros, autorización, Persona, auditoría y pruebas; decidir permisos aditivos y el índice solo si procede.
3. **Bloque 3 — Frontend operativo:** tabla, registro, edición y detalle reutilizando componentes existentes, con estados funcionales.
4. **Bloque 4 — Integraciones:** seguimientos, compromisos, formularios con destino real Riesgos, documentos e historial, sin sistema paralelo.
5. **Bloque 5 — Integración y cierre:** migraciones si existieran, seguridad 401/403, históricos, regresión y cierre.

## 18. Riesgos técnicos

- Clasificar por texto histórico, descripción o Persona causaría reclasificaciones incorrectas; queda prohibido.
- Reutilizar Caso sin un scope estricto mezclaría Riesgos en la consulta general y podría omitir el permiso específico.
- Dar solo `RIESGOS_TRABAJO` sin preservar sensibilidad de Caso puede abrir información sensible.
- Forzar un contexto de formulario inexistente rompería `response_contexts`; debe usarse el Caso real y el destino jerárquico real.
- Añadir relaciones con Accidentes/Ausentismos por coincidencia de Persona o fecha duplicaría significado y datos.
- Cambiar el almacenamiento documental durante esta fase ampliaría el alcance y pondría en riesgo adjuntos actuales.

## Mapa de reutilización

| Funcionalidad | Archivo/modelo/servicio actual | Acción | Cambio necesario |
|---|---|---|---|
| Caso | `models/casos.py`, `services/casos.py`, `api/casos.py` | MODIFICAR | Scope explícito `tipo_caso=RIESGOS_TRABAJO` y autorización contextual. |
| Persona | `models/personas.py`, servicios/búsquedas actuales | REUTILIZAR | Persona activa obligatoria; cédula textual y área actual. |
| Seguimientos | `Seguimiento`, `add_seguimiento`, `CasoDetailProductionPage` | REUTILIZAR | Limitar al Caso clasificado como Riesgo. |
| Compromisos | `Compromiso`, `add_compromiso` | REUTILIZAR | Limitar al Caso clasificado como Riesgo. |
| Formularios | `form_destinations.py`, `ContextualFormsPage` | MODIFICAR | Filtrar asignación por destino `RIESGOS_TRABAJO`. |
| Respuestas | `response_contexts.py`, `dynamic_responses.py` | MODIFICAR | Contexto Caso real más `id_destino_respuesta` Riesgos. |
| Documentos | `Documento`, `documentos.py`, `DocumentosPanel` | REUTILIZAR | Usar tipo `CASOS`; no cambiar BLOB. |
| Historial | `records.get_history`, `CasoDetailProductionPage` | REUTILIZAR | Consultar historia del Caso y sus eventos relacionados. |
| Auditoría | `Auditoria`, `audit.log_change` | REUTILIZAR | Eventos de Riesgo en tablas existentes, sin auditoría paralela. |
| Permisos | `permissions.py`, `security_seed.py` | MODIFICAR | Definir asignación aditiva de `RIESGOS_TRABAJO` y sensibilidad. |
| Accidentes | `Accidente`, `services/accidentes.py` | REUTILIZAR | Solo futura referencia opcional si surge requisito comprobado. |
| Ausentismos | `Ausentismo`, `services/ausentismos.py` | REUTILIZAR | Sin enlace automático; evaluar solo con requisito futuro. |

## 19. Bloque 2 implementado: backend operativo

La implementación reutiliza `Caso` de forma explícita: el servicio y router `riesgos-trabajo` fuerzan `tipo_caso="RIESGOS_TRABAJO"` al crear y verifican la misma clasificación antes de listar, consultar, editar, crear seguimientos, consultar compromisos, cerrar e inspeccionar historial. Un ID de Caso de otro tipo recibe 404 en las rutas de Riesgos y no puede ser reclasificado mediante el contrato de edición.

El listado consulta servidor y devuelve paginación real, Persona, cédula textual, área, estado, responsable, resumen disponible (`resultado`), autor y metadatos existentes. Los filtros combinables son nombre, cédula, área, estado, responsable y rango de fecha. El índice `ix_casos_tipo_estado_fecha_apertura` fue añadido por la migración `0020_indice_casos_riesgos`, porque toda consulta del módulo fija el tipo y filtra/ordena por estado y fecha; no agrega columnas ni datos.

La autorización reutiliza `RIESGOS_TRABAJO` como scope de las operaciones de Riesgos, sin conceder `CASOS` automáticamente. Los servicios compartidos de Casos aceptan ahora el módulo contextual para creación, edición, seguimiento, compromisos y cierre, conservando el comportamiento original para Casos. La semilla incorpora Riesgos al conjunto operativo sin ampliar permisos de otros módulos. Formularios conserva el destino jerárquico existente y Documentos continúa usando la relación `CASOS` del Caso especializado; no se construyó un motor paralelo ni se modificó BLOB.

La migración temporal validó `0019 → 0020`, downgrade a `0019` y upgrade final. Pruebas específicas de Riesgos: 4/4 aprobadas; cubren autenticación, autorización aislada sin `CASOS`, Persona, creación forzada, históricos, filtro/paginación, detalle, edición, cierre, seguimientos, Formularios/Documentos existentes e índice. Regresión focalizada Casos/Formularios: 23/23. Suite backend completa: 251/251. No se modificaron Accidentes ni Ausentismos ni se inició frontend.

## 20. Bloque 3 implementado: frontend operativo

La ruta canónica `Trabajo Social / Departamento Médico / Riesgos de trabajo` reutiliza el sidebar existente y consume solo el router contextual `/api/v1/riesgos-trabajo`. La tabla muestra datos disponibles del contrato real con paginación y filtros combinables aplicados por servidor; no reutiliza `GET /casos` ni representa Accidentes o Ausentismos.

El alta selecciona una Persona activa mediante el buscador del maestro y remite su `persona_id` real. El contrato de Riesgos guarda `responsable` como texto, por lo que la interfaz lo selecciona con la fuente reutilizable de responsables y guarda su etiqueta, sin inventar IDs ni campos. El formulario no presenta `tipo_caso`: el backend conserva la clasificación forzada. Edición usa `expected_version`; el cierre usa el endpoint y contrato existentes, sin reapertura.

El detalle de este bloque se limita a resumen y metadatos del Riesgo. Seguimientos, compromisos, Formularios, Documentos e Historial visual no se incorporaron y quedan para Bloque 4. La UI cubre carga, guardado, vacío, errores incluidos 401/403 y evita dobles envíos. La validación frontend fue 7/7 específica y 108/108 total, ejecutada por grupos seriales con un worker por el límite del entorno; el build aprobó.

## 21. Bloque 4 validado: integraciones contextuales

El detalle integrado usa rutas de Riesgos para Seguimientos, Compromisos e Historial y rechaza IDs de Casos de otro tipo. Para Formularios, el wrapper resuelve el destino activo por `DestinoFormulario.codigo == "RIESGOS_TRABAJO"`; no infiere textos ni usa una asignación `CASOS` como criterio. La lista une solo `FormularioDestino.id_destino_catalogo` del destino resuelto y las respuestas se consultan por Caso y por ese mismo `id_destino_respuesta`. El guardado reutiliza `dynamic_responses`, conserva contexto `CASOS`, versión, código y auditoría, pero fuerza el ID de destino resuelto y autoriza el Caso mediante `RIESGOS_TRABAJO`.

Para Documentos, los wrappers de Riesgos validan primero `Caso.tipo_caso == RIESGOS_TRABAJO` y luego delegan en `documentos.py` usando el módulo contextual. No se creó tabla, almacenamiento ni BLOB nuevos. Listado, carga, descarga y eliminación conservan los controles globales de documento y añaden el rechazo de Caso genérico. La prueba específica backend cubre destino Riesgos, exclusión de Formularios de Accidentes/Ausentismos, respuesta con destino real, Compromiso, Documentos e IDs genéricos rechazados.

La matriz frontend real quedó validada: Formularios cubre destino exclusivo Riesgos, exclusión Accidentes/Ausentismos/otras ramas, multidestino, respuesta contextual con `id_destino_respuesta` real, Persona/contexto, loading, vacío, error, 401/403 y doble envío; Documentos cubre metadata, permisos, loading, vacío, error y 401/403. El detalle integrado conserva sus seis secciones. Resultado: frontend específico 37/37, frontend completo serial 121/121 (18 archivos), build aprobado; backend Riesgos 5/5, regresión Formularios Fase 5 46/46 y suite completa 252/252.

La única incidencia de la validación fue ajena a Riesgos: `test_the_four_overdue_rules` tomaba `date.today()` del contenedor UTC, mientras `is_overdue` compara contra `America/Guayaquil`. Se reprodujo 3/3 tanto en el árbol actual como en `2252487`; la prueba se hizo determinista usando la misma zona horaria explícita de producción, sin cambiar la regla funcional. No se creó relación con Accidentes o Ausentismos ni se inició Bloque 5.
