# Checklist de pruebas

Este checklist es el plan de verificación de la versión 1.0.0. Las casillas se entregan sin marcar: deben completarse en un proyecto QA de Google Apps Script/Workspace antes de promover a producción.

## Registro de ejecución

| Dato | Valor |
|---|---|
| Versión/commit | |
| Proyecto Apps Script QA | |
| ID de despliegue | |
| Spreadsheet QA | |
| Carpeta Drive QA | |
| Dominio | |
| Navegadores/dispositivos | |
| Responsable | |
| Fecha | |
| Resultado | `APROBADO` / `RECHAZADO` |

Para cada prueba guarde: usuario/rol, hora, datos de entrada, captura o respuesta, `correlationId`, filas afectadas y defecto asociado. Nunca adjunte datos personales reales al ticket.

## Preparación

- [ ] Crear proyecto, Spreadsheet y carpeta exclusivos de QA; no probar sobre producción.
- [ ] Configurar cinco cuentas o usuarios de prueba: Administrador, Coordinador, Trabajador Social, Consulta y Gerencia.
- [ ] Configurar al menos un nivel no sensible y uno sensible mediante `Catalogos.EsSensible`; no usar categorías reales si no fueron suministradas.
- [ ] Crear una persona ficticia con código/cédula de prueba.
- [ ] Preparar archivos mínimos válidos: JPG, PNG, PDF, DOC, DOCX, XLS y XLSX.
- [ ] Preparar negativos: extensión prohibida, MIME discordante, firma alterada, archivo vacío, archivo mayor a 10 MiB y lote de 11 archivos.
- [ ] Preparar hoja histórica válida dentro de `TrabajoSocial/Importaciones` y variantes con encabezado desconocido, encabezado obligatorio ausente, UUID duplicado, código de caso duplicado y referencia inexistente.
- [ ] Abrir el historial de ejecuciones de Apps Script y una copia del Spreadsheet para verificar efectos.

## 1. Instalación y configuración

| # | Prueba | Resultado esperado |
|---:|---|---|
| 1.1 | [ ] Ejecutar `setupApplication()` sin IDs previos. | Crea un Spreadsheet, carpeta raíz, 24 hojas, encabezados, Script Properties y datos base; devuelve resumen sin exponer secretos a la Web App. |
| 1.2 | [ ] Comprobar `TS_SPREADSHEET_ID`, `TS_ROOT_FOLDER_ID`, `TS_IMPORT_FOLDER_ID`, `TS_CONFIG_JSON` y `TS_SETUP_VERSION` en Script Properties. | IDs válidos; no aparecen en HTML ni bootstrap cliente; staging es `TrabajoSocial/Importaciones`. |
| 1.3 | [ ] Ejecutar `setupApplication()` por segunda vez. | Conserva los mismos IDs y datos; no duplica hojas, roles, permisos, catálogos ni administrador. |
| 1.4 | [ ] Configurar IDs de recursos existentes y ejecutar setup. | Usa los recursos indicados, crea solo estructura faltante y no borra filas existentes. |
| 1.5 | [ ] Alterar temporalmente un encabezado en QA e intentar una operación. | Falla con `SCHEMA_MISMATCH`; no escribe en una columna incorrecta. Restaurar el encabezado. |
| 1.6 | [ ] Verificar zona horaria del script y Spreadsheet. | Ambas corresponden a `America/Guayaquil`; una fecha/hora de prueba se conserva correctamente. |
| 1.7 | [ ] Revisar permisos de Drive/Sheet tras setup. | No existe acceso público ni “cualquiera con el enlace”. |
| 1.8 | [ ] Invocar `setupApplication()` con una cuenta distinta de la propietaria y repetir como propietario sin `ADMINISTRACION:edit` en una instalación existente. | Ambos intentos se rechazan; el primer setup exige propietario y los reruns exigen además administración. |

## 2. Identidad, roles y navegación

