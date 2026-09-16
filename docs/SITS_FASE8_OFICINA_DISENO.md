# SITS — Fase 8: diseño de Oficina

**Estado.** Bloque 1 — auditoría y diseño técnico. No implementa entidades, migraciones, endpoints ni pantallas operativas.

## 1. Estado actual

La navegación ya contiene `Trabajo Social / Oficina` con Beneficios, Atenciones, Préstamos, Seguro y Formularios. Beneficios, Atenciones de Oficina, Préstamos y Seguro son `StructureBasePage`: rutas existentes pero *placeholders*. Formularios es funcional y reutiliza el repositorio central. No existe router `/api/v1/oficina`.

El inventario de modelos, routers, servicios, migraciones, clientes y componentes no contiene modelos operativos `Beneficio`, `Prestamo` ni `Seguro`, ni equivalentes de ayudas, anticipos, afiliaciones o pólizas. Sus únicas presencias reales son los permisos, los nodos de navegación y los destinos del catálogo. Por tanto, no hay datos ni reglas de negocio que permitan inventar tipo de beneficio, monto, interés, cuotas, coberturas, afiliaciones o reglas de aseguradora.

## 2. Beneficios

No existe modelo, schema, servicio, API, cliente ni pantalla operativa reutilizable. Persona, autor, responsable, estado, fechas, filtros, paginación, Documentos e historial no están definidos para Beneficios por código actual.

El modelo mínimo futuro requiere una decisión funcional explícita antes del Bloque 2. Sólo son justificables como forma de la infraestructura común: identificador, `id_persona` si la solicitud confirma que aplica, fecha, descripción si se define, responsable si se define, estado si se define y metadatos/auditoría. No se proponen tipos ni reglas adicionales.

## 3. Atenciones de Oficina

Se reutiliza exclusivamente `Atencion`, `app/services/atenciones.py`, metadatos comunes, auditoría, baja lógica y la migración `0021_contexto_operativo_atenciones`. El discriminador ya es nullable y sólo admite `PRODUCCION` u `OFICINA`; una ruta contextual futura debe descartar el valor enviado por cliente y crear con `contexto_operativo="OFICINA"`.

Persona ya es opcional (`id_persona` nullable); responsable es texto de negocio; `creado_por` identifica el autor. Los filtros y la paginación contextual de Producción pueden reutilizarse tal cual, cambiando sólo módulo, etiqueta, prefijo y contexto. La entidad, los campos de Atención y las rutas transversales se conservan. No habrá segunda tabla, segundo discriminador, backfill ni inferencia por área, Persona, descripción, usuario, centro, ubicación o texto.

## 4. Préstamos

No existe modelo, schema, servicio, router, API, cliente, tabla ni Documento asociado para Préstamos. Tampoco hay monto, responsable, fechas, estado, autorización ni trazabilidad específicos. Tasa, cuotas, amortización, descuentos, cobros, límites y aprobaciones contables quedan **NO DEFINIDOS**.

Si se autoriza una entidad futura, su mínimo debe acordarse desde necesidades reales; reutilizaría sólo `EntityService`, `records`, `audit`, Persona opcional únicamente si se define, el patrón de Documentos y permisos. No se diseña una regla financiera.

## 5. Seguro

No existe modelo, schema, servicio, router, API, cliente, tabla ni Documento asociado para Seguro, seguro médico, afiliaciones, dependientes, pólizas o gestiones equivalentes. Cobertura, copagos, deducibles, carencias, exclusiones, elegibilidad, aseguradora y facturación quedan **NO DEFINIDOS**.

El alcance futuro debe decidir si se registra una solicitud, gestión, afiliación o novedad; no se construirá un motor de pólizas, siniestros ni facturación. Sólo después podrá decidirse una entidad mínima con infraestructura común.

## 6. Persona y trazabilidad

`Persona` es el maestro reutilizable; conserva nombre, cédula textual, área actual, cargo y estado laboral. Para Beneficios, Préstamos y Seguro no puede declararse obligatoria ni opcional porque no existen modelos. Para Atenciones es opcional por modelo real.

Persona relacionada, responsable, autor (`creado_por`) y usuario que responde un formulario son conceptos independientes. Los metadatos comunes y `EnvioFormulario.usuario_respuesta` ya permiten no sustituirlos entre sí.

## 7. Formularios y respuestas

