# Sistema Integral de Gestión de Trabajo Social

Web App empresarial sobre Google Apps Script para configurar formularios, registrar y gestionar procesos de Trabajo Social, consultar casos, adjuntar evidencias, mantener trazabilidad y entregar datos normalizados para Power BI.

La solución usa HTML Service y JavaScript Vanilla en el cliente, servicios modulares Apps Script en el servidor, 24 hojas normalizadas en Google Sheets, documentos privados en Google Drive, Script Properties para configuración sensible, RBAC configurable, auditoría, soft delete, bloqueo de escrituras, control de versión, importación y exportación.

## Funcionalidad incluida

- formularios administrables, preguntas/opciones, orden, duplicación, publicación, vista previa, condiciones, cálculos seguros y respuestas tipadas;
- borrador y protección contra doble envío mediante `IdEnvioCliente`;
- personas, atenciones, casos, detalle sensible, novedades, recorridos, hallazgos, seguimientos, derivaciones, compromisos y cierres;
- consulta global con filtros, paginación, acciones por permiso y enmascaramiento sensible;
- archivos JPG/JPEG/PNG/PDF/DOC/DOCX/XLS/XLSX en Drive, con límite, firma binaria y acceso auditado;
- catálogos dependientes configurables, incluida la marca de sensibilidad;
- cinco roles base y matriz Crear/Leer/Editar/Eliminar/Sensible/Exportar;
- historial por campo, `CorrelationId`, soft delete, restauración y borrado definitivo excepcional con feature flag;
- importador histórico con preview, validación, UUID, duplicados y trazabilidad;
- exportación filtrada a CSV o Google Sheets;
- dashboard agregado y estructura lista para un modelo Power BI seguro.

Consulte [ARCHITECTURE.md](ARCHITECTURE.md) para decisiones y limitaciones, [DATA_MODEL.md](DATA_MODEL.md) para el contrato de datos, [SECURITY.md](SECURITY.md) antes de producción y [TEST_CHECKLIST.md](TEST_CHECKLIST.md) para QA.

## Requisitos