| # | Prueba | Resultado esperado |
|---:|---|---|
| 2.1 | [ ] Entrar como Administrador registrado. | Se identifica correo/rol y aparecen módulos autorizados. |
| 2.2 | [ ] Entrar como usuario del dominio no registrado. | Acceso denegado con mensaje amigable; no se muestran datos. |
| 2.3 | [ ] Desactivar un usuario y reintentar. | `USER_DISABLED`; ninguna operación queda permitida. |
| 2.4 | [ ] Probar un contexto en que `Session` no entregue correo. | `IDENTITY_UNAVAILABLE`; no usa la cuenta propietaria ni una identidad de prueba. |
| 2.5 | [ ] Entrar con cada rol base. | Menú y acciones corresponden a la matriz `Permisos`. |
| 2.6 | [ ] Invocar desde consola una función de escritura cuyo botón está oculto. | El servidor devuelve `FORBIDDEN`; no se crea ni modifica fila. |
| 2.7 | [ ] Quitar un permiso a una sesión activa e invocar otra operación. | La operación nueva respeta la matriz actual; no depende solo del menú ya renderizado. |
| 2.8 | [ ] Cambiar rol/estado desde Administración con versión vigente. | Cambio auditado y efectivo. |
| 2.9 | [ ] Guardar cambios de permisos con una `expectedVersion` obsoleta. | `VERSION_CONFLICT`; no sobrescribe el cambio más reciente. |
| 2.10 | [ ] Confirmar actualización de `UltimoAcceso`. | Se actualiza sin escribir en cada llamada gracias a caché de usuario. |

## 3. Constructor de formularios

| # | Prueba | Resultado esperado |
|---:|---|---|
| 3.1 | [ ] Crear formulario con nombre, descripción, proceso y responsable. | Estado inicial `BORRADOR`, UUID y auditoría `CREATE`. |
| 3.2 | [ ] Intentar publicar formulario sin preguntas. | Rechazado con mensaje “Agregue al menos una pregunta”. |
| 3.3 | [ ] Crear una pregunta de cada tipo permitido. | Definición recuperable y vista previa estable; tipos inválidos se rechazan. |
| 3.4 | [ ] Configurar obligatorio, ayuda, longitud máxima, solo lectura, oculto y valor predeterminado. | Vista previa y guardado respetan propiedades; longitud > 50.000 se rechaza. |
| 3.5 | [ ] Crear lista, selección única y múltiple con opciones. | Opciones persisten en orden y se renderizan sin editar HTML. |
| 3.6 | [ ] Editar etiqueta/tipo/opciones de una pregunta. | Incrementa `Version`; auditoría refleja solo campos cambiados. |
| 3.7 | [ ] Duplicar pregunta. | Crea nuevo `IdPregunta`, copia propiedades/opciones y asigna nuevo orden. |
| 3.8 | [ ] Mover pregunta arriba/abajo. | Orden contiguo y determinista; no se pierden preguntas. |
| 3.9 | [ ] Desactivar una pregunta con motivo. | Deja de aparecer; la fila histórica y auditoría permanecen. |
| 3.10 | [ ] Publicar y luego inactivar un formulario. | Solo `PUBLICADO` aparece al usuario final; `INACTIVO` queda administrable. |
| 3.11 | [ ] Vista previa antes de publicar. | Usa la definición actual sin crear respuesta definitiva. |

## 4. Formularios dinámicos, condiciones y borradores

