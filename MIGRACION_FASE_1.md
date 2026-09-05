# Fase 1 — Análisis y arquitectura propuesta

Estado: propuesta para revisión. No se ha generado ni modificado código de aplicación.
Fecha: 5 de septiembre de 2026. Stack solicitado: React, FastAPI, SQLite, Docker local; Vercel y PythonAnywhere como destinos.

## 1. Alcance y evidencia

El repositorio contiene una aplicación de gestión de Trabajo Social: personas, atenciones, expedientes, novedades, recorridos y sus hallazgos, seguimientos, derivaciones, compromisos, cierres, formularios configurables, documentos, consultas, reportes y administración.

Fuentes principales: `Code.gs` (contratos públicos), `Config.gs` (24 esquemas y configuración), `AuthService.gs` y `Setup.gs` (autorización y permisos iniciales), servicios de dominio, HTML de vistas y `Scripts.html`. La documentación existente es apoyo; cuando difiere del código se señala abajo.

No hay una copia de las filas productivas de Sheets ni de Script Properties en los archivos revisados. Por ello no se conocen los usuarios efectivos, permisos modificados, valores runtime, volumen de registros ni tamaño documental. Los valores del código son defaults, no evidencia de la configuración desplegada.

No se encontraron definiciones o creación de triggers ni uso de GmailApp o CalendarApp. Sí existen cargas manuales de parámetros y opciones. Los triggers instalados desde la consola de Apps Script no se pueden descartar inspeccionando solo estos archivos.

El manifiesto usa `USER_DEPLOYING`, acceso `DOMAIN` y scopes de Sheets, Drive e identidad por correo. Google proporciona identidad y protección de dominio; la aplicación añade su propia lista de usuarios y permisos.

## 2. Mapeo funcional

| Actual | Destino |
|---|---|
| Index/App/Styles/Components + Scripts | Shell React, navegación, componentes compartidos y cliente HTTP |
| Dashboard + SearchService.dashboard | Página de indicadores + servicio de agregación |
| DynamicForm + FormService | Motor React de preguntas; validación autoritativa en FastAPI |
| FormBuilder + FormService | Constructor, opciones, reglas, orden, duplicación, publicación y preview |
| CaseView + CaseService | Expediente con detalle, subprocesos, documentos e historial |
| ProcessService | Servicios explícitos de personas, atenciones, novedades, recorridos y hallazgos |
| SearchView + SearchService | Búsqueda filtrada y paginada con proyección según permisos |
| AdminView + Auth/Catalog/Config | Usuarios, roles, matriz de permisos, catálogos y configuración |
| DriveService | Servicio documental privado; metadatos en SQLite, binarios en almacenamiento privado propuesto |
| ImportService | Preview, validación y ejecución de importaciones CSV/XLSX; lote y errores trazables |
| ExportService | CSV y propuesta de XLSX descargable en sustitución de crear un Google Sheet |
| DataService + LockService | SQLAlchemy, restricciones SQL, transacciones y control optimista de versión |
| AuditService + ErrorService | Auditoría transaccional, errores HTTP estructurados y correlationId |
| Setup/CargaParametros/CargaOpcionesFormulario | Comandos administrativos de inicialización y carga idempotente |

La matriz de `CatalogoOpcionesFormulario.gs` contiene 22 preguntas y listas institucionales, extraídas de un XLSX que no está presente en el inventario. Se preservarán sus etiquetas, opciones, orden y configuración. Incluye campos que no tienen columna directa en Casos, como sexo, fin de restricción y reporte a Riesgo de Trabajo: permanecerán como respuestas tipadas. No se inventará una correspondencia por etiqueta sin documentarla y validarla.

Flujos que deben conservarse:

