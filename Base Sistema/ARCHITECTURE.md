# Arquitectura técnica

## Alcance de la versión

El Sistema Integral de Gestión de Trabajo Social es una Web App interna construida con Google Apps Script V8, HTML Service, JavaScript Vanilla, Google Sheets y Google Drive. La versión inicial prioriza despliegue sencillo, trazabilidad y un modelo normalizado que pueda migrarse sin cambiar sus UUID.

No es un formulario HTML estático: la configuración de formularios, preguntas, opciones y reglas vive en datos; los procesos operativos tienen tablas propias; las evidencias se guardan en Drive; cada operación se autoriza y audita en el servidor.

## Vista de componentes

```text
┌──────────────────────────────── Navegador ────────────────────────────────┐
│ HTML Service: shell, navegación, vistas, constructor, formularios         │
│ JavaScript Vanilla: estado local, validación UX, render, RPC asíncrono    │
└───────────────────────────────┬───────────────────────────────────────────┘
                                │ google.script.run
┌───────────────────────────────▼ Apps Script V8 ──────────────────────────┐
│ Code/API ─ Auth ─ Validación ─ Servicios de dominio ─ Errores            │
│                     │                 │                 │                 │
│                 Auditoría        DataService       DriveService          │
└─────────────────────┬─────────────────┬─────────────────┬────────────────┘
                      │                 │                 │
             Script Properties    Google Sheets       Google Drive
             IDs/configuración    24 hojas            evidencias/exportes
```

### Fronteras

- El navegador nunca es una frontera de seguridad. Los controles ocultos y validaciones cliente son solo experiencia de usuario.
- Las funciones públicas de `Code.gs` forman la API RPC. Deben devolver objetos serializables y pasar por `TSErrors.guard()`.
- Los servicios de dominio autorizan cada acción antes de consultar o mutar datos.
- `DataService.gs` es el único acceso genérico a las hojas; aplica esquemas, versiones, caché e invalidación.
- `DriveService.gs` es el único acceso documental y no crea permisos públicos.
- `TS_SPREADSHEET_ID`, `TS_ROOT_FOLDER_ID` y el ID interno de staging `TS_IMPORT_FOLDER_ID` se guardan en Script Properties y no se envían al cliente.

## Capas y responsabilidades

| Capa | Archivos | Responsabilidad |
|---|---|---|
| Entrada y composición | `Code.gs`, `Index.html` | `doGet`, `include`, bootstrap y funciones RPC públicas |
| Shell de interfaz | `App.html`, `Styles.html`, `Scripts.html`, `Components.html` | layout responsive, navegación, estado, componentes, llamadas asíncronas y feedback |
| Vistas | `Dashboard.html`, `DynamicForm.html`, `FormBuilder.html`, `CaseView.html`, `SearchView.html`, `AdminView.html` | pantallas funcionales cargadas dentro del shell |
| Configuración | `Config.gs`, `appsscript.json` | constantes, esquemas, módulos, límites, Script Properties, runtime, scopes y acceso de Web App |
| Base común | `Utils.gs`, `ErrorService.gs`, `ValidationService.gs` | UUID, normalización, serialización segura, bloqueos, errores amigables, reglas y validación de payloads/archivos |
| Persistencia | `DataService.gs` | lectura por lotes, búsqueda por ID, inserción, actualización, versión optimista, soft delete, restauración y caché |
| Identidad/RBAC | `AuthService.gs` | usuario activo, rol, matriz de permisos, sensibilidad, enmascaramiento y administración de acceso |
| Auditoría | `AuditService.gs` | eventos append-only por campo, redacción sensible y correlación |
| Formularios | `FormService.gs` | CRUD de formularios/preguntas/opciones, publicación, orden, condiciones, cálculos seguros, borradores y respuestas tipadas |
| Casos | `CaseService.gs` | creación, lectura, actualización, cierre, detalle sensible, historial y acciones del caso |
| Procesos | `ProcessService.gs` | atenciones, novedades, recorridos/hallazgos, seguimientos, derivaciones, compromisos, soft delete/restauración y borrado definitivo controlado |
| Catálogos | `CatalogService.gs` | catálogos jerárquicos, activación/desactivación y protección de valores usados |
| Documentos | `DriveService.gs` | validación binaria, carpetas por entidad/registro, metadatos, listado y acceso auditado |
| Consulta/reporting | `SearchService.gs`, `ExportService.gs` | búsqueda global, filtros, paginación, enmascaramiento y exportación autorizada |
| Históricos | `ImportService.gs` | validación de encabezados, detección de duplicados, lotes y trazabilidad de origen |
| Provisionamiento | `Setup.gs` | instalación/migración idempotente, hojas, encabezados, catálogos técnicos, roles, permisos y administrador inicial |