El catálogo real contiene `OFICINA` y los destinos hoja `BENEFICIOS`, `OFICINA_ATENCIONES`, `PRESTAMOS` y `SEGURO`; `ContextualFormsPage.office` consume la misma rama y el repositorio central. No se crearán destinos ni motor duplicados.

Las respuestas guardan destino real y siguen siendo distintas de registros operativos. El motor genérico conserva una integración dinámica explícita para tipos existentes, incluida `ATENCIONES`; por ello los wrappers futuros de Oficina deben seguir el patrón contextual de Producción: fijar registro, contexto y destino, eliminar del payload `crear_contexto`, `id_persona` y destino manipulables, y no crear Beneficio, Atención, Préstamo o Seguro automáticamente.

## 8. Documentos, historial y auditoría

`Documento` es polimórfico, BLOB comprimido y validado mediante `TIPO_REGISTRO_MODELOS`; hoy admite Atenciones, Personas, Casos, Novedades, Recorridos, Hallazgos, Seguimientos, Derivaciones, Compromisos, Cierres y respuestas, pero no Beneficios, Préstamos ni Seguro. No se modifica BLOB ni almacenamiento.

Atenciones de Oficina puede reutilizar un wrapper contextual análogo a Producción: validar primero `contexto_operativo="OFICINA"`, después exigir `OFICINA` y `DOCUMENTOS`, y delegar con tipo `ATENCIONES`. Para nuevas entidades, su tipo documental sólo se agregará si la entidad real se autoriza. `records.get_history` exige módulo contextual y `AUDITORIA:read`; `audit.log_change` ya registra CREATE, UPDATE, DELETE y RESTORE. No habrá historial paralelo.

## 9. Permisos y scope

La matriz ya declara `BENEFICIOS`, `PRESTAMOS` y `SEGUROS`, pero no `OFICINA`. Sus derechos iniciales son falsos para roles no administradores porque no pertenecen a `OPERATIONAL` ni `BASE_READ`. Los nodos de menú existentes usan esos permisos y `ATENCIONES` para la ruta de Oficina.

El cambio mínimo propuesto para Bloque 2 es añadir `OFICINA` como scope aditivo, sin concederlo automáticamente ni elevar permisos existentes, y exigirlo junto con permisos específicos: `FORMULARIOS`, `RESPUESTAS`, `DOCUMENTOS` y `AUDITORIA` según acción. Un usuario con `OFICINA` no obtendrá `PRODUCCION`, `ATENCIONES` transversales, ni acceso a Atenciones `PRODUCCION` o históricas `NULL`.

## 10. Mapa de reutilización

| Funcionalidad | Archivo/modelo/servicio/componente | Acción | Cambio necesario |
|---|---|---|---|
| Beneficios | No existe | CREAR | Sólo tras definir negocio mínimo y entidad real. |
| Atenciones | `Atencion`, `atenciones.py`, `produccion.py`, `EntityConfig.ts` | MODIFICAR | Wrapper OFICINA, cliente/config/rutas contextuales, mismo contexto explícito. |
| Préstamos | No existe | CREAR | Entidad mínima pendiente de definición; sin reglas financieras. |
| Seguro | No existe | CREAR | Entidad mínima pendiente de definir alcance; sin motor de pólizas. |
| Persona | `Persona`, selector existente | REUTILIZAR | Aplicar sólo cuando el modelo futuro lo justifique. |
| Formularios | `form_destinations.py`, `ContextualFormsPage` | REUTILIZAR | Usar destinos Office existentes. |
| Respuestas | `dynamic_responses.py`, patrón `produccion.py` | MODIFICAR | Wrapper contextual que fuerce registro/destino y bloquee creación implícita. |
| Documentos | `documentos.py`, `DocumentosPanel` | MODIFICAR | Wrapper de Atenciones Oficina; tipos nuevos sólo con entidad aprobada. |
| Auditoría | `audit.py`, `records.py` | REUTILIZAR | Usar eventos y `get_history` existentes. |
| Permisos | `security_seed.py` | MODIFICAR | Scope `OFICINA` mínimo, sin ampliar derechos. |
| Rutas | `App.tsx`, `Layout.tsx` | MODIFICAR | Sustituir placeholders sólo al implementar Bloques posteriores. |
| Frontend común | `EntityListPage`, `EntityDetailPage`, `EntityFormModal`, `entities.ts` | REUTILIZAR | Configuraciones y cliente contextual de Atención; evaluar nuevas entidades. |

## 11. Modelos, tablas y compatibilidad