| # | Prueba | Resultado esperado |
|---:|---|---|
| 4.1 | [ ] Configurar `¿Genera caso? = Sí` para mostrar campos dependientes. | Los campos cambian de visibilidad en cliente y servidor evalúa la misma condición. |
| 4.2 | [ ] Enviar un campo obligatorio que está oculto por condición. | No bloquea el envío ni crea una respuesta visible indebida. |
| 4.3 | [ ] Hacer visible el campo obligatorio y dejarlo vacío. | Validación cliente y `REQUIRED_ANSWERS` en servidor. |
| 4.4 | [ ] Probar operadores `EQ`, `NE`, `CONTAINS`, `IN`, `EMPTY` y `NOT_EMPTY`. | Resultado consistente en los valores de prueba. |
| 4.5 | [ ] Probar `SUM(id1,id2)`, `CONCAT(id1,id2)` y `TODAY()`. | Cálculo correcto; una fórmula no admitida no ejecuta JavaScript y usa el valor predeterminado/vacío. |
| 4.6 | [ ] Guardar formulario incompleto como borrador. | Estado `BORRADOR`; conserva `IdRespuesta` y permite continuar. |
| 4.7 | [ ] Finalizar el borrador. | Filas anteriores quedan inactivas y se crea la versión `REGISTRADO`; no se pierde auditoría. |
| 4.8 | [ ] Enviar selección múltiple con tres opciones. | Tres filas de detalle con un `IdRespuesta`, una por `ValorOpcion`. |
| 4.9 | [ ] Verificar número, fecha, sí/no y texto. | Solo la columna tipada `ValorNumero`, `ValorFecha`, `ValorBooleano` o `ValorTexto` correspondiente queda poblada. |
| 4.10 | [ ] Pulsar Guardar dos veces rápidamente con el mismo `IdEnvioCliente`. | Se reconoce el reenvío y no crea una segunda respuesta lógica. |
| 4.11 | [ ] Alterar el payload desde DevTools con pregunta inexistente. | El servidor ignora/rechaza datos fuera de la definición y no crea columnas. |

## 5. Personas, atenciones, novedades y recorridos

| # | Prueba | Resultado esperado |
|---:|---|---|
| 5.1 | [ ] Crear una persona y reutilizarla en una atención/caso. | Las transacciones guardan `IdPersona`; no duplican el maestro. |
| 5.2 | [ ] Referenciar un `IdPersona` inexistente. | `PERSON_NOT_FOUND`; no escribe. |
| 5.3 | [ ] Crear atención con fecha, responsable y motivo. | UUID, metadatos, estado y auditoría correctos. |
| 5.4 | [ ] Crear novedad con fecha, responsable, descripción y estado. | Registro recuperable por búsqueda y auditoría `CREATE`. |
| 5.5 | [ ] Crear recorrido y dos hallazgos. | Un recorrido y dos filas hijas enlazadas por `IdRecorrido`. |
| 5.6 | [ ] Crear hallazgo con recorrido inexistente. | `TOUR_NOT_FOUND`; no queda huérfano. |
| 5.7 | [ ] Enlazar hallazgo a novedad y caso. | `IdNovedad`/`IdCaso` preservan `Recorrido → Hallazgo → Novedad → Caso`. |
| 5.8 | [ ] Editar registro con la versión actual. | Conserva ID y creación; incrementa versión, fecha/usuario de actualización y auditoría. |

## 6. Casos y ciclo de gestión

| # | Prueba | Resultado esperado |
|---:|---|---|
| 6.1 | [ ] Crear caso mínimo válido. | UUID, `CodigoCaso` robusto `CAS-AAAA-*`, estado y auditoría; código único. |
| 6.2 | [ ] Intentar código de caso duplicado. | `DUPLICATE_CASE_CODE`; no crea fila. |
| 6.3 | [ ] Editar caso y conservar el ID. | Mismo `IdCaso`, `Version + 1` e historial por campo. |
| 6.4 | [ ] Marcar restricción sin fecha de inicio. | Validación rechaza; con fecha válida permite guardar. |
| 6.5 | [ ] Crear seguimiento con fecha/responsable/descripción. | Fila hija y `Casos.UltimoSeguimiento` actualizado. |
| 6.6 | [ ] Indicar próxima acción sin fecha. | Rechazado; con fecha se guarda. |
| 6.7 | [ ] Crear derivación sin área destino. | Rechazado; con destino/motivo se guarda y `Casos.Derivacion = TRUE`. |
| 6.8 | [ ] Crear compromiso sin responsable o estado. | Rechazado; completo se enlaza al caso/seguimiento. |
| 6.9 | [ ] Cerrar sin fecha o motivo. | Rechazado; no cambia el caso. |
| 6.10 | [ ] Cerrar con datos completos. | Crea `Cierres` y actualiza `Casos.EstadoCaso`, `FechaCierre`, `MotivoCierre` y resultado. |
| 6.11 | [ ] Abrir la vista del caso. | Muestra seguimientos, derivaciones, compromisos, cierres, archivos e historial autorizados sin duplicar el caso. |
| 6.12 | [ ] Dos usuarios cargan la misma versión y ambos editan. | El primero guarda; el segundo recibe `VERSION_CONFLICT` y debe recargar. |

