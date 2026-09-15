# SITS — Fase 5: diseño de Formularios

**ESTADO FINAL: IMPLEMENTADO Y VALIDADO.** Fase 5 completada y validada. Este documento conserva el diseño y registra el cierre; no se reclasifican datos históricos.

## 1. Estado actual

SITS tiene formularios dinámicos. Un formulario puede estar en BORRADOR, PUBLICADO, INACTIVO o ARCHIVADO; contiene secciones, preguntas, opciones y reglas. El constructor visual permite editar, previsualizar, publicar, archivar y duplicar. La publicación y las respuestas conservan una versión con un snapshot JSON de la definición.

La captura dinámica está operativa: valida preguntas requeridas, reglas de visibilidad, opciones, tipos numéricos, correo, longitudes y búsquedas; guarda borradores o respuestas registradas. Cada respuesta definitiva recibe un código correlativo global con prefijo TTHH_RRLL_.

Está operativa la disponibilidad en CASOS, ATENCIONES, NOVEDADES, RECORRIDOS, PERSONAS y GENERAL, con paneles por contexto y registros por módulo. Es parcial frente al objetivo porque los destinos son módulos planos: no existe Macroproceso → Proceso → Subproceso. También coexisten pantallas de captura simple anteriores junto al flujo dinámico enrutable actualmente.

## 2. Arquitectura actual

### Frontend

frontend/src/app/App.tsx enruta /formularios al administrador, /formularios/:id al constructor y /formularios/:id/responder a la captura dinámica. El administrador también está accesible desde las rutas de formularios de los cuatro bloques de Trabajo Social. Las páginas de entidades integran selector, panel contextual y registros de formularios.

### Backend, API y servicios

El router backend/app/api/formularios.py, con prefijo /api/v1/formularios, expone CRUD, estado, definición, preguntas, opciones, reglas, respuestas, formularios disponibles por módulo, respuestas por módulo, formularios por contexto y opciones de búsqueda.

form_builder.py persiste la definición; dynamic_responses.py valida, guarda y consulta respuestas; form_integrations.py las muestra por módulo/persona; response_contexts.py valida o crea el contexto; response_codes.py asigna códigos; audit.py registra auditoría. Las operaciones usan autenticación, authorize() y control optimista por version en las operaciones que modifican registros.

### Relaciones relevantes

    Formulario 1--N FormularioDestino (modulo: texto)
    Formulario 1--N SeccionFormulario
    Formulario 1--N Pregunta 1--N OpcionPregunta
    Formulario 1--N ReglaFormulario
    Formulario 1--N FormularioVersion (snapshot JSON)
    Formulario 1--N EnvioFormulario 1--N RespuestaFormulario
    EnvioFormulario N--0..1 FormularioVersion
    EnvioFormulario -- contexto_tipo/contexto_id --> contexto polimórfico

El contexto no tiene FK de base de datos a Casos, Atenciones, Novedades, Recorridos o Personas: se valida en la capa de servicio.

## 3. Modelos/tablas existentes

| Área | Tabla/modelo | Datos y relaciones |
|---|---|---|
| Formularios | formularios / Formulario | ID, nombre, proceso textual, estado, responsable, respuestas múltiples y versión publicada. |
| Destinos | formulario_destinos / FormularioDestino | FK id_formulario y modulo textual; único por formulario-módulo. |
| Definición | secciones_formulario, preguntas, opciones_pregunta, reglas_formulario | FKs al formulario, pregunta o sección. |
| Versiones | versiones_formulario / FormularioVersion | Único por formulario/número; definicion_json, fecha y publicador. |
| Respuestas | envios_formulario / EnvioFormulario | Formulario, versión, usuario, estado, fecha, contexto, correlativo y código. |
| Detalle | respuestas_formulario / RespuestaFormulario | Una o varias filas por pregunta; valor texto/número/fecha/booleano/opción. |
| Códigos | secuencias_respuestas_formulario | Contador técnico global GLOBAL; código y número únicos en envíos. |
| Personas | personas / Persona | Contexto directo o persona derivada de un registro contextual. |
| Auditoría | auditoria / Auditoria | Append-only por tabla, registro, acción, usuario, fecha, valores, motivo y correlación. |

Los modelos de formularios/respuestas heredan metadatos de alta, actualización, eliminación lógica, versión y procedencia. Auditoría es append-only. No existe catálogo jerárquico de destinos ni FK de envío a Persona.

