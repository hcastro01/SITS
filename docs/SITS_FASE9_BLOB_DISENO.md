# Fase 9 — Imágenes y adjuntos BLOB: auditoría y diseño técnico

Fecha de auditoría: 16 de septiembre de 2026. Alcance: Bloque 1 exclusivamente; no se modificó código funcional ni migraciones.

## 1. Resultado y estado actual

El supuesto de que SITS aún requiere introducir BLOB no se confirma. La infraestructura única de Documentos ya guarda binario real en SQLite desde la migración `0008_documentos`: `documentos.contenido_comprimido` es `LargeBinary`, por lo que SQLite lo materializa como `BLOB`. El servicio comprime los bytes con `zlib` antes de persistirlos y los descomprime sólo al descargarlos. No usa rutas locales, URL ni base64 para el contenido documental.

La Fase 9 no debe crear un segundo repositorio, una tabla paralela ni una migración `0023` que duplique el contenido. Su trabajo futuro debe endurecer y completar la experiencia del mecanismo existente, especialmente la integración real de preguntas ARCHIVO/FOTOGRAFIA de Formularios y la visualización segura.

Fuentes verificadas: rama `feature/sits-expansion`, HEAD `35407b0 docs: cerrar fase 8 oficina`, Fase 8 cerrada en el roadmap, y `alembic heads` = `0022_beneficios_prestamos_seguros`. El árbol sólo contiene los artefactos no rastreados ajenos enumerados por la solicitud; no hay cambios tracked pendientes.

## 2. Modelo Documentos actual

| Aspecto | Estado verificado |
|---|---|
| Tabla / PK | `documentos` / `id_archivo` (`String`, UUID generado por servicio) |
| Asociación | Referencia polimórfica `tipo_registro` + `id_registro`; validada en `TIPO_REGISTRO_MODELOS`, no FK física |
| Archivo real | `contenido_comprimido: LargeBinary`, `NOT NULL`; bytes zlib, BLOB SQLite |
| Nombre | `nombre_archivo`; es el nombre saneado conservado como metadata. No hay un campo separado de nombre original sin sanear. |
| Tipo y tamaño | `mime_type`, `extension`, `tamano_bytes`, `tamano_comprimido_bytes` |
| Integridad | `sha256`, indexado y deliberadamente no único |
| Otras metadata | `categoria_documento`, `sensibilidad` nullable; metadatos comunes de creación, actualización, baja, versión y fuente/importación |
| Baja / auditoría | `activo`, `eliminado`, fecha/usuario/motivo de baja y `version`; auditoría append-only en `auditoria` |
| Ruta / URL / base64 | No existen campos ni flujo para ellos |

La migración `0008_documentos` creó índices individuales para `tipo_registro`, `id_registro` y `sha256`. El listado serializa metadata y nunca `contenido_comprimido`; el binario sólo sale desde el endpoint de contenido.

## 3. Flujo actual de almacenamiento, upload y descarga

Flujo genérico: `DocumentosPanel` selecciona un único `File` → `frontend/src/api/documentos.ts` arma `FormData` → `POST /api/v1/documentos` recibe `multipart/form-data` con `UploadFile` y lee como máximo `MAX_FILE_BYTES + 1` → `upload_documento()` valida padre, permisos, tamaño, extensión, MIME declarado y firma → comprime, calcula SHA-256, crea Documento y evento `CREATE` en la misma sesión/transacción → `get_db` hace commit o rollback conjunto.

Los wrappers de Riesgos, Producción y Oficina repiten el contrato multipart sólo para forzar y comprobar el contexto antes de delegar al mismo servicio. No hay filesystem de aplicación en este recorrido. Las importaciones XLSX tienen sus propios BLOB de lote; no son la infraestructura documental ni deben fusionarse sin requerimiento explícito.

La descarga es `GET .../{id_archivo}/contenido`: llama a `download_documento()`, vuelve a validar el padre y permisos, registra `DOWNLOAD_FILE`, descomprime y responde `Response` con MIME persistido y `Content-Disposition: attachment` con filename RFC 5987 codificado. No usa `StreamingResponse`, `FileResponse`, URL ni base64. El comportamiento es descarga forzada; no hay preview inline ni headers `Cache-Control` explícitos.