## 7. Casos sensibles

| # | Prueba | Resultado esperado |
|---:|---|---|
| 7.1 | [ ] Crear nivel sensible mediante catálogo y un caso con ese nivel. | Sensibilidad se deriva de datos, no del texto hardcodeado. |
| 7.2 | [ ] Abrir como usuario con lectura y `PuedeSensible`. | Ve detalle autorizado; se registra `VIEW_SENSITIVE`. |
| 7.3 | [ ] Buscar como usuario sin `PuedeSensible`. | Resultado enmascarado con `[RESTRINGIDO]`; no expone cédula, persona, descripción u observaciones. |
| 7.4 | [ ] Invocar lectura directa del caso sensible sin permiso. | `SENSITIVE_FORBIDDEN`; no devuelve detalle ni relaciones. |
| 7.5 | [ ] Ver dashboard como Gerencia. | Solo agregados; no muestra detalle sensible. |
| 7.6 | [ ] Editar detalle sensible. | Requiere permiso sensible; auditoría registra el cambio sin copiar valores sensibles. |
| 7.7 | [ ] Exportar sin permiso sensible. | Dataset omite/enmascara los campos restringidos. |

## 8. Búsqueda, filtros y paginación

| # | Prueba | Resultado esperado |
|---:|---|---|
| 8.1 | [ ] Buscar por código/ID de caso. | Devuelve el registro exacto permitido. |
| 8.2 | [ ] Buscar por nombre, cédula y código de empleado. | Resuelve el maestro `Personas` sin incluir entidades no autorizadas. |
| 8.3 | [ ] Buscar texto permitido en cada tipo de entidad. | Coincidencia parcial sin buscar en detalle sensible. |
| 8.4 | [ ] Combinar fecha desde/hasta, responsable, área, estado, tipo, prioridad, sensibilidad, colaborador y código. | Solo registros que cumplen todos los filtros aplicables. Fecha hasta es inclusiva. |
| 8.5 | [ ] Pulsar “Limpiar filtros”. | Reinicia criterios, página y resultados de forma coherente. |
| 8.6 | [ ] Generar más de 20 resultados. | Primera página contiene 20; total/páginas correctos. |
| 8.7 | [ ] Solicitar página de 100 y luego 101. | 100 se admite; 101 se limita a 100. |
| 8.8 | [ ] Revisar acciones Ver/Editar/Seguimiento/Adjuntar/Historial/Cerrar/Eliminar por rol. | Cada bandera coincide con permisos y sensibilidad; el servidor vuelve a comprobarla. |
| 8.9 | [ ] Activar `includeDeleted` sin permisos administrativos en interfaz o payload. | Solo el flujo autorizado puede consultar/restaurar; no expone borrados a roles sin alcance. |
| 8.10 | [ ] En una pregunta `PERSONA`, buscar por nombre, cédula y código, seleccionar un resultado y guardar. | La búsqueda es remota; persiste el `IdPersona` exacto y la instantánea estructurada del nombre, sin aceptar una persona libre. |

## 9. Documentos y Drive