## 4. Componentes frontend existentes

- **Form Builder:** FormBuilderPage.tsx edita configuración, destinos, preguntas, vista previa y respuestas; publica, despublica o archiva.
- **Editor de preguntas:** QuestionEditor.tsx configura tipo, opciones, validación, búsqueda, sección y reglas.
- **Selector:** ModuleFormSelector.tsx lista formularios disponibles por módulo e inicia respuesta con contexto existente o nuevo.
- **Renderizador:** DynamicFormRenderer.tsx aplica visibilidad, obligatoriedad y secciones; reutiliza SearchAutocompleteField.tsx.
- **Respuestas/registros:** DynamicResponsePage.tsx, FormResponsesPanel.tsx, ModuleFormRecordsPanel.tsx y ContextFormsPanel.tsx.
- **Administración:** FormulariosAdminPage.tsx lista, filtra, crea, duplica, publica, archiva y elimina dentro de las reglas del backend.
- **Pantallas anteriores:** FormulariosListPage.tsx, FormularioDetailPage.tsx y ResponderFormularioPage.tsx continúan presentes.

## 5. Servicios backend existentes

| Servicio | Función |
|---|---|
| formularios.py | Alta, edición, estados y eliminación lógica. |
| form_builder.py | Definición completa, destinos, secciones, preguntas, opciones, reglas, duplicación y versiones. |
| respuestas_formulario.py | Fachada de guardado compatible. |
| dynamic_responses.py | Validación, borradores, persistencia, lectura, acciones y eliminación lógica. |
| form_integrations.py | Disponibilidad, respuestas por módulo y registros relacionados con Persona. |
| response_contexts.py | Contexto, Persona, creación/eliminación de contextos generados y autorización. |
| response_codes.py | Código definitivo correlativo. |
| audit.py | Trazabilidad de cambios. |
| form_search.py | Fuentes y opciones para preguntas BUSQUEDA. |

## 6. Sistema actual de destinos

Un destino es una fila de formulario_destinos con id_destino, id_formulario y modulo. sync_destinations() normaliza a mayúsculas, admite múltiples valores y, al retirarlos, conserva la fila con eliminación lógica. La unicidad es (id_formulario, modulo).

Los valores admitidos son GENERAL, CASOS, ATENCIONES, NOVEDADES, RECORRIDOS y PERSONAS. GENERAL no acepta contexto_id; los demás se validan contra CONTEXT_MODELS. Por tanto, una plantilla puede tener varios destinos, pero solo a nivel de módulo. No hay catálogo, jerarquía, código de proceso/subproceso, metadatos de destino ni FK que guarde el destino seleccionado en cada respuesta.

## 7. Contexto actual de respuestas

envios_formulario persiste id_respuesta, id_formulario, id_version_formulario, usuario_respuesta, estado, fecha, id_envio_cliente, id_registro_proceso, contexto_tipo, contexto_id, contexto_creado_dinamicamente, numero_secuencial, codigo_respuesta y metadatos/versionado. El detalle guarda pregunta y valor tipado.

La Persona no se persiste en el envío: resolve_person_id() la deriva. Para PERSONAS usa contexto_id; para los demás tipos obtiene id_persona del contexto. El módulo real es contexto_tipo, no una FK a la asignación de destino. La auditoría registra eventos de envío y puede ser sensible; el código se asigna solo al pasar a REGISTRADO.

## 8. Gaps frente al objetivo

El código conoce módulos planos. Formulario.proceso es texto y no controla disponibilidad, permisos ni contexto. No existe entidad Macroproceso/Proceso/Subproceso, relaciones por ID estable, filtro jerárquico, ni un destino real persistido para la respuesta. Tampoco hay manera de comprobar por FK que el destino elegido pertenezca a los destinos habilitados fuera de la validación textual vigente.

## 9. Modelo objetivo mínimo

Crear destinos_formulario: id_destino, codigo, nombre, nivel (MACROPROCESO, PROCESO, SUBPROCESO), padre_id_destino, orden y metadatos comunes. Una FK autorreferente expresa el árbol.

Evolucionar formulario_destinos para referenciar ese catálogo mediante id_destino_catalogo, manteniendo una asignación por plantilla/destino. Agregar envios_formulario.id_destino_respuesta, FK nullable a un subproceso. Destinos permitidos y destino real deben ser relaciones distintas.