Límites y validaciones actuales: máximo hardcodeado de 10 MiB y máximo de 10 documentos activos por registro; whitelist actual JPG/JPEG, PNG, WEBP, PDF, DOC/DOCX y XLS/XLSX; MIME declarado y extensión permitidos; magic bytes básicos (WEBP verifica RIFF y WEBP). El nombre sustituye controles y caracteres de ruta/problemáticos, elimina `..`, se recorta a 200 caracteres y nunca se usa como ruta. No hay normalización explícita MIME-extensión uno a uno, análisis profundo de contenedor, límite central en Settings/env, ni deduplicación prohibitiva. Los errores levantan `AppError`; si falla cualquier punto no se persiste el documento.

## 4. Frontend y Formularios

`DocumentosPanel.tsx` ya reutiliza input `type=file`, `FormData`, estado de carga/error, recarga de lista, muestra nombre/categoría/tamaño/fecha/autor, enlace de descarga y baja lógica con motivo/versionado. Sólo selecciona un archivo por envío, no hace preview, progreso ni validación previa de tamaño/tipo; su `accept` omite WEBP aunque backend sí lo permite y anuncia también Office/documents que exceden el objetivo inicial restringido.

El constructor permite tipos `ARCHIVO` y `FOTOGRAFIA`; `QuestionEditor` configura `max_files` (1–10) y `DynamicFormRenderer` muestra input de archivo, múltiples y aceptación de imágenes para fotografía. Es una UI incompleta: `DynamicResponsePage.toAnswers()` ignora deliberadamente los `File`, y el backend sólo admite los cinco campos de valor escalares de `RespuestaFormulario`. Por tanto, ninguna pregunta de archivo/fotografía persiste bytes ni un vínculo documental. Además, el preview provisional llama `URL.createObjectURL()` durante render y no lo revoca. Las respuestas existentes conservan texto/número/fecha/booleano/opción, sin JSON BLOB ni campo documental.

## 5. Arquitectura objetivo

Se selecciona **extender el modelo `Documento` existente**. La opción A (añadir contenido al Documento) ya está realizada mediante `contenido_comprimido`; la tabla 1:1 `DocumentoContenido` (B) no ofrece valor con el límite actual y duplicaría transacciones/consultas. La primera versión de Fase 9 debe conservar el BLOB comprimido y sus metadata; no convertirlo a TEXT/base64 ni a ruta.

Formatos iniciales de la experiencia de adjuntos: PDF, JPG/JPEG, PNG y WEBP. DOC, DOCX, XLS y XLSX son formatos ya habilitados por la infraestructura, pero no se amplían ni se presuponen para Formularios: Bloque 2 debe decidir por tipo de pregunta con whitelist explícita. SVG, HTML, ejecutables, scripts y ZIP no se habilitan por defecto.

Metadata que se conserva: nombre saneado (y, si se requiere fidelidad de UI, agregar en migración futura `nombre_original` saneado para presentación, nunca para ruta), MIME, extensión, tamaño original/comprimido, SHA-256, BLOB, creación, categoría, sensibilidad, baja y versión. SHA-256 seguirá siendo diagnóstico/integridad, no `UNIQUE`: el mismo archivo puede adjuntarse legítimamente a entidades distintas. `sensibilidad` actualmente no se asigna por upload; la autorización se deriva del padre sensible y debe continuar así salvo definición posterior.

`MAX_UPLOAD_SIZE` debe trasladarse desde la constante a `Settings`/env centralizado, con default inicial propuesto de **10 MiB** para compatibilidad. El límite de archivos por registro también debe ser configuración explícita si se conserva. El router debe seguir leyendo límite + 1 antes de persistir; para el tamaño propuesto, bytes en memoria y `Response` son aceptables, documentando que una solicitud y la descompresión ocupan memoria. No se diseña streaming prematuro.

## 6. Seguridad, permisos y scope