- Google Workspace; el despliegue está pensado para usuarios del mismo dominio.
- Cuenta institucional propietaria con capacidad de crear/editar Apps Script, Sheets y Drive.
- Permiso administrativo para aprobar los scopes del proyecto.
- Navegador moderno con JavaScript habilitado.
- Para despliegue por CLI: Node.js y [`@google/clasp`](https://github.com/google/clasp); es opcional.
- Catálogos funcionales aprobados por la organización. El setup crea solo estados técnicos mínimos y no inventa tipos de caso, áreas ni niveles sensibles.

## Arquitectura resumida

```text
Navegador / HTML Service
        │ google.script.run
        ▼
Code.gs → Auth + Validation + servicios de dominio
        ├── DataService → Google Sheets (24 hojas)
        ├── DriveService → Google Drive (evidencias)
        ├── AuditService → Auditoria
        └── Script Properties → IDs y configuración runtime
```

Todas las funciones RPC devuelven una envoltura serializable:

```javascript
{
  ok: true,
  data: {},
  message: "Cambios guardados.",
  correlationId: "REQ-..."
}
```

Un error esperado conserva `code`, mensaje amigable y `correlationId`; un fallo interno no envía stack trace al navegador.

## Manifest de archivos

### Runtime Apps Script

| Archivo | Responsabilidad |
|---|---|
| `appsscript.json` | runtime V8, zona horaria, logs, scopes explícitos y perfil de Web App de dominio |
| `Code.gs` | `doGet`, `include`, bootstrap y todos los endpoints RPC públicos |
| `Config.gs` | defaults, Script Properties, 24 esquemas, módulos, IDs de rol y configuración administrable |
| `Utils.gs` | UUID, fechas, normalización, serialización segura, CSV y `LockService` |
| `ErrorService.gs` | `TSAppError`, respuestas amigables y correlación |
| `ValidationService.gs` | whitelist de entidades/campos, preguntas, paginación, archivos y reglas de negocio |
| `DataService.gs` | repositorio Sheets, lectura por lotes, caché versionada, CRUD, versión, soft delete/restauración |
| `AuthService.gs` | identidad Workspace, usuarios, roles, permisos, sensibilidad y administración RBAC |
| `AuditService.gs` | auditoría append-only, redacción sensible y eventos por lote |
| `DriveService.gs` | estructura de carpetas, firmas binarias, carga, listado y acceso documental |
| `CatalogService.gs` | CRUD lógico, activación y catálogos dependientes |
| `FormService.gs` | constructor, preguntas/opciones, orden, publicación, condiciones, cálculos y respuestas |
| `CaseService.gs` | casos, detalle restringido, seguimientos, derivaciones, compromisos y cierres |
| `ProcessService.gs` | CRUD común de personas y procesos, referencias, soft delete, restauración, borrado físico controlado e historial |
| `SearchService.gs` | búsqueda multi-entidad, filtros, paginación, acciones y dashboard |
| `ImportService.gs` | preview/validación/ejecución de históricos y estado del lote |
| `ExportService.gs` | CSV y Google Sheets filtrados y autorizados |
| `Setup.gs` | setup owner-only e idempotente, hojas, roles/permisos, catálogos y configuración base |

### Interfaz HTML

| Archivo | Responsabilidad |
|---|---|
| `Index.html` | documento raíz y composición de parciales |
| `App.html` | cabecera, sidebar, navegación por rol y shell |
| `Styles.html` | sistema visual responsive, tarjetas, tablas, formularios, modales y estados |
| `Scripts.html` | estado cliente, RPC, navegación, render seguro y controladores de todos los módulos |
| `Components.html` | diálogos reutilizables, toasts, carga documental y componentes auxiliares |
| `Dashboard.html` | indicadores agregados y accesos rápidos |
| `DynamicForm.html` | capturador dinámico y borradores |
| `FormBuilder.html` | lista, editor, preguntas, opciones, orden y vista previa |
| `CaseView.html` | listado/detalle de casos y subprocesos |
| `SearchView.html` | consulta global, filtros, paginación, documentos y exportación |
| `AdminView.html` | catálogos, usuarios/roles/permisos, importación y configuración |

### Documentación y soporte

| Archivo | Responsabilidad |
|---|---|
| `README.md` | instalación, despliegue, uso, operación y troubleshooting |
| `ARCHITECTURE.md` | componentes, flujos, límites y migración |
| `DATA_MODEL.md` | hojas, columnas, relaciones e integración Power BI |
| `SECURITY.md` | threat model, controles, hardening, riesgos e incidentes |
| `TEST_CHECKLIST.md` | pruebas funcionales, negativas, seguridad, concurrencia y aceptación |
| `VALIDATION_REPORT.md` | evidencia automática de sintaxis, contratos RPC, HTML y consistencia del paquete |
| `.claspignore` | evita subir Markdown y archivos locales con `clasp push` |

## Configuración central

### Script Properties

Abra **Project Settings → Script properties**. Las propiedades principales son:

| Clave | Uso |
|---|---|
| `TS_SPREADSHEET_ID` | ID de la base Sheets. Si falta, setup crea el libro. |
| `TS_ROOT_FOLDER_ID` | ID de la carpeta Drive raíz. Si falta, setup crea `TrabajoSocial`. |
| `TS_IMPORT_FOLDER_ID` | ID interno de `TrabajoSocial/Importaciones`; setup lo crea/actualiza. No editar manualmente. |
| `TS_CONFIG_JSON` | overrides JSON de la configuración runtime. |
| `TS_SETUP_VERSION` | versión de estructura instalada; la escribe setup. |
| `TS_TABLE_VERSION_<Tabla>` | contador interno de invalidación de caché; no editar. |

Los IDs se guardan en Script Properties y **no se envían al cliente**. No los copie en HTML, parámetros de URL, catálogos, la hoja `Configuracion` ni mensajes de error. Los editores del proyecto sí pueden ver Script Properties: limite ese rol.

Defaults de `Config.gs`:

| Parámetro | Inicial |
|---|---:|
| `appName` | Sistema Integral de Gestion de Trabajo Social |
| `locale` | `es_EC` |
| `timeZone` | `America/Guayaquil` |
| `pageSize` / `maxPageSize` | 20 / 100 |
| `maxExportRows` / `maxImportRows` | 5.000 / 5.000 |
| `maxFileBytes` | 10 MiB |
| `maxFilesPerRecord` | 10 |
| `cacheSeconds` | 300 |
| `lockTimeoutMs` | 30.000 ms |
| `shareExportsWithRequester` | `true` |
| `allowTestIdentity` | `false` |
| `allowHardDelete` | `false` |

Ejemplo de `TS_CONFIG_JSON` parcial:

```json
{
  "appName": "Gestión de Trabajo Social",
  "pageSize": 25,
  "maxExportRows": 3000,
  "maxImportRows": 2000,
  "maxFileBytes": 8388608,
  "maxFilesPerRecord": 8,
  "cacheSeconds": 180,
  "shareExportsWithRequester": true
}
```

Administración puede cambiar los campos permitidos mediante `saveApplicationConfig`; el servicio actualiza Script Properties y refleja valores operativos en `Configuracion`. No edite esa hoja esperando que cambie el runtime.

`TS_TEST_USER_EMAIL` solo se considera si un desarrollador modifica `allowTestIdentity` a `true`. No habilite ese modo ni conserve esa propiedad en producción.

## Instalación manual en Apps Script

1. Entre con la cuenta institucional que será propietaria y cree un proyecto independiente en [script.google.com](https://script.google.com/).
2. En **Project Settings**, active **Show “appsscript.json” manifest file in editor**.
3. Reemplace el manifiesto con `appsscript.json`.
4. Cree cada archivo `.gs` y copie su contenido completo. Los nombres deben coincidir con el manifest anterior.
5. Cree cada archivo HTML y copie su contenido. En el editor, use el nombre sin duplicar la extensión; por ejemplo `Index` crea `Index.html`.
6. Guarde. Apps Script resuelve todos los `.gs` como un único espacio global; el orden visual de archivos no importa.
7. Si usará recursos existentes, configure `TS_SPREADSHEET_ID` y/o `TS_ROOT_FOLDER_ID` en Script Properties. La cuenta propietaria necesita acceso de edición.
8. Seleccione `setupApplication` y pulse **Run** desde el editor. No ejecute el primer setup desde la Web App.
9. Conceda los scopes solicitados de Sheets, Drive y correo de usuario.
10. Revise el objeto devuelto y confirme que `administratorCreated` es `true`.

### Instalación opcional con clasp

```bash
npm install -g @google/clasp
clasp login
clasp create --type standalone --title "Sistema Integral de Gestión de Trabajo Social"
clasp push
clasp open
```

Ejecute los comandos desde esta carpeta después de que `clasp create` genere `.clasp.json`, o vincule un proyecto existente con su Script ID. `.claspignore` excluye la documentación. Revise `clasp status` antes de cada push y nunca confirme `.clasp.json` de un entorno sensible en un repositorio público.

## Creación/verificación de Google Sheets

`setupApplication()` crea o completa estas 24 hojas:

`Usuarios`, `Roles`, `Permisos`, `Personas`, `Formularios`, `Preguntas`, `OpcionesPregunta`, `ReglasFormulario`, `RespuestasFormulario`, `Atenciones`, `Casos`, `DetalleCasosSensibles`, `Novedades`, `Recorridos`, `HallazgosRecorrido`, `Seguimientos`, `Derivaciones`, `Compromisos`, `Cierres`, `Documentos`, `Catalogos`, `Auditoria`, `Configuracion`, `Importaciones`.

El setup:

- crea encabezados, congela la primera fila y aplica formato básico;
- añade columnas faltantes al final cuando el prefijo existente coincide;
- se detiene ante encabezados incompatibles y no borra/renombra datos;
- conserva roles, permisos y catálogos ya existentes; solo inserta seeds ausentes;
- crea al ejecutor inicial como `ROLE_ADMIN` si Workspace entrega su correo;
- puede repetirse después de una actualización sin duplicar la estructura.

No reordene columnas manualmente. El contrato exacto está en [DATA_MODEL.md](DATA_MODEL.md).

## Configuración de Drive

Si `TS_ROOT_FOLDER_ID` está vacío, setup crea una carpeta privada `TrabajoSocial`. Las subcarpetas aparecen al cargar el primer archivo:

```text
TrabajoSocial/
  Importaciones/
  Casos/<IdCaso>/Documentos/
  Atenciones/<IdAtencion>/Documentos/
  Novedades/<IdNovedad>/Documentos/
  ...
  Exportaciones/
```

No cambie la propiedad a una carpeta pública. El código no publica archivos y los listados no exponen `DriveFileId`/URL. Al abrir un archivo, la app valida permisos y audita; Drive realiza además su propia comprobación de ACL. Si los usuarios deben abrir enlaces de Drive, otorgue acceso mediante grupos estrictos y manténgalos alineados con RBAC. Consulte las implicaciones en [SECURITY.md](SECURITY.md).

La pantalla global **Documentos** no enumera el repositorio completo: dirige al usuario al caso/registro y su pestaña documental. Esta decisión evita convertir nombres/metadatos sensibles en un directorio navegable; cada apertura permanece contextual y auditada.

## Primer arranque y datos base

1. Abra el Spreadsheet devuelto por setup y confirme las 24 hojas.
2. Abra la carpeta devuelta y confirme que no sea pública.
3. En `Usuarios`, verifique el correo del propietario con `ROLE_ADMIN`, `ACTIVO`, `Activo = TRUE` y `Eliminado = FALSE`.
4. Revise la matriz de permisos desde Administración.
5. Cargue únicamente catálogos aprobados: áreas, turnos, tipos, estados y niveles de sensibilidad. Marque `EsSensible` solo tras decisión funcional.
6. Cree usuarios finales y asigne rol. Un usuario del dominio no registrado queda bloqueado.
7. Cree un formulario de prueba, agregue preguntas, previsualice y publíquelo.
8. Ejecute el smoke test de [TEST_CHECKLIST.md](TEST_CHECKLIST.md) antes de desplegar.

Los únicos catálogos sembrados automáticamente son estados técnicos de formulario (`BORRADOR`, `PUBLICADO`, `INACTIVO`) y de caso (`BORRADOR`, `REGISTRADO`, `EN_GESTION`, `CERRADO`).

## Despliegue como Web App

1. En Apps Script seleccione **Deploy → New deployment**.
2. Tipo: **Web app**.
3. Descripción: incluya versión/fecha.
4. **Execute as:** la cuenta que despliega (`Me` / `USER_DEPLOYING`).
5. **Who has access:** usuarios del dominio (`DOMAIN`). Nunca habilite acceso anónimo.
6. Pulse **Deploy**, complete autorización y copie la URL `/exec`.
7. Abra la URL con el administrador inicial y una cuenta de prueba no administradora.
8. Confirme que ambas muestran su propio correo. Si aparece `IDENTITY_UNAVAILABLE`, detenga el despliegue y revise la modalidad/política de `Session`.
9. Confirme que una cuenta del dominio no registrada recibe acceso denegado.
10. Ejecute QA por rol, sensibilidad y documentos.

La URL `/dev` usa el código guardado más reciente y solo funciona para editores; no se distribuye como URL productiva.

### Actualizar una versión

1. Respaldar Spreadsheet y configuración; registrar el corte.
2. Subir todos los archivos de una misma versión.
3. Ejecutar `setupApplication()` desde el editor con la cuenta propietaria del script. En reruns, esa misma cuenta debe conservar además permiso `ADMINISTRACION:edit`.
4. Verificar que no exista conflicto de esquema.
5. En **Manage deployments**, editar el despliegue y seleccionar una versión nueva.
6. Ejecutar smoke, autorización, búsqueda, guardado y archivo.
7. Conservar la versión anterior para rollback de código. Un rollback de código no revierte datos; cualquier migración necesita su propio plan.

## Permisos

La matriz física es:

| Rol | Comportamiento inicial |
|---|---|
| Administrador | todos los módulos y acciones, incluido sensible, exportación y soft delete |
| Coordinador / Relaciones Laborales | lectura consolidada y auditoría; crea/edita procesos, respuestas y documentos; no elimina ni ve sensible inicialmente |
| Trabajador Social | crea/edita procesos, personas, respuestas y documentos; consulta operación; no elimina ni ve sensible inicialmente |
| Consulta | lectura operativa limitada, sin cambios/exportación/sensible |
| Gerencia | dashboard, consulta agregada y exportación de reportes, sin detalle sensible |

Los nombres y derechos son configurables. La captura de formularios usa el módulo `RESPUESTAS`, separado de `FORMULARIOS`, para que responder no conceda acceso al constructor. La carga documental exige a la vez edición sobre la entidad y creación en `DOCUMENTOS`.

## Uso operativo

### Administración

1. Dar de alta usuarios por correo y rol.
2. Ajustar permisos por módulo; aplicar mínimo privilegio.
3. Mantener catálogos y dependencias. Desactivar valores usados; no eliminarlos físicamente.
4. Crear formularios en borrador, añadir preguntas/opciones/condiciones y publicar tras vista previa.
5. Ejecutar importaciones primero en modo validación y revisar todos los errores.
6. Revisar parámetros, auditoría y ejecuciones fallidas.

### Captura

1. Seleccionar Nueva atención, Nuevo caso, Nueva novedad, Nuevo recorrido o un formulario publicado.
2. Completar campos; el navegador valida para UX y el servidor repite validación.
   En una pregunta `PERSONA`, buscar por nombre, cédula o código, elegir el resultado remoto y conservar `IdPersona` junto con la instantánea estructurada del nombre; no escribir una persona libre.
3. Guardar borrador si el formulario es extenso.
4. Adjuntar archivos después de que exista el UUID del registro.
5. Confirmar el mensaje de éxito; si la red falla, buscar el registro antes de reenviar.

### Gestión de casos

- La vista de caso reúne detalle, seguimientos, derivaciones, compromisos, cierres, documentos e historial.
- Seguimientos actualizan `UltimoSeguimiento`; derivaciones marcan el caso; el cierre crea su entidad y actualiza el caso.
- Un cambio concurrente devuelve `VERSION_CONFLICT`; recargue, compare y vuelva a aplicar conscientemente.
- Eliminar requiere rol y motivo; la fila queda recuperable. Restaurar usa el mismo permiso de eliminación.
- La eliminación definitiva permanece deshabilitada por defecto. Si una política formal activa `allowHardDelete`, solo un usuario con `ADMINISTRACION:edit`, permiso de eliminar sobre la entidad y permiso sensible cuando aplique puede retirar una fila que ya tenga soft delete, no posea dependencias/documentos y confirme exactamente `BORRAR:<Id>` con motivo. Auditoría se conserva y no existe borrado en cascada.

### Consulta y reportes

- Combine texto, entidad, fechas, responsable, área, estado, tipo, prioridad, sensibilidad, colaborador y código.
- Los resultados se paginan; las acciones se calculan por registro/rol.
- CSV se devuelve al navegador; Google Sheets crea un libro privado en `Exportaciones`.
- Exportar vuelve a comprobar permiso y limita a 5.000 filas por defecto.

## Importación histórica

Tablas admitidas: personas y entidades de proceso, incluido detalle sensible con permiso explícito. Para una fuente Google Sheets, mueva el archivo nativo como hijo directo de `TrabajoSocial/Importaciones` y use `spreadsheetId` + `sheetName`; el servidor rechaza archivos fuera de staging y archivos cuyo MIME no sea Google Sheets. Para CSV, la interfaz procesa el archivo localmente y envía encabezados/filas tabulares al mismo validador; el binario no se convierte en fuente arbitraria de Drive.

Flujo obligatorio:

1. crear respaldo;
2. seleccionar tabla destino;
3. validar encabezados y preview;
4. corregir encabezados desconocidos, obligatorios, fechas, referencias, UUID y códigos duplicados;
5. ejecutar solo cuando `valid = true`;
6. registrar `IdImportacion` y conciliar filas;
7. revisar metadatos `ArchivoFuente`, `HojaFuente`, `RegistroFuente`, `FechaImportacion`, `UsuarioImportacion`.

Máximo inicial: 5.000 filas por ejecución. Si una sola fila falla validación, no se ejecuta el lote. Sheets no ofrece rollback transaccional multihoja: ante un fallo de infraestructura durante la escritura, revise `Importaciones`, filas y auditoría antes de reintentar. No homologue categorías por similitud automática.

## Power BI

El modelo recomendado está detallado en [DATA_MODEL.md](DATA_MODEL.md). Para una integración segura:

1. no publique la base transaccional en la web;
2. cree un libro/dataset de reporting separado con columnas autorizadas, o use exportación controlada;
3. filtre `Activo = TRUE` y `Eliminado = FALSE`;
4. trate UUID, cédula y código de empleado como texto;
5. cree dimensión fecha y relaciones 1:N desde `Personas`, `Catalogos`, `Formularios` y `Preguntas` hacia hechos;
6. excluya `DetalleCasosSensibles`, `Usuarios`, `Permisos`, `Auditoria` y `Configuracion` del modelo gerencial;
7. configure credenciales, refresh y acceso del workspace de Power BI según gobierno corporativo;
8. reconcilie conteos con búsqueda/dashboard para la misma fecha de corte.

La Web App no implementa seguridad por fila dentro de Power BI. El dataset de reporting debe aplicar su propio RLS/gobierno.

## Pruebas

La estrategia completa está en [TEST_CHECKLIST.md](TEST_CHECKLIST.md). Como mínimo, antes de producción pruebe:

- setup y segundo setup;
- alta/edición/búsqueda de atención y caso;
- seguimiento, derivación, compromiso y cierre;
- borrador, publicación, condiciones y doble envío;
- imagen, PDF, Office, firma inválida, tamaño y cantidad;
- soft delete, restauración e historial;
- usuario sin permiso e intento de RPC directo;
- caso sensible con/sin permiso;
- dos ediciones concurrentes y conflicto de versión;
- importación válida/inválida y exportación CSV/Sheets;
- escritorio, tablet, móvil y teclado.

## Operación y mantenimiento

- Revise Apps Script Dashboard, fallos y cuotas; use `correlationId` para investigar.
- Revise altas/bajas, administradores, sensibilidad y ACL de Drive periódicamente.
- Haga respaldo antes de importaciones y actualizaciones de esquema.
- No edite filas directamente en producción salvo procedimiento de emergencia documentado.
- No borre archivos de Drive manualmente: dejaría metadatos huérfanos.
- No borre propiedades `TS_TABLE_VERSION_*`; son internas, aunque una pérdida solo invalida la optimización.
- Mida p95 de búsqueda/guardado, filas, celdas, duración de lotes y contención de locks.
- Evalúe migración cuando Apps Script/Sheets deje de cumplir SLA, atomicidad, seguridad por fila o volumen; vea [ARCHITECTURE.md](ARCHITECTURE.md).

## Solución de problemas

| Código/síntoma | Causa probable | Acción |
|---|---|---|
| `NOT_CONFIGURED` | falta `TS_SPREADSHEET_ID` | ejecutar setup como propietario |
| `SETUP_OWNER_ONLY` | setup llamado por otro usuario/contexto | ejecutarlo desde el editor con la cuenta que despliega |
| `SETUP_SCHEMA_CONFLICT` / `SCHEMA_MISMATCH` | encabezado renombrado/reordenado | restaurar desde `Config.gs`/backup; no forzar escritura |
| `IDENTITY_UNAVAILABLE` | `Session` no entrega correo en esa modalidad | verificar dominio y ejecución; no habilitar identidad de prueba |
| `USER_NOT_REGISTERED` | correo no existe en `Usuarios` | Administrador da de alta correo en minúsculas |
| `USER_DISABLED` | usuario inactivo | revisar baja y reactivar solo con aprobación |
| `FORBIDDEN` / `SENSITIVE_FORBIDDEN` | la matriz no concede acción/sensible | revisar rol y permiso exacto; no resolver mostrando solo el botón |
| `VERSION_CONFLICT` | otra sesión guardó primero | recargar, comparar y reintentar con nueva versión |
| `LOCK_TIMEOUT` | escritura larga/concurrente >30 s | esperar, verificar si se guardó y reintentar una vez |
| `HARD_DELETE_DISABLED` | eliminación definitiva no aprobada/activada | usar soft delete; habilitar solo mediante cambio formal de Administrador |
| `HARD_DELETE_REQUIRES_SOFT_DELETE` / `RECORD_HAS_DEPENDENCIES` | no cumple prerrequisitos del borrado físico | eliminar lógicamente primero o conservar el registro mientras tenga relaciones/documentos |
| `FILE_*` | extensión, MIME, firma, base64, tamaño o cantidad inválidos | usar archivo permitido y revisar política mostrada |
| Archivo no abre | ACL de Drive no concede acceso | revisar grupo/carpeta; nunca hacerlo público para resolverlo |
| `IMPORT_VALIDATION_FAILED` | existe al menos un error de lote | descargar/revisar reporte, corregir todas las filas y revalidar |
| Exportación truncada | total supera `maxExportRows` | acotar filtros o ejecutar cortes controlados |
| Dashboard vacío | sin permiso o datos vigentes | revisar `DASHBOARD:read`, filtros y metadatos Activo/Eliminado |
| UI desactualizada tras deploy | versión/cache del navegador | confirmar despliegue `/exec`, recargar sin caché y verificar versión |
| Error genérico | fallo no controlado o cuota | buscar `correlationId` en ejecuciones; no pedir al usuario datos sensibles |

## Limitaciones y mejoras futuras

Apps Script impone tiempo de ejecución, concurrencia y cuotas; HTML Service es asíncrono; Sheets no tiene transacciones/índices/seguridad por fila; Drive conserva una ACL independiente; base64 limita tamaño práctico; Power BI necesita una capa de reporting segura. La tabla **Limitación → Impacto → Solución implementada → Alternativa futura** está en [ARCHITECTURE.md](ARCHITECTURE.md).

Fuentes oficiales: [cuotas de Apps Script](https://developers.google.com/apps-script/guides/services/quotas), [Web Apps](https://developers.google.com/apps-script/guides/web), [Session](https://developers.google.com/apps-script/reference/base/session), [HTML Service RPC](https://developers.google.com/apps-script/guides/html/communication) y [autorización](https://developers.google.com/apps-script/guides/services/authorization).

## Checklist de producción

- [ ] Documentos [SECURITY.md](SECURITY.md) y [TEST_CHECKLIST.md](TEST_CHECKLIST.md) aprobados.
- [ ] Propietario institucional con MFA y sucesión.
- [ ] URL restringida al dominio y correo de sesión verificado.
- [ ] Spreadsheet/Drive sin acceso público; editores mínimos.
- [ ] Administrador inicial, usuarios y permisos revisados.
- [ ] Catálogos reales cargados sin inventar/homologar dudas.
- [ ] Sensibilidad configurada y probada con dos roles.
- [ ] Backups y retención definidos.
- [ ] Dataset Power BI separado y sanitizado.
- [ ] Versión de despliegue, responsable y rollback registrados.