1. Los usuarios solo pueden crearse desde la administración de la misma aplicación, por un usuario con los permisos administrativos vigentes, asignándoles los roles y accesos actuales. No existe autorregistro ni creación automática al iniciar sesión con Google. Para acceder se exige usuario registrado, estado activo, rol vigente y permiso por acción. Google se mantiene como mecanismo de identificación propuesto, sujeto a confirmar las cuentas admitidas.
2. Administrador configura catálogos/formularios; publicación habilita captura.
3. Captura valida opciones, referencias, dependencias, obligatoriedad y cálculos; guarda borrador o respuesta registrada con identificador de envío.
4. Expediente admite seguimiento, derivación, compromiso y cierre; las actualizaciones del padre y la auditoría son una sola transacción.
5. Documentos se cargan y consultan desde su registro, verificando permisos y sensibilidad.
6. Búsquedas y exportaciones aplican la misma política de acceso; eliminación lógica con motivo, restauración e historial.

## 3. Arquitectura

React con TypeScript y Vite → API `/api/v1` en FastAPI → servicios → repositorios SQLAlchemy → SQLite.

FastAPI encaja con la preferencia expresada y permite contratos Pydantic, validación y OpenAPI. Se propone SQLAlchemy con sesiones síncronas por petición y rutas adecuadas para operaciones bloqueantes; no hace falta añadir complejidad asíncrona a SQLite. Alembic administrará cambios de esquema. Las versiones concretas se fijarán en la fase 2.

El frontend tendrá estado de sesión/permisos y consultas remotas separadas del estado de formularios. El servidor decidirá siempre la autorización. Los cálculos configurables conservarán operaciones acotadas como SUM, CONCAT y TODAY; nunca eval de código recibido.

Configuración sensible/de infraestructura por entorno: ruta absoluta SQLite, directorio privado de archivos, credenciales OAuth, orígenes permitidos, modo de ejecución y política de dominio. Configuración funcional editable en `configuracion`, con whitelist y auditoría. React solo recibe parámetros públicos.

Defaults a conservar salvo configuración productiva distinta: es_EC, America/Guayaquil, páginas 20/100, importación y exportación 5.000 filas, 10 MiB/archivo, 10 archivos/registro, borrado definitivo deshabilitado e identidad de prueba deshabilitada. Los antiguos IDs de Drive/Sheets serán referencias de migración, no configuración necesaria del sistema nuevo.

### Autenticación propuesta

Google OpenID Connect, validado por el backend: firma, emisor, audiencia, expiración, nonce, correo verificado y `hd` cuando se exija Workspace. Asociar la identidad estable `sub` a un usuario previamente autorizado; no crear usuarios automáticamente al iniciar sesión. El dominio permitido aún requiere confirmación.

Corrección confirmada por el usuario: las altas se realizan exclusivamente desde la aplicación, con los roles y accesos vigentes. La API de administración comprobará ADMINISTRACION:edit, conforme a saveUserRole del sistema actual; ocultar el formulario no sustituye ese control. No habrá alta pública ni aprovisionamiento de usuarios mediante OAuth. La migración conservará las cuentas existentes, incluido el administrador inicial; si no se dispone de esas cuentas, deberá definirse el arranque inicial antes de implementar, sin crear un administrador implícito.

La sesión propia será revocable y los cambios de rol/bloqueo se comprobarán en cada petición. Se propone cookie HttpOnly y Secure, protección CSRF en operaciones mutables y expiración. Para evitar depender de cookies de terceros entre vercel.app y pythonanywhere.com, se decidirá entre dominios propios bajo un mismo dominio o proxy del frontend según límites de alojamiento y carga de archivos. Esta decisión debe cerrarse antes del login del frontend. No se guardarán credenciales en localStorage.

Referencia de validación de identidad: https://developers.google.com/identity/openid-connect/openid-connect

## 4. Esquema SQLite propuesto

Contrato de conservación: todas las columnas de negocio de `TSConfig.schemas` se trasladan, excepto las sustituciones explícitas siguientes. Los nombres SQL usarán snake_case y el importador tendrá mapeos explícitos a los encabezados legacy. No se usarán conversiones automáticas ambiguas para asignar tipos o relaciones.