La tabla futura de Atenciones Oficina usa los campos reales: ID, fecha, Persona/cédula/área actual, motivo, responsable, registrado por, estado y acciones. Beneficios, Préstamos y Seguro no tienen campos reales todavía: sus tablas futuras no se pueden concretar más allá de los metadatos comunes, Persona/responsable/estado/fecha sólo si el modelo aprobado los requiere.

Históricos de Atención permanecen `NULL`, siguen accesibles sólo por el contrato transversal preservado y nunca se reclasifican. Producción continúa filtrando exclusivamente `PRODUCCION`; Oficina deberá filtrar exclusivamente `OFICINA`.

## 12. Migración propuesta

La cabeza real de Alembic es `0021_contexto_operativo_atenciones`. Atenciones Oficina no requiere migración: su columna, restricción e índice ya existen.

Beneficios, Préstamos y Seguro requerirían migraciones aditivas únicamente después de que se definan sus entidades reales. Cada una deberá declarar sus columnas confirmadas, FKs sólo cuando estén justificadas, índices derivados del listado real, históricos intactos y downgrade limitado a lo creado. En este bloque no se crea ninguna.

## 13. Bloques de implementación y riesgos

1. **Bloque 1 — Auditoría y diseño técnico:** completado por este documento.
2. **Bloque 2 — Backend contextual de Oficina:** scope OFICINA y Atenciones; decidir y crear únicamente entidades aprobadas para Beneficios, Préstamos/Seguro si ya existe definición funcional suficiente.
3. **Bloque 3 — Frontend contextual de Oficina:** reutilizar configuraciones/componentes y sustituir placeholders correspondientes.
4. **Bloque 4 — Integración:** Formularios, Documentos, trazabilidad e historial sobre registros reales.
5. **Bloque 5 — Cierre:** regresión, migraciones y documentación.

Riesgos reales: clasificar históricos por inferencia; reutilizar `ATENCIONES` transversal sin scope; convertir respuestas en registros; inventar beneficios, préstamos o pólizas; conceder `OFICINA` automáticamente; y crear BLOB, historial, formularios o páginas paralelas.

## 14. Bloque 2A — Atenciones Oficina + scope OFICINA

**IMPLEMENTADO Y VALIDADO.** `/api/v1/oficina/atenciones` reutiliza `Atencion`, fuerza `contexto_operativo="OFICINA"` en backend, filtra exclusivamente ese valor y rechaza con 404 los registros `PRODUCCION` y los históricos `NULL`. El scope aditivo `OFICINA` no concede `PRODUCCION` ni el acceso transversal `ATENCIONES`; se conserva autor desde la sesión, responsable como campo existente, filtros server-side, paginación `items`/`total`/`limite`/`offset`, auditoría e historial existentes.

No se creó migración: `alembic heads` continúa en `0021_contexto_operativo_atenciones` y `alembic check` no detectó operaciones pendientes. Las pruebas focalizadas de Oficina y Producción aprobaron 9/9; la suite backend por `python -m unittest discover -s tests` aprobó 261/261. No se modificaron Formularios, respuestas, Documentos ni BLOB.

## 15. Bloque 2B — Beneficios, Préstamos y Seguro

**IMPLEMENTADO Y VALIDADO.** El backend crea las tres entidades persistentes y separadas: `Beneficio`, `Prestamo` y `Seguro`, bajo las rutas contextuales `/api/v1/oficina/beneficios`, `/prestamos` y `/seguro`. Todas reutilizan `EntityService`, metadatos comunes, versión optimista, baja lógica y `Auditoria`; no se creó una mega-tabla ni historial paralelo.

- Beneficios admite únicamente `TIA` y `FARMACIA`, con gestiones `ACTIVACION`, `BLOQUEO` y `ANULACION`.
- Préstamos admite únicamente `PRESTAMO` y `ANTICIPO`; no contiene monto, interés, cuotas, plazo, saldo, amortización ni lógica financiera.
- Seguro admite únicamente `AFILIACION`, `ENROLAMIENTO`, `COBERTURA`, `REEMBOLSO`, `PRIMA` y `DEPENDIENTE`. `DEPENDIENTE` es una gestión, sin estructura ni campos de dependientes; tampoco hay pólizas ni motor de cobertura.
- `persona_id` es FK nullable a `Persona`; nombre, cédula y área se proyectan desde esa relación cuando existe, sin duplicación. Fecha, descripción, observación y responsable de negocio son nullable. No se creó estado, monto ni catálogo adicional.
- Autor proviene exclusivamente de la sesión mediante los metadatos existentes. Las rutas exigen el scope aditivo `OFICINA`, que no concede Producción ni las APIs transversales.
- Los listados mantienen filtros server-side reales (Persona/nombre, cédula, área, responsable, fecha, tipo y tipo de gestión cuando aplica) y el contrato `items`, `total`, `limite`, `offset`. Formularios y Documentos permanecen sin wrappers ni integración profunda hasta el Bloque 4.