| # | Prueba | Resultado esperado |
|---:|---|---|
| 9.1 | [ ] Cargar JPG/PNG/PDF/DOC/DOCX/XLS/XLSX válidos. | Archivo privado en `TrabajoSocial/<Entidad>/<Id>/Documentos`, metadato en `Documentos` y auditoría. |
| 9.2 | [ ] Cargar extensión no permitida. | `FILE_EXTENSION_NOT_ALLOWED`; no crea archivo ni fila. |
| 9.3 | [ ] Declarar MIME permitido que no coincide. | `FILE_MIME_NOT_ALLOWED` o `FILE_SIGNATURE_MISMATCH`. |
| 9.4 | [ ] Renombrar un ejecutable como PDF. | Firma rechazada; no queda huérfano en Drive. |
| 9.5 | [ ] Cargar archivo vacío o base64 corrupto. | Error amigable; no crea metadato. |
| 9.6 | [ ] Cargar archivo mayor a 10 MiB. | `FILE_TOO_LARGE`. |
| 9.7 | [ ] Superar 10 archivos vigentes en un registro. | `TOO_MANY_FILES`, incluso con dos sesiones concurrentes. |
| 9.8 | [ ] Listar documentos. | No devuelve `DriveFileId` ni URL directa. |
| 9.9 | [ ] Abrir/descargar documento autorizado. | Entrega enlace sujeto a Drive y audita `DOWNLOAD_FILE`. |
| 9.10 | [ ] Abrir documento sensible sin permiso. | Acceso denegado antes de entregar enlace. |
| 9.11 | [ ] Revocar permiso de Drive y volver a abrir. | La app puede autorizar, pero Drive niega el recurso; se muestra explicación sin hacerlo público. |
| 9.12 | [ ] Forzar fallo de metadatos después de crear el archivo en QA. | Archivo recién creado se mueve a papelera como compensación. |

## 10. Soft delete, restauración e historial

| # | Prueba | Resultado esperado |
|---:|---|---|
| 10.1 | [ ] Eliminar sin motivo. | `DELETE_REASON_REQUIRED`; registro sigue activo. |
| 10.2 | [ ] Eliminar con rol autorizado y motivo. | `Activo = FALSE`, `Eliminado = TRUE`, fecha/usuario/motivo y auditoría `DELETE`. |
| 10.3 | [ ] Buscar normalmente tras eliminar. | Registro no aparece. |
| 10.4 | [ ] Restaurar con permiso de eliminar. | Registro vuelve a estar activo y genera `RESTORE`. |
| 10.5 | [ ] Consultar historial. | Orden descendente, usuario/fecha/campo/antes/después/motivo y `CorrelationId`. |
| 10.6 | [ ] Revisar actualización sensible. | Auditoría contiene marcador, no contenido sensible. |
| 10.7 | [ ] Invocar eliminación definitiva con `allowHardDelete = false`. | `HARD_DELETE_DISABLED`; la fila y auditoría permanecen. |
| 10.7a | [ ] Habilitarla en QA e intentar sobre registro activo, sin motivo o con confirmación distinta de `BORRAR:<id>`. | Rechazo por prerrequisito/validación; no elimina. |
| 10.7b | [ ] Intentar como no Administrador o sin permiso de eliminar/sensible. | `FORBIDDEN`/`SENSITIVE_FORBIDDEN`; no elimina. |
| 10.7c | [ ] Intentar sobre fila ya eliminada que tiene hijo o documento relacionado. | `RECORD_HAS_DEPENDENCIES`; no hace cascada ni toca Drive. |
| 10.7d | [ ] Eliminar definitivamente en QA una fila huérfana con soft delete, motivo y confirmación exacta. | Retira solo esa fila; conserva el evento de Auditoría y devuelve `permanentlyDeleted = true`. |
| 10.8 | [ ] Desactivar catálogo ya usado. | Valor histórico permanece y deja de ofrecerse en nuevas capturas; no se borra físicamente. |

## 11. Importación histórica