Tipos físicos: identificadores legacy y nuevos en TEXT (hay prefijos, no todos son UUID puros); textos/correos/códigos/cédulas en TEXT; booleanos INTEGER con CHECK 0/1; versiones, orden y contadores INTEGER; ValorNumero REAL para las respuestas numéricas existentes. Fechas civiles TEXT YYYY-MM-DD; horas TEXT HH:MM:SS; instantes TEXT ISO 8601 UTC, presentados en America/Guayaquil. Validaciones/condiciones estructuradas en JSON serializado a TEXT validado. No convertir cédulas/códigos en números ni perder ceros iniciales.

Metadatos comunes conservados: activo, eliminado, fecha_creacion, creado_por, fecha_actualizacion, actualizado_por, fecha_eliminacion, usuario_eliminacion, motivo_eliminacion, version y los cinco campos de procedencia/importación. Auditoría y configuración conservan sus esquemas especiales. Los correos históricos de autor permanecen como instantáneas de texto aunque el usuario deje de existir.

| Tabla destino | Origen / columnas y relaciones principales |
|---|---|
| usuarios | Usuarios: id_usuario PK TEXT, correo TEXT UNIQUE normalizado, nombre, rol_id FK roles, estado, ultimo_acceso; añadir google_sub TEXT UNIQUE nullable |
| roles | Roles: id_rol PK TEXT, nombre, descripcion |
| permisos | Permisos: id_permiso PK, rol_id FK, modulo; seis banderas INTEGER; UNIQUE(rol_id, modulo) |
| personas | Personas: id_persona PK; codigo_empleado, cedula, nombre, cargo, area, departamento, centro, sub_centro, turno, estado_laboral TEXT |
| formularios | Formularios: id_formulario PK, nombre, descripcion, proceso, estado, responsable, fecha_publicacion |
| preguntas | Preguntas: id_pregunta PK, id_formulario FK; etiqueta, descripcion, tipo, categoria, subcategoria, defaults/ayuda; banderas; orden/longitud INTEGER; validacion/condicion; campo_dependiente FK preguntas nullable; formula |
| opciones_pregunta | OpcionesPregunta: id_opcion PK, id_pregunta FK, valor, etiqueta, orden; id_catalogo FK nullable; id_opcion_padre FK propia nullable |
| reglas_formulario | ReglasFormulario: id_regla PK, id_formulario FK, pregunta_origen/destino FK preguntas; operador, comparación, acción, mensaje, orden |
| envios_formulario | Nueva cabecera: id_respuesta PK, id_formulario FK, usuario_respuesta TEXT, id_envio_cliente TEXT, estado, fecha_respuesta, id_registro_proceso nullable; version. UNIQUE(usuario_respuesta, id_envio_cliente) cuando haya clave |
| respuestas_formulario | RespuestasFormulario: id_detalle_respuesta PK, id_respuesta FK cabecera, id_pregunta FK; valor_texto TEXT, valor_numero REAL, valor_fecha TEXT, valor_booleano INTEGER nullable, valor_opcion TEXT; procedencia y versiones históricas |
| atenciones | Atenciones: id_atencion PK, id_persona FK nullable; fecha/hora, colaborador, responsable, tipo, motivo, canal, gestion, resultado, observaciones, evidencias, estado; requiere_seguimiento/genera_caso INTEGER |
| casos | Casos: id_caso PK, codigo_caso TEXT UNIQUE, id_persona FK nullable; fechas, colaborador/responsable, tipo/subtipo, prioridad, nivel_sensibilidad, estado, gestion/evento, area/turno/condición; restriccion/derivacion INTEGER; cierre/resultado/evidencias |
| detalle_casos_sensibles | DetalleCasosSensibles: id_detalle_sensible PK, id_caso FK UNIQUE; descripcion_sensible, antecedentes, diagnostico_social, intervencion, notas_privadas TEXT |
| novedades | Novedades: id_novedad PK; fecha/hora, responsable, fuente, tipo/subtipo, area/turno/lugar, descripcion, impacto/prioridad, accion_inmediata, estado/evidencias; genera_atencion/genera_caso INTEGER |
| recorridos | Recorridos: id_recorrido PK; fecha/horas, responsable, planta/area/turno, objetivo/observaciones, personas_contactadas, novedades_detectadas, acciones/evidencias. Revisar contenido real antes de tipar los dos campos potencialmente cuantitativos |
| hallazgos_recorrido | HallazgosRecorrido: id_hallazgo PK, id_recorrido FK, id_novedad/id_caso FK nullable; tipo/categoria/subcategoria, area, descripcion, prioridad, accion, estado; genera_novedad/genera_caso INTEGER |
| seguimientos | Seguimientos: id_seguimiento PK, id_caso FK; fecha/hora, responsable, tipo, canal, tecnica, descripcion, resultado, proxima_accion, fecha_proxima_accion, estado/evidencias |
| derivaciones | Derivaciones: id_derivacion PK, id_caso FK; fecha, area_destino/responsable_destino, motivo/estado, fecha_respuesta/fecha_cierre, resultado/observaciones |
| compromisos | Compromisos: id_compromiso PK, id_caso FK, id_seguimiento FK nullable; fechas, responsable, descripcion, estado, evidencia/observacion |
| cierres | Cierres: id_cierre PK, id_caso FK; fecha_cierre_caso, responsable, motivo, resultado_final, evidencia/observacion, requiere_monitoreo INTEGER |
| documentos | Documentos: id_archivo PK; tipo_registro/id_registro, nombre, MIME/extensión, tamano_bytes INTEGER, fechas/autor, categoria/sensibilidad; storage_key TEXT UNIQUE y sha256 TEXT; drive_file_id/url solo como procedencia privada durante migración |
| catalogos | Catalogos: id_catalogo PK, tipo/codigo/valor/descripcion, orden INTEGER, id_catalogo_padre FK propia; tipo_padre/codigo_padre históricos, es_sensible INTEGER; UNIQUE(tipo,codigo) |
| auditoria | Auditoria: id_auditoria PK, tabla/id_registro, accion/usuario/fecha_hora, campo/valores redactados, motivo/correlation_id; solo inserción por API |
| configuracion | Configuracion: clave TEXT PK, valor TEXT, descripcion, tipo, editable INTEGER, fecha_actualizacion/actualizado_por |
| importaciones | Importaciones: id_importacion PK; destino/fuente/hoja, total/importadas/error INTEGER, estado, errores JSON validado, fechas y usuario |
| sesiones | Nueva: id_sesion PK, token_hash UNIQUE, id_usuario FK, fecha_creacion, expira_en, revocada_en; nunca almacenar el token en claro |