Migración `0022_beneficios_prestamos_seguros`, posterior a `0021`: crea exclusivamente las tres tablas, FKs nullable hacia `personas`, constraints de tipos confirmados e índices de Persona y tipo/fecha. Su downgrade elimina únicamente esas tablas. No se modificó Atenciones Oficina ni se inició frontend o Bloque 3.

## 16. Bloque 3 — Frontend de Oficina

**IMPLEMENTADO Y VALIDADO.** Las cuatro rutas operativas reutilizan una sola familia configurable de vistas (`EntityListPage`, `EntityFormModal` y `EntityDetailPage`) y clientes contextuales. No se crearon `BeneficiosPage`, `PrestamosPage` ni `SeguroPage` paralelos.

- Beneficios, Préstamos y Seguro consumen exclusivamente `/api/v1/oficina/beneficios`, `/prestamos` y `/seguro`; Atenciones usa exclusivamente `/api/v1/oficina/atenciones`. Ninguna vista Oficina llama las APIs transversales ni las de Producción.
- Las configuraciones representan los tipos aprobados mediante selects, sin valores inventados. Persona usa `persona_id` nullable para las tres entidades nuevas, permite selección, sustitución, limpieza y guardado sin Persona. La Atención conserva el contrato existente y no expone `contexto_operativo`.
- Tablas y detalles separan Persona, responsable y registrado por. Los filtros se envían al servidor según contrato, con paginación `items`, `total`, `limite`, `offset`, y conservan los estados de carga, vacío, error, 401 y 403.
- Los detalles de Oficina no montan Formularios ni Documentos: la ruta Oficina/Formularios continúa usando el repositorio contextual existente. Integraciones profundas, documentos y BLOB quedan reservados para Bloque 4.

Validación: pruebas focalizadas Oficina y regresión Producción 7/7; suite frontend serial 128/128 en 20 archivos; build y `git diff --check` aprobados. Validación visual manual APROBADA en las cinco rutas contextuales, en desktop (1440x900), tablet (768x1024) y móvil (390x844): navegación, sidebar, filtros, paginación, formularios/modales, tablas y responsive correctos, sin solapamientos, controles fuera de pantalla ni errores visuales bloqueantes. Fase 8 no está completa; el siguiente trabajo autorizado es Bloque 4 — Integraciones de Oficina.

## 17. Bloque 4 — Integraciones de Oficina

**IMPLEMENTADO Y VALIDADO.** Los cuatro registros operativos de Oficina reutilizan `ContextFormsPanel`, `DynamicResponsePage` y `DocumentosPanel`, con `oficinaKind` explícito. No se duplicó el repositorio central ni se crearon vistas, almacenamiento BLOB o historial paralelos.

- Formularios se listan sólo por el destino hoja real de cada registro: `BENEFICIOS`, `OFICINA_ATENCIONES`, `PRESTAMOS` o `SEGURO`. El wrapper contextual fija registro, contexto y destino al guardar; ignora intentos de manipularlos y una respuesta no crea Beneficio, Atención, Préstamo ni Seguro. Las plantillas multidestino continúan únicas y la respuesta conserva su `id_destino_respuesta` concreto.
- Documentos reutiliza el servicio existente después de verificar el registro y scope `OFICINA`. En Atenciones, el wrapper exige `contexto_operativo="OFICINA"`; registros Producción e históricos `NULL` se rechazan. Permisos, auditoría e historial existentes permanecen como fuente única.
- Validación final: backend `267/267` (exit 0; 83.144 s; sin fallos ni errores), frontend serial `128/128` en 20 suites (exit 0), focalizadas backend `test_oficina` `4/4` y frontend `OficinaEntities.test.tsx` `4/4`, build (exit 0), `alembic heads` `0022_beneficios_prestamos_seguros`, `alembic check` y `git diff --check` aprobados. La suite global cubre las regresiones de Producción y del repositorio central/destinos/respuestas de Fase 5.

Fase 8 no está completa; el siguiente trabajo autorizado es Bloque 5 — Integración, regresión y cierre.