## API y patrón de llamadas

HTML Service no ofrece un servidor HTTP tradicional dentro de la vista; usa `google.script.run`, que es asíncrono. `Scripts.html` centraliza el patrón:

1. activar estado de carga y bloquear el control que dispara la operación;
2. invocar una función pública de `Code.gs`;
3. procesar la envoltura `{ok, data, message, correlationId}`;
4. mostrar un mensaje seguro y actualizar solo el estado afectado;
5. liberar el control tanto en éxito como en error.

No se deben lanzar escrituras dependientes en paralelo: Apps Script no garantiza el orden de dos llamadas asíncronas. El servidor vuelve a validar permisos, reglas e identidad en cada llamada.

Las funciones internas terminadas en `_` no se exponen mediante `google.script.run`. Los servicios se agrupan en objetos congelados (`TSData`, `TSAuth`, `TSForms`, etc.) para reducir el espacio global.

## Flujos principales

### Inicio y autorización

1. `doGet()` compone `Index.html` y sus parciales.
2. La interfaz solicita el bootstrap.
3. `TSAuth.current()` obtiene el correo de `Session`, busca el usuario activo, resuelve rol y permisos.
4. El servidor devuelve perfil, resumen de permisos, configuración pública y datos iniciales; nunca devuelve IDs de infraestructura.
5. El cliente muestra únicamente navegación autorizada. La autorización real se repite en cada operación.

Si el correo está vacío, el usuario no existe o está deshabilitado, el proceso falla de forma cerrada.

### Escritura de una entidad

```text
UI → función RPC → Auth → Validation → LockService
   → leer versión/relaciones → escribir fila → invalidar caché
   → escribir Auditoria → respuesta serializable
```

- El UUID se genera antes de escribir.
- La actualización acepta `expectedVersion`; si otra persona modificó la fila, se devuelve `VERSION_CONFLICT` y no se sobrescribe.
- Las reglas de negocio se aplican en servidor.
- El borrado normal cambia metadatos; no elimina la fila. El borrado físico está deshabilitado inicialmente y, si se habilita expresamente, exige Administrador, permiso de eliminación, soft delete previo, motivo, confirmación `BORRAR:<id>` y ausencia de dependencias/documentos; conserva Auditoría.
- `CorrelationId` enlaza respuesta, logs y auditoría.

### Formulario dinámico

1. Administración crea un formulario en `BORRADOR`.
2. Agrega preguntas, opciones y condiciones; el orden se cambia con operaciones estables.
3. La vista previa consume la misma definición que el capturador.
4. Para publicar se exige al menos una pregunta.
5. El usuario carga una definición `PUBLICADO`; el cliente renderiza controles por `Tipo` y aplica condiciones.
6. El servidor recalcula visibilidad, obligatoriedad y campos calculados admitidos (`SUM`, `CONCAT`, `TODAY`); no ejecuta código arbitrario.
7. Cada envío recibe `IdRespuesta`; cada pregunta produce una o varias filas tipadas en `RespuestasFormulario`.
8. `IdEnvioCliente` evita duplicar un reenvío del navegador. Un borrador queda en estado `BORRADOR`; el envío final queda `REGISTRADO`.

Para selección múltiple se genera una fila por valor, lo que mantiene la analítica normalizada.

Una pregunta `PERSONA` no es texto libre: el cliente consulta remotamente el maestro por nombre, cédula o código, y guarda el `IdPersona` seleccionado más la instantánea estructurada del nombre. El servidor vuelve a validar la referencia antes de persistir.

### Caso y ciclo de vida

- Un caso mantiene sus datos principales en `Casos` y el contenido restringido en `DetalleCasosSensibles`.
- Seguimientos, derivaciones, compromisos y cierres son entidades hijas; no duplican toda la fila del caso.
- Crear un cierre valida fecha/motivo y actualiza el caso principal durante la operación protegida.
- Las consultas sin `PuedeSensible` reciben campos enmascarados y nunca el detalle sensible.
- Ver detalle sensible, consultar historial o descargar evidencia genera auditoría según la acción.

### Gestión documental