Defensa prevista: whitelist por tipo de pregunta; correspondencia estricta extensión ↔ MIME permitido; comprobación de firmas para JPEG, PNG, WEBP y PDF; rechazo de vacío, firma inconsistente y MIME de navegador no confiable. La comprobación actual es una firma inicial, no un parser antivirus ni una garantía de archivo inocuo. No se añaden dependencias pesadas en Bloque 1. Las imágenes no se insertarán como HTML/SVG y los nombres se mostrarán como texto React escapado.

Toda descarga/preview debe exigir sesión (401), permiso del módulo padre + `DOCUMENTOS` (403) y revalidación del registro activo antes de leer bytes. Los wrappers ya aportan la barrera contra acceso horizontal: Riesgos exige `Caso.tipo_caso=RIESGOS_TRABAJO`; Producción exige su registro/scope (`PRODUCCION` para Atenciones); Oficina exige `OFICINA` para Atenciones y el tipo exacto para sus entidades; además comparan `tipo_registro` e `id_registro` con la ruta. El endpoint genérico aplica los permisos del padre resuelto. Cualquier endpoint binario futuro debe delegar a estas mismas funciones, nunca resolver sólo por `documento_id`.

Acciones actuales: carga exige `edit` del padre y `DOCUMENTOS:create`; listado/descarga exige `read` de ambos; baja exige `edit` del padre y `DOCUMENTOS:delete`. No existe reemplazo: la política a preservar es crear + baja lógica, sin sobrescribir BLOB. Un documento dado de baja deja de recuperarse porque `get_active()` lo rechaza. La baja conserva el BLOB en DB; no se inventa retención ni purga legal.

La auditoría ya es transaccional y append-only: `CREATE` registra nombre/tipo/registro/tamaño/hash, `DOWNLOAD_FILE` la descarga y `DELETE` la baja. Preview autenticado debe auditarse como `DOWNLOAD_FILE` salvo que se amplíe de forma central y autorizada el catálogo de acciones; no se creará auditoría paralela. Los eventos no incluyen bytes.

Para contenido privado se diseñan respuestas con `Cache-Control: private, no-store`, `Pragma: no-cache` y `X-Content-Type-Options: nosniff`. Descarga mantiene `attachment`; preview exclusivamente para JPG/JPEG/PNG/WEBP y PDF se obtiene autenticadamente como Blob con `fetch(..., credentials: 'include')`, `URL.createObjectURL`, y `URL.revokeObjectURL` al cambiar/cerrar/desmontar. No exponer endpoint directo inline reutilizable por terceros.

## 7. Históricos, migración y SQLite

`Documento` no tiene históricos de sólo metadata admisibles: `contenido_comprimido` es `NOT NULL` desde 0008. No hay ruta/URL histórica que migrar o backfill que inventar. Los campos de procedencia (`archivo_fuente`, etc.) se preservan; si aparecieran registros externos sin BLOB en otra tabla, deben continuar sin contenido y marcarse explícitamente como no migrados, sin intentar leer una ruta inexistente.

No se debe crear `0023` sólo por el objetivo BLOB ya satisfecho. Si Bloque 2 aprueba cambios de esquema realmente necesarios (por ejemplo `nombre_original` o una relación explícita Documento–RespuestaFormulario), la siguiente revisión debe ser aditiva sobre `0022_beneficios_prestamos_seguros`, nullable para compatibilidad, con índices sólo justificables, FK clara si se abandona polimorfismo, y downgrade que retire únicamente lo añadido. Nunca convertir BLOB existente a `NOT NULL` nuevo ni tocar registros históricos. Antes de cierre: SQLite temporal `upgrade → check → downgrade → upgrade`.

SQLite crecerá con BLOB comprimidos y sus backups/restores incluirán los adjuntos atómicamente. Riesgos: más I/O, backups mayores, bloqueo de escritor y espacio no devuelto inmediatamente al bajar documentos. Mitigaciones: límite configurable, observación de tamaño/backup y restauración, WAL ya configurado, evitar seleccionar BLOB en listados y planificar `VACUUM` sólo como operación administrada posterior a purgas autorizadas. No cambia la decisión BLOB en DB.