Respuestas múltiples conservan varias filas por pregunta; no imponer UNIQUE(id_respuesta,id_pregunta). Las filas históricas inactivas se mantienen. La cabecera nueva agrupa IdRespuesta y elimina la repetición de la identidad del envío, sin perder el contenido original del respaldo de migración.

Documentos y enlaces de respuestas a procesos son referencias polimórficas: SQLite no puede imponer una FK hacia varias tablas. Se validarán tipo permitido, existencia, coherencia y permiso dentro del servicio; se bloqueará borrado físico de registros referenciados. No se presentarán estas referencias como FKs reales. Las reglas solo podrán enlazar preguntas del mismo formulario y los compromisos, seguimientos del mismo caso.

Índices: todas las FK; casos(estado_caso, fecha_apertura), casos(responsable), personas(cedula), personas(codigo_empleado), documentos(tipo_registro,id_registro), auditoria(tabla,id_registro,fecha_hora), respuestas_formulario(id_respuesta,activo). No declarar únicos los códigos de persona hasta auditar duplicados reales.

PRAGMA foreign_keys por conexión; transacciones cortas; busy_timeout acotado; versión obligatoria en modificaciones para detectar conflicto con HTTP 409. No habilitar WAL automáticamente en almacenamiento remoto: depende del filesystem del alojamiento. El respaldo usará un procedimiento consistente de SQLite, no copiar una base abierta arbitrariamente.