1. El cliente convierte cada archivo permitido a base64 y envía metadatos.
2. El servidor autoriza edición del registro propietario.
3. Valida extensión, MIME, tamaño, cantidad y firma binaria real.
4. Dentro de un bloqueo crea `TrabajoSocial/<Entidad>/<UUID>/Documentos`.
5. Crea el archivo privado y registra metadatos en `Documentos`.
6. Si falla la escritura de metadatos, mueve a papelera los archivos recién creados como compensación.
7. Para abrir/descargar, vuelve a autorizar, audita y entrega un enlace sujeto también a las ACL de Drive.

La interfaz no ofrece enumeración global de todos los documentos. El acceso se inicia desde el expediente o registro propietario para conservar contexto y reducir exposición de metadatos.

### Búsqueda y exportación

- La búsqueda acepta solo tablas configuradas y filtros permitidos.
- Se normaliza el criterio, se excluyen registros eliminados y se pagina con `pageSize` predeterminado 20 y máximo 100.
- Los casos sensibles se enmascaran antes de llegar al cliente si falta permiso.
- La exportación vuelve a comprobar `PuedeExportar`, limita inicialmente a 5.000 filas y elimina campos no autorizados.
- CSV/Sheets de salida son artefactos secundarios; no sustituyen a la base ni deben hacerse públicos.

### Importación histórica

1. Administración selecciona tabla y aporta filas estructuradas con información de origen. Una fuente por ID debe ser Google Sheets nativo y estar como hijo directo de `TrabajoSocial/Importaciones`; CSV se transforma en filas tabulares en el cliente.
2. El servicio compara encabezados con el esquema permitido y genera un informe antes de mutar.
3. Detecta IDs repetidos en el lote y contra el destino; genera UUID solo cuando falta.
4. Aplica validación y reglas por fila.
5. Inserta el lote aceptado bajo bloqueo, completa metadatos de origen y audita `IMPORT`.
6. `Importaciones` conserva totales, estado y errores.

No se homologan categorías por aproximación. Los valores desconocidos deben revisarse antes de importarse.

## Concurrencia, consistencia y caché

- `LockService.getScriptLock()` serializa escrituras críticas con espera máxima configurable (30 s iniciales).
- UUID elimina la dependencia de `CountRows + 1`.
- `Version` implementa control optimista para ediciones desde pantallas desactualizadas.
- Los insert masivos usan un único `setValues()` y revisan duplicados en memoria.
- CacheService almacena lecturas por tabla durante 300 s; cada mutación incrementa `TS_TABLE_VERSION_<Tabla>`, por lo que una clave vieja deja de utilizarse.
- La caché puede desaparecer antes de tiempo; ninguna decisión duradera depende de ella.

La combinación Lock + Version reduce colisiones, pero Sheets no ofrece transacciones ACID entre hojas. Las operaciones compuestas usan orden explícito, auditoría y compensación donde es viable.

## Rendimiento

Decisiones implementadas:

- lecturas rectangulares por lote en vez de celda por celda;
- inserciones masivas con `setValues`;
- búsqueda de ID leyendo una sola columna antes de cargar la fila;
- caché versionada para catálogos/configuración/lecturas reutilizadas;
- paginación de resultados y límites de exportación;
- cliente sin frameworks ni dependencias remotas;
- formularios y vistas cargados como parciales de una sola Web App.

Advertencia: la búsqueda flexible sobre Sheets sigue leyendo y filtrando en memoria. La paginación limita el renderizado, no convierte Sheets en un motor indexado. Cuando crezca el volumen deben medirse tiempo de lectura, p95 de respuesta, concurrencia y uso de cuotas.

## Limitaciones reales de Apps Script