| # | Prueba | Resultado esperado |
|---:|---|---|
| 11.1 | [ ] Validar hoja correcta sin ejecutar. | Preview hasta 10 filas, conteos y cero mutaciones. |
| 11.1a | [ ] Intentar importar por ID una hoja fuera de staging o un archivo no nativo. | `IMPORT_SOURCE_OUTSIDE_STAGING` o `IMPORT_SOURCE_TYPE`; no lee ni escribe datos. |
| 11.2 | [ ] Encabezado desconocido o mínimo ausente. | Informe en fila 1; `valid = false`. |
| 11.3 | [ ] UUID repetido en destino o lote. | Error por fila; no ejecuta el lote. |
| 11.4 | [ ] Caso con `CodigoCaso` repetido. | Error; no mezcla los registros. |
| 11.5 | [ ] ID faltante. | Genera UUID y lo muestra en preview. |
| 11.6 | [ ] Referencia sensible/relacional inválida. | Rechaza la fila conforme al alcance de validación; no importa detalle sensible huérfano. |
| 11.7 | [ ] Una fila inválida entre filas válidas. | La validación falla y `execute` no guarda ninguna fila; error no es silencioso. |
| 11.8 | [ ] Ejecutar lote completamente válido. | Filas importadas, metadatos de origen, `Importaciones.COMPLETADA` y auditoría `IMPORT`. |
| 11.9 | [ ] Cargar más de 5.000 filas. | `IMPORT_TOO_LARGE`; dividir en lotes no superpuestos. |
| 11.10 | [ ] Forzar fallo de infraestructura durante ejecución. | Trabajo queda `ERROR` si puede actualizarse; reconciliar conteos porque Sheets no tiene rollback multihoja. |
| 11.11 | [ ] Consultar estado con otro usuario no administrador. | Solo ve sus propias importaciones; administrador puede ver todas. |

## 12. Exportación y Power BI

| # | Prueba | Resultado esperado |
|---:|---|---|
| 12.1 | [ ] Exportar filtros a CSV con permiso. | BOM UTF-8, encabezados, mismos filtros y máximo 5.000 filas; indica `truncated`. |
| 12.2 | [ ] Exportar a Google Sheets. | Libro en `Exportaciones`, formato básico, URL privada y visor agregado cuando está configurado. |
| 12.3 | [ ] Exportar sin `PuedeExportar`. | `FORBIDDEN`; no crea archivo. |
| 12.4 | [ ] Exportar texto que comienza `=`, `+`, `-` o `@`. | Se neutraliza como texto; no ejecuta fórmula al abrir. |
| 12.5 | [ ] Revisar columnas de exportación. | No incluye `_rowNumber`, `DriveFileId`, URL, trazabilidad de fuente ni motivo de eliminación. |
| 12.6 | [ ] Cargar hojas normalizadas en Power BI QA. | IDs como texto, fechas/booleanos tipados, relaciones 1:N sin ambigüedad. |
| 12.7 | [ ] Aplicar filtro `Activo/Eliminado`. | Conteos coinciden con dashboard y búsqueda para el mismo corte. |
| 12.8 | [ ] Validar dataset gerencial. | Excluye `DetalleCasosSensibles`, seguridad, auditoría y campos no autorizados. |

## 13. Errores, concurrencia y resiliencia

| # | Prueba | Resultado esperado |
|---:|---|---|
| 13.1 | [ ] Provocar validación, permiso, not found y fallo técnico controlado. | Mensajes amigables; no stack trace al usuario; cada respuesta tiene `correlationId`. |
| 13.2 | [ ] Ejecutar 10–20 creaciones simultáneas con distintas cuentas. | UUID únicos, filas completas, auditoría correspondiente; sin corrupción. |
| 13.3 | [ ] Mantener un bloqueo >30 s en QA e intentar guardar. | `LOCK_TIMEOUT`; el usuario puede reintentar sin fila parcial. |
| 13.4 | [ ] Leer, escribir y leer de nuevo una tabla cacheada. | La segunda lectura refleja la escritura; la versión invalida la clave anterior. |
| 13.5 | [ ] Simular evicción/fallo de CacheService. | La operación obtiene datos desde Sheets y sigue funcionando. |
| 13.6 | [ ] Reenviar una solicitud tras timeout del navegador. | La clave cliente evita duplicar respuestas; para otras entidades se revisa el resultado antes de reintentar. |
| 13.7 | [ ] Revisar logs tras errores con PII/archivo. | No aparece base64, contenido sensible completo ni stack trace en la UI. |

## 14. Seguridad negativa