## 8. Integración futura de Formularios

Bloque 4 debe subir cada `File` mediante el servicio común antes de registrar la respuesta, dentro de una misma unidad transaccional. La asociación coherente es **RespuestaFormulario detalle → Documento**: añadir una relación explícita nullable/repetible (tabla puente `respuesta_documentos` es preferible si una pregunta admite varios archivos) que contenga `id_detalle_respuesta` e `id_archivo`, índices y FKs. `Documento.tipo_registro="RESPUESTAS_FORMULARIO"` seguirá apuntando a `EnvioFormulario` para la autorización existente; el puente atribuye el archivo a la pregunta concreta sin guardar binario ni URL en JSON/`valor_*`.

Para evitar huérfanos: validar antes de crear, crear Envio/Detalle/Documento/puente en la misma sesión y dejar que cualquier error haga rollback total. Cancelar cliente antes de enviar no persiste; exceder tamaño, tipo/MIME inválido o fallo de contenido no genera metadata independiente. El número real de adjuntos se valida contra `max_files` de la pregunta y los límites centrales. La cardinalidad actual de Documentos permite múltiples por entidad (hasta 10); la tabla puente preserva múltiples por pregunta sin imponer cardinalidad nueva a respuestas previas.

## 9. Matriz de pruebas futura

Bloque 2 backend: PDF/JPG/PNG/WEBP válidos; bytes idénticos tras descompresión/descarga; metadata, MIME, filename y tamaño; límite; tipo, extensión y firma inconsistentes; 401, 403, padre/scope incorrecto, inexistente y baja; listado sin BLOB; hash repetido permitido; rollback y auditoría. Incluir regresiones de Riesgos, Producción, Oficina, genérico y Documentos existentes.

Bloque 3 frontend: selección multipart, validación previa informativa, loading/error, lista metadata, descarga, preview de imagen, PDF mediante Blob, cierre/revocación de object URL, baja, permisos, vacío/error y WEBP. Bloque 4: uno/múltiples adjuntos de preguntas ARCHIVO/FOTOGRAFIA, máximo por pregunta, vínculo al detalle correcto, rollback y respuestas históricas sin vínculo.

## 10. Mapa de reutilización

| Funcionalidad | Archivo/modelo/servicio | Estado actual | Acción | Cambio necesario |
|---|---|---|---|---|
| Modelo Documentos | `models/documentos.py`, 0008 | BLOB comprimido real | REUTILIZAR | Ninguno para BLOB; evaluar metadata sólo si se justifica |
| Schemas/serialización | routers `_serialize` | Metadata separada de bytes | MODIFICAR | Contrato metadata explícito y sin BLOB |
| Servicio | `services/documentos.py` | Validación, hash, compresión, permisos | MODIFICAR | Config central, MIME-extensión estricta y firmas focales |
| Router | `api/documentos.py` | Multipart/Response seguro básico | MODIFICAR | Cache headers y opción de contenido autenticado para preview |
| Permisos | `core/permissions.py`, seed | Padre AND DOCUMENTOS | REUTILIZAR | Conservar en toda ruta nueva |
| Auditoría | `services/audit.py` | CREATE/DOWNLOAD_FILE/DELETE transaccional | REUTILIZAR | Reusar DOWNLOAD_FILE para preview |
| Panel | `DocumentosPanel.tsx` | Carga, lista, descarga, baja | MODIFICAR | WEBP, validación UI y preview seguro |
| API frontend | `api/documentos.ts` | FormData y URL de descarga | MODIFICAR | Fetch Blob autenticado para preview |
| Formularios | `DynamicFormRenderer`, `QuestionEditor` | Inputs ARCHIVO/FOTOGRAFIA UI | MODIFICAR | No crear object URL en render; carga real |
| Respuestas | `dynamic_responses.py`, `RespuestaFormulario` | Sólo valores escalares; ignora File | MODIFICAR | Puente detalle-documento transaccional |
| Preguntas archivo/imagen | Builder y tipos permitidos | Tipos ya configurables | REUTILIZAR | Whitelist y cardinalidad aplicadas al upload |
| Producción | `services/produccion.py` | Wrapper y anti-IDOR | REUTILIZAR | Regresión solamente |
| Oficina | `services/oficina.py` | Wrapper/scope OFICINA | REUTILIZAR | Regresión solamente |
| Riesgos | `services/riesgos_trabajo.py` | Wrapper/tipo de caso | REUTILIZAR | Regresión solamente |