La API deberá recibir/devolver IDs y códigos; el frontend deberá seleccionar en cascada. El mapeo entre módulos/rutas existentes y ramas de negocio requiere definición explícita: el código actual no lo contiene.

## 10. Destinos jerárquicos

La semilla objetivo mínima, sin clasificar históricos, es:

    TRABAJO_SOCIAL
    ├── ACTIVIDADES
    │   └── GENERAL
    ├── DEPARTAMENTO_MEDICO
    │   ├── RIESGOS_TRABAJO
    │   ├── AUSENTISMOS
    │   └── ACCIDENTES
    ├── PRODUCCION
    │   ├── ATENCIONES
    │   ├── RECORRIDOS
    │   └── NOVEDADES_PLANTA
    └── OFICINA
        ├── BENEFICIOS
        ├── ATENCIONES
        ├── PRESTAMOS
        └── SEGURO

La identidad persistente debe ser el ID de catálogo; los códigos requieren unicidad global o junto con el padre. No se debe usar solo la etiqueta, pues puede repetirse entre ramas. Formularios, Registrar actividad y Tabla de actividades no son subprocesos: son, respectivamente, una capacidad transversal y etiquetas de interfaz; no se incluyen en el catálogo de destino.

## 11. Múltiples destinos

La plantilla sigue siendo una sola fila en formularios. Cada destino permitido es una fila de asignación. No se duplican formulario, preguntas ni versiones. La publicación valida destinos activos y la respuesta valida que su subproceso real pertenezca a una asignación permitida, directa o por regla de rama definida.

## 12. Destino permitido vs. destino real

- **Permitido:** relación de la plantilla con los destinos donde puede usarse.
- **Real:** envios_formulario.id_destino_respuesta, único destino concreto elegido para el envío.

La distinción permite compartir plantilla, consultar histórico por subproceso y no inferir respuestas desde asignaciones modificadas posteriormente.

## 13. Compatibilidad histórica

No clasificar automáticamente formularios ni respuestas existentes. Se preservan IDs, preguntas, versiones, detalles, usuarios, códigos, correlativos, auditoría y contexto. proceso, formulario_destinos.modulo y contexto_tipo/contexto_id permanecen como datos compatibles. Para históricos, la nueva FK debe ser nula y mostrarse como sin clasificación jerárquica. No se modifican definicion_json ni las versiones existentes.

## 14. Permisos

Se reutiliza permisos por rol/módulo y las acciones create, read, edit, delete, sensitive, export. FORMULARIOS protege plantillas y RESPUESTAS la captura/consulta; las integraciones además exigen permisos del módulo contextual y, si corresponde, sensibilidad. El catálogo podría administrarse inicialmente con FORMULARIOS; el código no implementa aún un permiso jerárquico propio.

## 15. Migración implementada

La cabeza previa era 0018_accidentes. El Bloque 2 agregó 0019_destinos_jerarquicos_formularios, sin modificar 0015, 0016, 0017 ni 0018. La nueva cabeza es 0019_destinos_jerarquicos_formularios.

La migración creó destinos_formulario, con FK autorreferente, código único, nivel validado, índices por padre y vigencia/orden. Agregó id_destino_catalogo nullable a formulario_destinos e id_destino_respuesta nullable a envios_formulario, ambos con FK e índices; mantiene modulo y los valores textuales históricos sin backfill.

El downgrade retira primero los índices y columnas nuevas y luego el catálogo. El ciclo SQLite temporal 0018 → 0019 → 0018 → 0019 verificó estructura, FKs, índices, semilla y upgrade final. No se actualizan históricos por inferencia.

## 16. Bloque 2 implementado: backend y modelo de destinos de formularios

El bloque se limitó al backend/modelo, sin cambiar las pantallas frontend ni iniciar otro módulo funcional.