## 5. Contrato REST propuesto

Prefijo `/api/v1`. Listados paginados; creación 201; lecturas/modificaciones 200; errores 401/403/404/409/422 y 500 sanitizado. Mantener code, message y correlationId. Datos de entrada validados y campos internos excluidos de los esquemas públicos. PATCH acepta expected_version y motivo cuando corresponda.

| Métodos y rutas | RPC/función equivalente y permiso |
|---|---|
| GET /auth/google/start; GET /auth/google/callback; POST /auth/logout; GET /auth/me | Sustituyen identidad Session; login no da de alta usuarios |
| GET /bootstrap | getBootstrapData; usuario vigente, configuración pública y permisos |
| GET /dashboard | getDashboardData; DASHBOARD:read |
| GET /formularios/publicados; GET /formularios/{id}/definicion | getPublishedForms/getFormDefinition; FORMULARIOS:read |
| GET /admin/formularios; GET /admin/formularios/{id} | listForms/getFormAdmin; FORMULARIOS:edit |
| POST /formularios; PATCH /formularios/{id} | saveFormDefinition; create/edit |
| POST /formularios/{id}/preguntas; PATCH /preguntas/{id} | saveQuestion, incluyendo opciones; permiso constructor |
| POST /preguntas/{id}/duplicaciones; PATCH /preguntas/{id}/estado | duplicateQuestion/deactivateQuestion |
| PUT /formularios/{id}/orden-preguntas; PATCH /formularios/{id}/estado | reorderQuestions/changeFormStatus |
| POST /formularios/{id}/respuestas; PATCH /respuestas/{id} | saveFormResponse/saveDraft; estado BORRADOR o REGISTRADO, clave idempotente y reglas de propietario |
| GET /respuestas/{id} | Lectura autorizada para retomar borrador; validar propietario/permisos y sensibilidad |
| GET, POST /personas, /atenciones, /casos, /novedades, /recorridos, /hallazgos, /seguimientos, /derivaciones, /compromisos, /cierres | Listado y creación por módulo; hijos delegan siempre al servicio de casos/recorridos |
| GET, PATCH /{recurso}/{id} | getRecord/saveRecord; recurso de whitelist y esquema específico |
| POST /{recurso}/{id}/eliminacion; POST /{recurso}/{id}/restauracion | softDeleteRecord/restoreRecord; delete + motivo y versión |
| DELETE /{recurso}/{id}/permanente | hardDeleteRecord; flag, ADMINISTRACION:edit, delete, sensibilidad, motivo/confirmación y cero dependencias |
| GET /{recurso}/{id}/historial | getRecordHistory; lectura del registro y controles de sensibilidad |
| GET, PATCH /casos/{id}/detalle-sensible | Lectura/edición protegida; CASOS:read/edit + sensitive |
| POST /casos/{id}/seguimientos, /derivaciones, /compromisos, /cierres | saveFollowUp/saveReferral/saveCommitment/closeCase; permiso del hijo y edición del padre |
| GET /busqueda | searchRecords; BUSQUEDA:read + permisos por entidad |
| GET, POST /catalogos; PATCH /catalogos/{id}; PATCH /catalogos/{id}/estado; GET /catalogos/dependientes | list/save/toggle/dependent, permisos CATALOGOS |
| GET, POST /{recurso}/{id}/documentos; GET /documentos/{id}/contenido | listRecordFiles/uploadFiles/getFileAccess; permisos documento + padre; multipart para carga |
| POST /exportaciones | exportSearchResults; REPORTES:export y política de búsqueda; formato CSV/XLSX propuesto |
| POST /importaciones/validaciones; POST /importaciones; GET /importaciones; GET /importaciones/{id} | validateImport/executeImport/getImportStatus; IMPORTACION y permiso de entidad; revalidar al ejecutar |
| GET /admin/usuarios; POST /admin/usuarios; PATCH /admin/usuarios/{id}; GET /admin/roles | listUsersRolesPermissions/saveUserRole; ADMINISTRACION |
| GET /admin/permisos; PUT /admin/roles/{id}/permisos/{modulo} | savePermissions; ADMINISTRACION:edit |
| GET, PATCH /admin/configuracion | saveApplicationConfig; valores funcionales permitidos |