## 11. Bloques de implementación

1. **Bloque 1 — Auditoría y diseño:** este documento y roadmap.
2. **Bloque 2 — Backend / endurecimiento BLOB:** no crear BLOB paralelo; endurecer/configurar infraestructura existente y cubrir pruebas backend.
3. **Bloque 3 — Frontend carga/descarga/preview:** panel y cliente Blob autenticado.
4. **Bloque 4 — Formularios y módulos contextuales:** relación de adjuntos a respuesta, carga transaccional y regresión contextual.
5. **Bloque 5 — Regresión, migración y cierre:** sólo si Bloques 2–4 justificaron una migración; ciclo SQLite y suites completas.

## 12. Riesgos reales pendientes

- La finalidad BLOB ya existe, por lo que una implementación literal de una segunda tabla/columna sería regresiva y contraria a la reutilización.
- El backend ya centraliza límite/formato y el panel documental ofrece preview Blob autenticado; las preguntas ARCHIVO/FOTOGRAFIA de Formularios siguen fuera de este bloque y su preview provisional aún requiere tratamiento separado.
- ARCHIVO/FOTOGRAFIA aún no persisten archivos: el UI permite seleccionarlos, pero la serialización los omite.
- Las respuestas binario se cargan completas en memoria y no definen headers privados de cache; deben mantenerse límites y no incluir BLOB en listados.

## 13. Decisiones implementadas — Bloque 2

- No se alteró el esquema: `contenido_comprimido` ya es BLOB real y la metadata existente (`nombre_archivo` saneado, MIME, extensión, tamaños y SHA-256 no único) cubre el flujo. No se agregó `nombre_original` sin sanear, porque no puede ser ruta ni fuente de confianza; `nombre_archivo` conserva la metadata segura de presentación.
- `Settings.max_upload_bytes` y `Settings.max_documents_per_record` centralizan los valores compatibles de 10 MiB y 10. Los routers continúan leyendo límite + 1 antes de delegar, por lo que los rechazos no dejan Documento ni auditoría persistidos.
- La whitelist efectiva de Documentos queda en PDF, JPEG, PNG y WEBP. La validación exige extensión, MIME exacto asociado y magic bytes; SVG, HTML, JS, ejecutables, Office y demás formatos no se aceptan en este flujo inicial.
- Todas las rutas de contenido existentes siguen siendo `attachment`; el preview autenticado inline queda expresamente para Bloque 3. Se aplicaron cabeceras privadas uniformes (`private, no-store`, `Pragma: no-cache`, `nosniff` y filename RFC 5987) a genérico, Riesgos, Producción y Oficina.
- La descarga transforma BLOB inválido o ausente en un `AppError` controlado, conserva baja lógica y auditoría `DOWNLOAD_FILE` sólo tras recuperar bytes válidos. Los controles de padre, permisos y scope de wrappers no cambiaron.

## 14. Decisiones implementadas — Bloque 3

- El cliente HTTP existente incorpora una única lectura autenticada `getForBlob`: mantiene cookies, transforma errores HTTP en `HttpError` y extrae el filename RFC 5987 de `Content-Disposition`. No se creó cliente paralelo ni se cargaron BLOB en los listados.
- `DocumentosPanel` reutiliza esa lectura en las rutas genérica, Riesgos, Producción y Oficina. La descarga crea un enlace temporal desde Blob y revoca la URL inmediatamente después de dispararla.
- PDF, JPEG, PNG y WEBP se previsualizan exclusivamente tras fetch autenticado, en un `Modal` con Blob URL. La URL se revoca al cierre, al reemplazar un preview y al desmontar el componente. No se inserta endpoint protegido directamente en `img` o `iframe`.
- La validación de UI es informativa y centralizada: extensión/MIME declarado, 10 MiB y máximo 10 documentos. El backend mantiene toda validación de seguridad y autorización.
- Formularios no se modificó. Bloque 4 sigue siendo responsable de adjuntos por pregunta, vínculo transaccional con respuestas y tratamiento de sus object URLs.