- **Modelos reutilizados:** Formulario, FormularioDestino, EnvioFormulario, MetadatosComunes, Auditoria y Permission.
- **Modelos modificados:** FormularioDestino enlaza opcionalmente al catálogo; EnvioFormulario persiste id_destino_respuesta nullable.
- **Estructura nueva:** DestinoFormulario / destinos_formulario es autorreferente, con código, nombre, nivel, padre, orden y metadatos comunes. No se crea una nueva plantilla por destino.
- **Servicios:** form_destinations.py crea la semilla idempotente, árbol, asignaciones, retiro lógico y validación; form_builder conserva separadas las asignaciones textuales; dynamic_responses valida y conserva el destino real; response_contexts permanece separado.
- **Endpoints y schemas:** GET /formularios/destinos, GET /formularios/destinos/activos, GET /formularios/destinos/{id_destino}/respuestas, GET y PUT /formularios/{id_formulario}/destinos; ResponderFormularioRequest acepta id_destino_respuesta y DestinosFormularioRequest prohíbe campos no declarados.
- **Permisos:** se reutilizaron FORMULARIOS para catálogo/asignaciones y RESPUESTAS más el módulo contextual para el envío; no se añadió permiso global.
- **Migración y semilla:** 0019_destinos_jerarquicos_formularios, posterior a 0018_accidentes, y 16 destinos iniciales idempotentes; sin reclasificación automática.
- **Pruebas ejecutadas:** catálogo, jerarquía, unicidad, idempotencia, múltiples asignaciones, retiro lógico, auditoría, destino permitido/no permitido/inexistente/inactivo, aislamiento por destino, históricos, permisos, schema y ciclo SQLite. La suite backend completa aprobó 247/247.

Los bloques posteriores al Bloque 2 cubrirán el frontend jerárquico, filtros/vistas por rama y regresión integral.

## 17. Bloque 3 implementado: Repositorio central y destinos jerárquicos

El frontend extiende el Repositorio único ya existente. `FormulariosAdminPage` conserva el listado de plantillas y `FormBuilderPage` conserva el constructor, editor, vista previa y respuestas. No hay pantallas de Formularios específicas para Actividades, Departamento Médico, Producción u Oficina en este bloque.

- **Cliente API:** `formBuilder.ts` usa el cliente HTTP existente para el árbol, asignaciones vigentes y sincronización (`GET /formularios/destinos`, `GET/PUT /formularios/{id_formulario}/destinos`). No se añadieron URLs absolutas ni endpoints nuevos.
- **Repositorio:** muestra estado, versión, fecha, acciones disponibles y rutas legibles de los destinos. Los filtros jerárquicos usan `id_destino_catalogo`; nombre y estado siguen siendo filtros locales compatibles con el listado actual.
- **Selector:** `HierarchicalDestinationPicker` obtiene el árbol del backend, permite marcar varios subprocesos, carga las asignaciones vigentes, evita doble envío y confirma éxito solo al completar el PUT. El retiro de una marca usa el retiro lógico del servicio backend.
- **Históricos y permisos:** los destinos textuales se muestran explícitamente como sin clasificación jerárquica. La interfaz impide administrar asignaciones sin `FORMULARIOS:edit`, pero 401/403 continúan siendo decisiones del backend.
- **Alcance excluido:** no se implementó selección de destino real al responder, filtrado de respuestas por destino ni vistas contextuales por proceso/subproceso.

## 18. Riesgos reales

- La equivalencia actual es textual (modulo, contexto_tipo); cambiarla sin transición puede romper disponibilidad y autorización.
- El contexto es polimórfico y validado en servicio; destino de negocio y registro contextual no deben confundirse.
- Las versiones son snapshots inmutables; reclasificarlas dañaría trazabilidad.
- Nombres de módulos como ATENCIONES ya existen y pueden colisionar semánticamente con etiquetas nuevas.
- Las asignaciones se eliminan lógicamente; los filtros deben diferenciar vigencia de historia.

## 19. Bloque 4: mapeo aprobado para vistas contextuales

Las rutas existentes de Formularios de Actividades, Departamento Médico, Producción y Oficina son vistas contextuales del Repositorio central; no son destinos, subprocesos ni repositorios nuevos. El árbol real del backend resuelve los IDs mediante códigos estables y las vistas solo incluyen asignaciones jerárquicas explícitas a subprocesos: `ACTIVIDADES/GENERAL`; `DEPARTAMENTO_MEDICO/{RIESGOS_TRABAJO,AUSENTISMOS,ACCIDENTES}`; `PRODUCCION/{ATENCIONES,RECORRIDOS,NOVEDADES_PLANTA}`; y `OFICINA/{BENEFICIOS,ATENCIONES,PRESTAMOS,SEGURO}`.