No exponer runSetup como endpoint público. Inicializar por comando administrativo fuera de la API. Las rutas genéricas son abreviatura documental: no permiten seleccionar una tabla arbitraria ni saltar servicios especializados. La gestión de reglas se mantiene dentro del contrato de definición del formulario, con validación y auditoría.

## 6. Seguridad a conservar y diferencias por resolver

Conservar cinco IDs de rol, 18 módulos y seis acciones. Importar la matriz efectiva de producción, no sustituirla por los seeds. Proteger al último administrador y los permisos mínimos de administración. Revocar sesiones al bloquear usuarios; rechazar roles/permisos inactivos.

Conservar soft delete, motivo, trazabilidad, versiones, redacción de auditoría, protección de exportaciones frente a fórmulas, límites documentales, validación de contenido y denegación de acceso a archivos por URL pública. El archivo se servirá mediante API autorizada; las rutas físicas no se exponen. La firma binaria actual es una comprobación de formato y no equivale a análisis antivirus.

Hallazgos que impiden prometer una copia literal segura:

- SearchService usa un OR entre permiso sensible del módulo y CASOS; la lectura individual/documental aplica controles distintos. Propuesta: política central coherente; para hijos de casos sensibles exigir permisos sobre hijo y caso.
- El enmascaramiento usa una lista fija de campos. Propuesta: esquemas de salida explícitos, filtrado de preguntas sensibles y aplicación de la misma política a búsqueda, exportación, adjuntos e historial.
- Gerencia puede leer varios registros según Setup, aunque la documentación resume su función como agregada. Se conservará la matriz real; restringirla solo a indicadores sería un cambio de negocio que requiere aprobación.
- expectedVersion es opcional en la implementación actual. Propuesta: hacerlo obligatorio al modificar para que la concurrencia esté realmente protegida.
- La idempotencia de respuestas consulta una clave global antes de comprobar propietario. Propuesta: clave asociada al usuario y control de acceso antes de devolver una respuesta existente.

No se ha ejecutado la app en Google ni realizado una auditoría de seguridad exhaustiva. Estos son hallazgos de revisión estática y decisiones propuestas para la migración.

## 7. Estructura de carpetas

```text
backend/
  app/
    main.py
    api/v1/                 # rutas explícitas por módulo
    core/                   # configuración, identidad, permisos, errores
    schemas/                # entradas y salidas Pydantic
    models/                 # entidades SQLAlchemy
    services/               # casos, formularios, búsqueda, auditoría...
    repositories/           # consultas y persistencia
    db/                     # engine, sesiones y transacciones
    storage/                # adaptador documental privado
    cli/                    # inicialización y migración legacy
  migrations/               # Alembic
  tests/                    # permisos, dominio, migración y concurrencia
  pyproject.toml
  .env.example
  Dockerfile
  .dockerignore
frontend/
  src/
    app/                    # router y proveedores
    features/               # auth, dashboard, casos, formularios, admin...
    components/             # UI compartida
    api/                    # cliente y contratos
    hooks/
    styles/
  .env.example
  Dockerfile
  .dockerignore
deploy/                     # configuración de servidor y hosting
docs/                       # arquitectura, operación y migración
docker-compose.yml
```