## 15. Decisiones implementadas — Bloque 4

- `respuesta_documentos` vincula repetiblemente `RespuestaFormulario` con `Documento`; no duplica BLOB, hash, compresión ni metadata. Los históricos sin filas en el puente permanecen sin asociación inferida.
- El contrato multipart usa un campo `payload` JSON para valores escalares y partes repetibles `archivo:<id_pregunta>`. El backend valida que cada parte pertenezca a una pregunta `ARCHIVO` o `FOTOGRAFIA`, aplica el límite de la pregunta sin ampliar el límite central y restringe fotografía a JPEG/PNG/WEBP.
- La carga se integra en `save_dynamic_response`: respuesta, detalle, `Documento` y puente comparten la transacción de la petición. Los documentos se vinculan al envío mediante `RESPUESTAS_FORMULARIO` y al detalle de pregunta mediante el puente.
- Evidencia parcial de Bloque 4 (2026-09-16): la prueba dedicada fuerza un adjunto válido seguido de uno con firma inválida, tanto en una pregunta como entre dos preguntas; tras el rollback compara los conteos de `envios_formulario`, `respuestas_formulario`, `respuesta_documentos` y `documentos` y conserva los valores previos. También verifica que la serialización histórica no infiere adjuntos y que una edición directa de respuesta registrada con vínculo es rechazada por servidor. La prueba frontend comprueba el campo `payload`, partes repetidas `archivo:<id_pregunta>` y revocación de URLs locales/persistidas. Esta evidencia no sustituye las suites finales ni autoriza cierre.
- Cierre de validación (2026-09-16): la prueba de adjuntos pasó `10/10`, incluida autorización del usuario sin permiso (`FORBIDDEN`) y scope de respuesta/documento: una respuesta/contexto distinto, documento sin puente o dado de baja no permite descarga. El rollback confirmó los conteos previos y posteriores de las cuatro tablas sin filas huérfanas. Backend completo: `283/283` en 39 archivos, exit `0`; frontend completo por grupos aislados: `136/136` en 22 archivos, exit `0`. El modo global serial no daba un resumen dentro del intervalo de captura por el arranque aislado de un worker por archivo; los grupos conservaron aislamiento y demostraron que no había handles abiertos. `--no-isolate` se descartó por contaminación entre archivos. Alembic temporal, typecheck, Vite build y `git diff --check` aprobaron.

## 16. Cierre formal — Bloque 5

El cierre no añadió funcionalidad. En una SQLite temporal limpia, `0023_respuesta_documentos` completó `upgrade → check → downgrade a 0022 → upgrade → check`; ambos checks aprobaron y la revisión final fue `0023_respuesta_documentos`. La inspección SQLite confirmó la tabla puente, sus FKs hacia detalle de respuesta y Documento, su unicidad `(id_detalle_respuesta, id_archivo)` y sus dos índices explícitos.

La regresión final aprobó backend `283/283` (98.536 s, exit 0), frontend aislado `136/136` en 22 archivos (exit 0), `tsc -b`, Vite build y `git diff --check`. Las pruebas existentes cubren la cadena Formulario → multipart → Envío/Detalle → puente → Documento BLOB → metadata → descarga/preview autenticados, incluyendo permisos, vínculo exacto, baja lógica, históricos sin vínculo y ausencia de BLOB en listados. No se creó almacenamiento paralelo, base64 ni campos binarios de Formularios.

Deuda conocida, no bloqueante: SQLite con BLOB aumenta I/O/backups y tiene concurrencia limitada; la baja lógica no libera espacio inmediatamente; upload/download usan memoria dentro de los límites; no hay antivirus ni análisis profundo; los históricos sin relación explícita no se clasifican; y la edición de respuestas con adjuntos permanece bloqueada para mantener la atomicidad.