| Limitación | Impacto | Solución implementada | Alternativa futura |
|---|---|---|---|
| Ejecución de Apps Script: 6 minutos por ejecución; cuotas sujetas a cambio | Importaciones/exportaciones grandes pueden interrumpirse | lotes, límites, lecturas/escrituras masivas, errores explícitos y trazabilidad | trabajos asíncronos en Cloud Run/Functions con cola |
| `google.script.run` es asíncrono y admite hasta 10 llamadas simultáneas | respuestas fuera de orden y saturación si la UI dispara llamadas por campo | RPC centralizado, carga por vista, controles bloqueados e invocaciones secuenciales para escrituras | API HTTP propia con control de concurrencia |
| Google Sheets tiene hasta 10 millones de celdas y degrada antes según fórmulas/volumen | búsquedas y actualizaciones lineales pierden rendimiento | hojas normalizadas, caché, lectura por lotes, paginación y exportes limitados | Cloud SQL/Dataverse; Sheets queda como reporting |
| No hay claves foráneas ni transacciones multihoja | una operación compuesta puede quedar parcial ante fallo externo | validación previa, bloqueo, versión, auditoría y compensación documental | base relacional con transacciones |
| `Session.getActiveUser().getEmail()` depende del modo/política de despliegue | una identidad vacía impide RBAC | acceso de dominio, prueba obligatoria y fail-closed | ejecutar como usuario o autenticar mediante IdP/IAP |
| Transferir archivos por `google.script.run` usa base64 y memoria | aproximadamente 33 % de sobrecarga; archivos grandes agotan tiempo/memoria | 10 MiB por archivo, 10 por registro, validación antes de Drive | carga directa privada a Cloud Storage con URL firmada |
| Drive aplica sus propias ACL al enlace | un usuario autorizado por la app puede no abrir; compartir amplio permite acceso fuera de la app | archivos no públicos, autorización y auditoría antes de revelar enlace | gateway de descarga o carpetas/almacenamiento con ACL por grupo |
| CacheService es temporal y no garantiza persistencia | miss de caché o evicción | fallback transparente a Sheets; invalidación por versión | Redis/Memorystore si se adopta backend propio |
| Script Properties limita tamaño por valor/almacén | no sirve para datos transaccionales o catálogos grandes | solo IDs y JSON de configuración pequeño | Secret Manager/configuración de backend |
| HTML Service corre en un iframe con restricciones | algunas APIs/navegaciones del navegador no se comportan como sitio autónomo | HTML/CSS/JS compatibles y enlaces con `target="_blank"` cuando corresponde | frontend alojado separado |
| Power BI no obtiene seguridad por fila de la Web App | conectar la hoja transaccional puede eludir el RBAC | modelo normalizado y recomendación de dataset sanitizado separado | data warehouse con RLS y refresh administrado |

Fuentes: [cuotas de Apps Script](https://developers.google.com/apps-script/guides/services/quotas), [comunicación de HTML Service](https://developers.google.com/apps-script/guides/html/communication), [identidad de Session](https://developers.google.com/apps-script/reference/base/session) y [límites de archivos de Google Sheets](https://support.google.com/drive/answer/37603).

## Escalabilidad y criterios de migración

No se define un número mágico de filas: se migra cuando las métricas y controles dejan de cumplir el objetivo. Señales concretas:

- p95 de búsqueda o guardado superior al objetivo acordado durante periodos sostenidos;
- ejecuciones que se acercan repetidamente a seis minutos;
- contención frecuente de LockService o errores por cuota;
- volumen próximo al límite de celdas o exportaciones habituales por encima de 5.000 filas;
- necesidad de transacciones estrictas, seguridad por fila, API móvil/offline o integración en tiempo real;
- auditoría inmutable, cifrado de campo o residencia de datos que Sheets no cubre.

### Opciones

| Plataforma | Cuándo encaja | Consideración |
|---|---|---|
| AppSheet | digitalización rápida y móvil sobre volúmenes controlados | validar licencias, seguridad por fila y complejidad del constructor dinámico |
| SharePoint | organización centrada en Microsoft 365, listas y documentos | no sustituye por sí solo una base relacional de alto volumen |
| Dataverse | Power Platform, gobierno empresarial, RLS y Power BI | coste/licenciamiento y reimplementación de servicios |
| Firebase/Firestore | interacción móvil/realtime y escala horizontal | el modelo relacional y BI requieren desnormalización/ETL |
| Cloud SQL | integridad relacional, consultas complejas, transacciones y BI | requiere backend seguro, pooling y operación de infraestructura |

### Migración incremental recomendada

1. Congelar y versionar el esquema actual.
2. Crear un dataset de reporting separado y medir carga/uso real.
3. Mantener UUID y campos de trazabilidad como contrato estable.
4. Implementar carga inicial y reconciliar conteos/relaciones.
5. Durante transición, usar una sola fuente de escritura; evitar dual-write sin outbox/reintentos.
6. Migrar servicios de dominio detrás del mismo contrato RPC/API.
7. Validar permisos, sensibilidad, auditoría y documentos antes del corte.
8. Dejar Sheets en solo lectura por un periodo de conciliación aprobado.

## Decisiones que deben conservarse

- IDs de infraestructura solo en Script Properties.
- UUID estables en todas las plataformas.
- sensibilidad configurada por catálogo, no hardcodeada por categoría.
- autorización en servidor para cada operación.
- archivos fuera de las celdas.
- soft delete y auditoría por defecto.
- separación entre tablas transaccionales, maestro de personas, detalle sensible y respuestas dinámicas.
- ninguna fuente de Power BI publicada directamente con detalle sensible.