| # | Prueba | Resultado esperado |
|---:|---|---|
| 14.1 | [ ] Ingresar `<script>alert(1)</script>` en campos mostrados en tabla/tarjeta. | Se presenta como texto; no ejecuta script. |
| 14.2 | [ ] Ingresar HTML con atributo `onerror`. | No se interpreta como HTML. |
| 14.3 | [ ] Manipular nombre de tabla/módulo en RPC. | `INVALID_TABLE`, `INVALID_ENTITY` o `FORBIDDEN`; no accede a otra hoja. |
| 14.4 | [ ] Buscar IDs de Spreadsheet/Drive en HTML, bootstrap y Network. | No están presentes. |
| 14.5 | [ ] Revisar archivo y carpeta con enlace anónimo. | Acceso denegado. |
| 14.6 | [ ] Revocar rol en aplicación pero conservar enlace previo de Drive. | Registrar el comportamiento de ACL; ejecutar proceso de revocación de Drive. |
| 14.7 | [ ] Modificar `expectedVersion`, metadatos de creación o ID desde cliente. | ID no cambia; conflicto/whitelist impiden sobrescritura indebida. |
| 14.8 | [ ] Abrir URL como cuenta externa al dominio. | Google bloquea antes de cargar la aplicación. |
| 14.9 | [ ] Revisar scopes del consentimiento. | Solo Sheets, Drive y correo; no aparece `external_request` ni otros scopes innecesarios. |

## 15. UX, responsive y accesibilidad

| # | Prueba | Resultado esperado |
|---:|---|---|
| 15.1 | [ ] Escritorio ≥1280 px. | Sidebar, dashboard, tablas y formularios sin solapamiento. |
| 15.2 | [ ] Tablet 768–1024 px. | Navegación compacta, tarjetas legibles y controles táctiles. |
| 15.3 | [ ] Móvil 320–430 px. | Una columna, menú colapsable, acciones accesibles y tabla adaptada/desplazable. |
| 15.4 | [ ] Navegar solo con teclado. | Foco visible, orden lógico, menús/botones activables y modal cerrable. |
| 15.5 | [ ] Lector de pantalla básico. | Etiquetas asociadas, regiones/títulos, estados y mensajes anunciables. |
| 15.6 | [ ] Aumentar zoom a 200 %. | Contenido y acciones principales permanecen utilizables. |
| 15.7 | [ ] Simular red lenta/fallo RPC. | Indicador de carga, no doble envío, control se libera y mensaje accionable. |
| 15.8 | [ ] Confirmar eliminación. | Solicita confirmación y motivo; cancelar no cambia datos. |

## 16. Rendimiento y cuotas

- [ ] Medir p50/p95 de bootstrap, búsqueda, apertura y guardado con volumen representativo.
- [ ] Confirmar que ninguna prueba normal se acerca a seis minutos por ejecución.
- [ ] Verificar que una búsqueda renderiza solo la página solicitada.
- [ ] Validar importación y exportación de 5.000 filas en QA; documentar duración y memoria.
- [ ] Revisar Apps Script Dashboard por fallos, cuota y ejecuciones concurrentes.
- [ ] Probar al menos dos sesiones escribiendo en entidades distintas y en la misma entidad.
- [ ] Establecer umbral operativo para migración si p95, filas o contención dejan de cumplir el SLA interno.

## Criterio de aprobación

La versión puede promoverse únicamente si:

- no existen defectos abiertos críticos/altos de autorización, sensibilidad, pérdida de datos o exposición documental;
- setup y segundo setup son satisfactorios;
- los flujos obligatorios de atención, caso, edición, búsqueda, seguimiento, derivación, compromiso, cierre, soft delete/restauración y archivos pasan;
- doble envío, concurrencia y conflicto de versión no corrompen datos;
- una cuenta sin permiso no obtiene datos mediante RPC directo;
- el caso sensible queda enmascarado/restringido y sus accesos son auditados;
- los IDs de infraestructura y archivos privados no llegan al cliente antes de autorización;
- el modelo Power BI reconcilia conteos y excluye sensibilidad;
- existe evidencia de QA firmada por responsable funcional y técnico.