El filtro Todos es la unión sin duplicados por formulario de los subprocesos de la rama. No hay herencia desde los nodos de proceso, ni inferencia desde destinos textuales históricos, rutas antiguas, nombres o semántica. Los formularios sin asignación jerárquica permanecen exclusivamente en el Repositorio central. El destino real de la respuesta sigue fuera de este bloque y solo puede ser un subproceso válido.

## 20. Bloque 5 implementado: destino real y respuestas contextualizadas

`DynamicResponsePage` y el cliente existente envían `id_destino_respuesta` al contrato ya disponible de respuestas. Una plantilla con un único subproceso activo lo preselecciona y muestra la ruta legible completa. Una plantilla multidestino abierta desde una vista contextual recibe el ID real del subproceso; desde Todos requiere una selección explícita y ofrece solo destinos activos, asignados y compatibles con la rama contextual.

El destino real se conserva al editar una respuesta existente; no sustituye Persona, contexto, versión, códigos, correlativos ni auditoría. Los formularios históricos sin asignaciones jerárquicas siguen enviando `null`, sin inferencia. `ContextualFormsPage` consulta el endpoint existente de respuestas por destino solamente cuando se selecciona un subproceso, por lo que no incorpora respuestas históricas sin destino ni respuestas de otros subprocesos.

## 21. Estado final de implementación y validación

La Fase 5 quedó cerrada sin crear repositorios por Actividades, Departamento Médico, Producción u Oficina: sus rutas reutilizan el único Repositorio central y aplican asignaciones jerárquicas explícitas, sin herencia ni inferencia. La prueba integrada existente valida la plantilla multidestino Recorridos + Novedades de planta, el aislamiento de `id_destino_respuesta`, el retiro lógico y la preservación de la respuesta histórica.

La migración `0019_destinos_jerarquicos_formularios` se verificó desde `0018_accidentes` hasta `head` en SQLite temporal: catálogo de 16 destinos, FK autorreferente `padre_id_destino`, FKs de `formulario_destinos.id_destino_catalogo` y `envios_formulario.id_destino_respuesta`, índice de respuesta y siembra idempotente. Backend: 52/52 pruebas específicas de Formularios y 247/247 en la suite completa. Frontend: 52/52 específicas de Fase 5, 101/101 totales y build aprobado. Se preservan permisos, Persona, versiones, códigos, auditoría e históricos sin destino jerárquico.

Pendientes reales dentro de la Fase 5: ninguno. Las fases o módulos posteriores permanecen fuera de este alcance.

## Mapa de reutilización

| Funcionalidad actual | Archivo/modelo/servicio | Acción | Cambio necesario |
|---|---|---|---|
| Form Builder | FormBuilderPage.tsx, form_builder.py | MODIFICAR | Selector jerárquico e IDs de destinos permitidos. |
| preguntas | Pregunta, QuestionEditor.tsx | REUTILIZAR | Ninguno para la jerarquía. |
| versiones | FormularioVersion, create_version() | REUTILIZAR | Mantener snapshots sin reclasificación. |
| formularios | Formulario, formularios.py | REUTILIZAR | Asociar destinos sin duplicar plantilla. |
| respuestas | EnvioFormulario, dynamic_responses.py | MODIFICAR | Guardar y validar destino real nullable. |
| destinos | FormularioDestino, sync_destinations() | MODIFICAR | Referencia gradual a catálogo jerárquico. |
| catálogo jerárquico de destinos | DestinoFormulario / destinos_formulario | CREAR | Árbol de macroproceso, proceso y subproceso con IDs estables. |
| contexto | response_contexts.py, contexto_tipo/contexto_id | REUTILIZAR | Mantener separado del destino. |
| Personas | Persona, resolve_person_id() | REUTILIZAR | Preservar derivación actual. |
| auditoría | Auditoria, audit.py | REUTILIZAR | Auditar catálogo y asignaciones. |
| códigos | SecuenciaRespuestaFormulario, response_codes.py | REUTILIZAR | Sin cambio de correlativo/formato. |
| permisos | permissions.py, permisos | REUTILIZAR | Reutilizar permisos actuales. |
| vistas por módulo | ModuleFormSelector.tsx, ModuleFormRecordsPanel.tsx, form_integrations.py | MODIFICAR | Filtros y presentación por rama. |