Los archivos legacy se conservarán como referencia. SQLite y adjuntos irán en volúmenes privados, fuera del repositorio y de las imágenes. Docker local tendrá servicios backend y frontend; SQLite no necesita un contenedor servidor de base de datos.

## 8. Migración y validación previstas

1. Obtener exportación de las 24 hojas, configuración efectiva y manifiesto de documentos; inventariar triggers instalados. No enviar secretos por chat.
2. Respaldo previo y diagnóstico: encabezados, IDs duplicados, referencias huérfanas, fechas, booleanos, filas eliminadas y variantes de catálogo. Informar conflictos sin descartarlos.
3. Importar roles/usuarios/permisos, catálogos, personas, formularios/preguntas/reglas/opciones y procesos en orden de dependencia; preservar IDs. Reconstruir cabeceras de respuestas y conservar filas históricas.
4. Transferir documentos con tamaño y hash, mantener asociación, procedencia y permisos. El antiguo importador de procesos no basta para migrar usuarios, configuración, formularios y auditoría: se necesita un comando de migración completo.
5. Conciliar conteos por tabla/estado, relaciones, respuestas y hashes; verificar permisos con cuentas de cada rol. Inicialización idempotente sin sobrescribir configuraciones importadas.
6. Probar borradores, reenvíos, conflicto concurrente, cierre transaccional, archivos, exportación, restauración y denegaciones por API directa.
7. Corte con escrituras legacy detenidas y respaldo final. Conservar rollback; si el sistema nuevo ya recibió datos, reconciliarlos antes de volver al anterior.

## 9. Viabilidad del alojamiento

FastAPI requiere ASGI. PythonAnywhere documenta soporte ASGI en beta mediante sus herramientas de línea de comandos/API; no se configurará como una aplicación WSGI ordinaria. Confirmar disponibilidad en la cuenta antes de comprometer el despliegue. Fuente: https://help.pythonanywhere.com/pages/ASGICommandLine

PythonAnywhere ofrece SQLite, pero desaconseja su uso como base productiva por el rendimiento del filesystem. Mantendremos SQLite conforme a lo solicitado, sujetos a prueba con el volumen real; si resulta insuficiente, las alternativas son otro host con disco local persistente o migrar a una base servidor. Fuente: https://help.pythonanywhere.com/pages/KindsOfDatabases

La estrategia es Docker para ejecución local y despliegue del código Python en el entorno del proveedor; no depende de ejecutar los contenedores en PythonAnywhere. Vercel construirá React y no alojará el archivo SQLite. La fase 5 precisará rutas, límites del plan, HTTPS, orígenes CORS exactos, credenciales y mecanismo de sesión. CORS no reemplaza autenticación ni permisos.

## 10. Decisiones pendientes antes de implementar

- Identidad: ¿solo cuentas del dominio institucional (cuál), o también @gmail.com previamente autorizadas? El manifiesto actual indica DOMAIN.
- Archivos: confirmar almacenamiento privado fuera de SQLite y traslado de adjuntos históricos; alternativamente, si se requieren binarios BLOB en SQLite, revisar volumen y respaldo antes de decidir.
- Datos: confirmar migración histórica y proporcionar exportación de Sheets/configuración cuando corresponda; volumen aproximado, número de usuarios simultáneos y tamaño total documental.
- Alojamiento: plan/cuenta PythonAnywhere; uso de dominios propios o direcciones predeterminadas para cerrar la estrategia de sesión.
- Confirmar sustitución de exportación Google Sheets por XLSX y los ajustes de seguridad descritos.

La fase 2 empieza únicamente después de la confirmación de esta fase y de resolver las decisiones críticas correspondientes.
