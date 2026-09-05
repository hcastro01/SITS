# Modelo de datos

Este documento describe el modelo físico que `TSConfig.schemas` crea en Google Sheets. Es el contrato de persistencia de la versión 1.0.0: los nombres de hoja y de columna distinguen mayúsculas y minúsculas y no deben renombrarse manualmente.

## Convenciones

- Cada hoja representa una entidad o un evento; la fila 1 contiene los encabezados y cada fila posterior representa un registro.
- Los identificadores se generan con `Utilities.getUuid()`; nunca dependen del número de filas.
- Las referencias entre hojas son identificadores lógicos. Google Sheets no aplica claves foráneas, por lo que los servicios validan las relaciones antes de escribir.
- Los booleanos se guardan como valores booleanos y las fechas como fechas reales siempre que el origen sea válido. Power BI debe tiparlas explícitamente al importar.
- Los archivos binarios viven en Drive. `Documentos` guarda únicamente sus metadatos y referencias.
- `RespuestasFormulario` usa un modelo vertical tipado: una fila por pregunta respondida. Los procesos principales conservan además sus columnas operativas.
- Los valores de selección múltiple pueden serializarse en una celda; para analítica de detalle deben expandirse en Power Query.

### Metadatos comunes

Salvo `Auditoria` y `Configuracion`, todas las tablas reciben al final estas columnas:

`Activo`, `Eliminado`, `FechaCreacion`, `CreadoPor`, `FechaActualizacion`, `ActualizadoPor`, `FechaEliminacion`, `UsuarioEliminacion`, `MotivoEliminacion`, `Version`, `ArchivoFuente`, `HojaFuente`, `RegistroFuente`, `FechaImportacion`, `UsuarioImportacion`.

`Importaciones` ya declara `ArchivoFuente`, `HojaFuente` y `UsuarioImportacion` como campos propios; al concatenar metadatos filtra esos tres para que cada encabezado aparezca una sola vez.

Reglas:

- Registro vigente: `Activo = TRUE` y `Eliminado = FALSE`.
- Borrado lógico: `Activo = FALSE`, `Eliminado = TRUE`, con fecha, usuario y motivo.
- Restauración: revierte los indicadores sin borrar el rastro de auditoría.
- Eliminación física excepcional: solo puede retirar la fila ya eliminada si `allowHardDelete = true` y no existen dependencias/documentos; no elimina la auditoría ni hace cascada.
- `Version` aumenta en cada actualización y sirve para detectar cambios.
- Las cinco columnas de origen permiten rastrear cargas históricas; permanecen vacías para capturas nativas.

## Relaciones principales

| Origen | Cardinalidad | Destino | Uso |
|---|---:|---|---|
| `Roles.IdRol` | 1:N | `Usuarios.RolId` | Rol asignado al usuario |
| `Roles.IdRol` | 1:N | `Permisos.RolId` | Matriz RBAC por módulo |
| `Personas.IdPersona` | 1:N | `Atenciones.IdPersona`, `Casos.IdPersona` | Maestro de colaboradores |
| `Formularios.IdFormulario` | 1:N | `Preguntas.IdFormulario`, `ReglasFormulario.IdFormulario`, `RespuestasFormulario.IdFormulario` | Definición y captura dinámica |
| `Preguntas.IdPregunta` | 1:N | `OpcionesPregunta.IdPregunta`, `RespuestasFormulario.IdPregunta` | Opciones y respuestas |
| `OpcionesPregunta.IdOpcion` | 1:N | `OpcionesPregunta.IdOpcionPadre` | Opciones dependientes |
| `Casos.IdCaso` | 1:0..1 | `DetalleCasosSensibles.IdCaso` | Separación de contenido restringido |
| `Recorridos.IdRecorrido` | 1:N | `HallazgosRecorrido.IdRecorrido` | Hallazgos del recorrido |
| `Casos.IdCaso` | 1:N | `Seguimientos`, `Derivaciones`, `Compromisos`, `Cierres` | Ciclo de vida del caso |
| `Seguimientos.IdSeguimiento` | 1:N | `Compromisos.IdSeguimiento` | Compromisos originados en un seguimiento |
| `(TipoRegistro, IdRegistro)` | N:1 lógica | Entidad propietaria | Asociación polimórfica de `Documentos` |
| `Catalogos.IdCatalogo` | 1:N | `Catalogos.IdCatalogoPadre` | Catálogos dependientes |

La cadena `Recorrido → Hallazgo → Novedad → Caso` se conserva mediante `IdRecorrido`, `IdNovedad` e `IdCaso` en `HallazgosRecorrido`.

## Esquema físico completo

Las columnas indicadas a continuación aparecen antes de los metadatos comunes.

### Seguridad y configuración

#### `Usuarios`

Clave primaria: `IdUsuario`.

Columnas: `IdUsuario`, `Correo`, `Nombre`, `RolId`, `Estado`, `UltimoAcceso`.

`Correo` se normaliza en minúsculas y debe ser único a nivel funcional. `Estado` controla si el usuario puede entrar.

#### `Roles`

Clave primaria: `IdRol`.

Columnas: `IdRol`, `Nombre`, `Descripcion`.

Los IDs iniciales son `ROLE_ADMIN`, `ROLE_COORDINADOR`, `ROLE_TRABAJADOR_SOCIAL`, `ROLE_CONSULTA` y `ROLE_GERENCIA`; los nombres visibles pueden modificarse sin cambiar las referencias.

#### `Permisos`

Clave primaria: `IdPermiso`.

Columnas: `IdPermiso`, `RolId`, `Modulo`, `PuedeCrear`, `PuedeLeer`, `PuedeEditar`, `PuedeEliminar`, `PuedeSensible`, `PuedeExportar`.

La combinación funcional `RolId + Modulo` debe ser única. Los módulos reconocidos son `DASHBOARD`, `ATENCIONES`, `CASOS`, `NOVEDADES`, `RECORRIDOS`, `SEGUIMIENTOS`, `DERIVACIONES`, `COMPROMISOS`, `PERSONAS`, `FORMULARIOS`, `RESPUESTAS`, `CATALOGOS`, `DOCUMENTOS`, `BUSQUEDA`, `REPORTES`, `IMPORTACION`, `AUDITORIA` y `ADMINISTRACION`.

#### `Configuracion`

Clave primaria: `Clave`.

Columnas: `Clave`, `Valor`, `Descripcion`, `Tipo`, `Editable`, `FechaActualizacion`, `ActualizadoPor`.

Esta hoja contiene configuración administrable, no secretos. Los IDs de Spreadsheet y Drive se guardan en Script Properties, no aquí.

### Maestros y formularios

#### `Personas`

Clave primaria: `IdPersona`.

Columnas: `IdPersona`, `CodigoEmpleado`, `Cedula`, `Nombre`, `Cargo`, `Area`, `Departamento`, `Centro`, `SubCentro`, `Turno`, `EstadoLaboral`.

`CodigoEmpleado` y `Cedula` deben tratarse como texto para conservar ceros iniciales. La aplicación referencia `IdPersona`; los campos de nombre en transacciones son instantáneas operativas, no nuevas personas.

#### `Formularios`

Clave primaria: `IdFormulario`.

Columnas: `IdFormulario`, `Nombre`, `Descripcion`, `Proceso`, `Estado`, `Responsable`, `FechaPublicacion`.

Estados funcionales: `BORRADOR`, `PUBLICADO`, `INACTIVO`. Solo los publicados se ofrecen para captura final.

#### `Preguntas`

Clave primaria: `IdPregunta`.

Columnas: `IdPregunta`, `IdFormulario`, `Etiqueta`, `Descripcion`, `Tipo`, `Obligatoria`, `Orden`, `Categoria`, `Subcategoria`, `ValorPredeterminado`, `TextoAyuda`, `Visible`, `SoloLectura`, `LongitudMaxima`, `Validacion`, `Sensibilidad`, `CondicionVisibilidad`, `CampoDependiente`, `ValorDependiente`, `Formula`.

Tipos admitidos: `TEXTO_CORTO`, `TEXTO_LARGO`, `NUMERO`, `FECHA`, `FECHA_HORA`, `HORA`, `SI_NO`, `LISTA_DESPLEGABLE`, `SELECCION_UNICA`, `SELECCION_MULTIPLE`, `ESCALA_LIKERT`, `PERSONA`, `AREA`, `TURNO`, `ARCHIVO`, `FOTOGRAFIA`, `PDF`, `DOCUMENTO`, `CAMPO_CALCULADO`, `CAMPO_OCULTO` y `SECCION`.

Para `PERSONA`, la interfaz busca remotamente en `Personas` por nombre, cédula o `CodigoEmpleado`; la respuesta persistida conserva el `IdPersona` y la instantánea estructurada del nombre seleccionado. No se admite usar texto libre como sustituto de la referencia.

#### `OpcionesPregunta`

Clave primaria: `IdOpcion`.

Columnas: `IdOpcion`, `IdPregunta`, `Valor`, `Etiqueta`, `Orden`, `IdCatalogo`, `IdOpcionPadre`.

`IdCatalogo` permite reutilizar una opción maestra; `IdOpcionPadre` modela dependencia dentro de una pregunta.

#### `ReglasFormulario`

Clave primaria: `IdRegla`.

Columnas: `IdRegla`, `IdFormulario`, `IdPreguntaOrigen`, `Operador`, `ValorComparacion`, `IdPreguntaDestino`, `Accion`, `Mensaje`, `Orden`.

Las reglas se evalúan en orden. Origen, operador y comparación determinan una acción sobre la pregunta destino; el servidor vuelve a validar los campos visibles/obligatorios.

#### `RespuestasFormulario`

Clave primaria: `IdDetalleRespuesta`.

Columnas: `IdDetalleRespuesta`, `IdRespuesta`, `IdEnvioCliente`, `IdFormulario`, `IdPregunta`, `IdRegistroProceso`, `EstadoRespuesta`, `ValorTexto`, `ValorNumero`, `ValorFecha`, `ValorBooleano`, `ValorOpcion`, `FechaRespuesta`, `UsuarioRespuesta`.

`IdRespuesta` agrupa todas las filas de un envío. `IdEnvioCliente` es la clave de idempotencia que permite reconocer un reenvío del navegador. `IdRegistroProceso` enlaza, cuando corresponde, el caso, atención, novedad u otro registro estructurado creado por la respuesta. Debe poblarse una sola columna `Valor*` según el tipo de pregunta.

#### `Catalogos`

Clave primaria: `IdCatalogo`.

Columnas: `IdCatalogo`, `Tipo`, `Codigo`, `Valor`, `Descripcion`, `Orden`, `IdCatalogoPadre`, `TipoPadre`, `CodigoPadre`, `EsSensible`.

La combinación funcional recomendada es `Tipo + Codigo`. La jerarquía padre soporta proceso, categoría, subcategoría y gestión dependientes. Un valor usado se desactiva mediante metadatos; no se elimina físicamente. `EsSensible` configura sensibilidad sin inventar categorías.

### Procesos de Trabajo Social

#### `Atenciones`

Clave primaria: `IdAtencion`.

Columnas: `IdAtencion`, `Fecha`, `Hora`, `IdPersona`, `Colaborador`, `Responsable`, `TipoAtencion`, `Motivo`, `Canal`, `Gestion`, `Resultado`, `RequiereSeguimiento`, `GeneraCaso`, `Observaciones`, `Evidencias`, `Estado`.

#### `Casos`

Clave primaria: `IdCaso`; clave de negocio: `CodigoCaso`.

Columnas: `IdCaso`, `CodigoCaso`, `FechaApertura`, `IdPersona`, `Colaborador`, `Responsable`, `TipoCaso`, `SubtipoCaso`, `Prioridad`, `NivelSensibilidad`, `EstadoCaso`, `TipoGestion`, `TipoEvento`, `Area`, `Turno`, `CondicionLaboral`, `Restriccion`, `FechaInicioRestriccion`, `Derivacion`, `UltimoSeguimiento`, `FechaCierre`, `MotivoCierre`, `Resultado`, `Evidencias`.

Un caso cerrado requiere `FechaCierre` y `MotivoCierre`; una restricción activa requiere `FechaInicioRestriccion`.

#### `DetalleCasosSensibles`

Clave primaria: `IdDetalleSensible`; referencia: `IdCaso`.

Columnas: `IdDetalleSensible`, `IdCaso`, `DescripcionSensible`, `Antecedentes`, `DiagnosticoSocial`, `Intervencion`, `NotasPrivadas`.

Esta hoja se mantiene fuera de exportaciones gerenciales y solo se lee con permiso `PuedeSensible`.

#### `Novedades`

Clave primaria: `IdNovedad`.

Columnas: `IdNovedad`, `Fecha`, `Hora`, `Responsable`, `Fuente`, `Tipo`, `Subtipo`, `Area`, `Turno`, `Lugar`, `Descripcion`, `Impacto`, `Prioridad`, `AccionInmediata`, `GeneraAtencion`, `GeneraCaso`, `Estado`, `Evidencias`.

#### `Recorridos`

Clave primaria: `IdRecorrido`.

Columnas: `IdRecorrido`, `Fecha`, `HoraInicio`, `HoraFin`, `Responsable`, `Planta`, `Area`, `Turno`, `Objetivo`, `Observaciones`, `PersonasContactadas`, `NovedadesDetectadas`, `Acciones`, `Evidencias`.

#### `HallazgosRecorrido`

Clave primaria: `IdHallazgo`; referencia obligatoria: `IdRecorrido`.

Columnas: `IdHallazgo`, `IdRecorrido`, `TipoHallazgo`, `Categoria`, `Subcategoria`, `Area`, `Descripcion`, `Prioridad`, `Accion`, `GeneraNovedad`, `IdNovedad`, `GeneraCaso`, `IdCaso`, `Estado`.

#### `Seguimientos`

Clave primaria: `IdSeguimiento`; referencia: `IdCaso`.

Columnas: `IdSeguimiento`, `IdCaso`, `Fecha`, `Hora`, `Responsable`, `TipoSeguimiento`, `Canal`, `Tecnica`, `Descripcion`, `Resultado`, `ProximaAccion`, `FechaProximaAccion`, `Estado`, `Evidencias`.

Si se informa `ProximaAccion`, se exige `FechaProximaAccion`.

#### `Derivaciones`

Clave primaria: `IdDerivacion`; referencia: `IdCaso`.

Columnas: `IdDerivacion`, `IdCaso`, `Fecha`, `AreaDestino`, `ResponsableDestino`, `Motivo`, `Estado`, `FechaRespuesta`, `Resultado`, `FechaCierre`, `Observaciones`.

Toda derivación requiere caso, área destino y motivo.

#### `Compromisos`

Clave primaria: `IdCompromiso`; referencias: `IdCaso` e `IdSeguimiento` opcional.

Columnas: `IdCompromiso`, `IdCaso`, `IdSeguimiento`, `FechaCreacionCompromiso`, `Responsable`, `Descripcion`, `FechaLimite`, `Estado`, `FechaCumplimiento`, `Evidencia`, `Observacion`.

Todo compromiso requiere caso, responsable, descripción y estado.

#### `Cierres`

Clave primaria: `IdCierre`; referencia: `IdCaso`.

Columnas: `IdCierre`, `IdCaso`, `FechaCierreCaso`, `Responsable`, `MotivoCierre`, `ResultadoFinal`, `Evidencia`, `RequiereMonitoreo`, `Observacion`.

Crear un cierre actualiza también el estado y datos de cierre del caso principal bajo el mismo bloqueo lógico.

### Documentos, auditoría e importación

#### `Documentos`

Clave primaria: `IdArchivo`; referencia lógica: `TipoRegistro + IdRegistro`.

Columnas: `IdArchivo`, `IdRegistro`, `TipoRegistro`, `NombreArchivo`, `MimeType`, `Extension`, `TamanoBytes`, `DriveFileId`, `Url`, `FechaCarga`, `UsuarioCarga`, `CategoriaDocumento`, `Sensibilidad`.

`DriveFileId` es la referencia canónica. `Url` no implica acceso público: Drive vuelve a comprobar que la cuenta tenga permiso. El borrado normal solo desactiva el metadato y conserva el archivo.

#### `Auditoria`

Clave primaria: `IdAuditoria`.

Columnas exactas: `IdAuditoria`, `Tabla`, `IdRegistro`, `Accion`, `Usuario`, `FechaHora`, `Campo`, `ValorAnterior`, `ValorNuevo`, `Motivo`, `CorrelationId`.

No recibe metadatos comunes y se trata como registro append-only. Acciones admitidas: `CREATE`, `UPDATE`, `DELETE`, `RESTORE`, `VIEW_SENSITIVE`, `DOWNLOAD_FILE`, `IMPORT` y `LOGIN`. Un cambio multicolumna puede producir una fila por campo; las importaciones usan un evento resumido por registro para no agotar tiempo/cuota.

#### `Importaciones`

Clave primaria: `IdImportacion`.

Columnas físicas completas: `IdImportacion`, `TablaDestino`, `ArchivoFuente`, `HojaFuente`, `TotalFilas`, `FilasImportadas`, `FilasError`, `Estado`, `Errores`, `FechaInicio`, `FechaFin`, `UsuarioImportacion`, `Activo`, `Eliminado`, `FechaCreacion`, `CreadoPor`, `FechaActualizacion`, `ActualizadoPor`, `FechaEliminacion`, `UsuarioEliminacion`, `MotivoEliminacion`, `Version`, `RegistroFuente`, `FechaImportacion`.

`Errores` contiene el resumen serializado del lote. Cada registro aceptado recibe además la trazabilidad de origen en sus metadatos comunes.

## Integridad y comportamiento de escritura

1. El servicio valida que la tabla pertenezca al catálogo de esquemas.
2. El servidor filtra el payload a columnas conocidas; el cliente no puede crear columnas arbitrarias.
3. Se aplican las reglas de negocio y permisos correspondientes.
4. Las escrituras críticas usan `LockService` y UUID.
5. Se completa el bloque de metadatos y la versión.
6. Se escribe la fila o se actualiza la fila identificada.
7. Se registra auditoría con `CorrelationId`.

Sheets no ofrece transacciones relacionales entre hojas. Un error después de una escritura puede dejar una operación compuesta parcialmente aplicada; la auditoría y el `CorrelationId` permiten reconciliarla. Para requisitos de atomicidad estricta se debe migrar a una base transaccional.

## Preparación para Power BI

### Modelo recomendado

- Hechos: `Casos`, `Atenciones`, `Novedades`, `Recorridos`, `HallazgosRecorrido`, `Seguimientos`, `Derivaciones`, `Compromisos`, `Cierres` y `RespuestasFormulario`.
- Dimensiones: `Personas`, `Catalogos`, `Formularios`, `Preguntas` y una dimensión calendario creada en Power BI.
- Relaciones: uno a muchos, filtro en una sola dirección desde dimensiones a hechos.
- `Documentos` aporta conteos y categorías, nunca el contenido binario.
- `DetalleCasosSensibles`, `Usuarios`, `Permisos`, `Auditoria` y `Configuracion` deben excluirse del conjunto gerencial salvo necesidad aprobada y controlada.

### Carga segura

No se recomienda publicar la hoja transaccional en la web. Cree un libro de reporting separado, con solo columnas autorizadas y acceso de solo lectura, o programe una exportación controlada hacia una fuente empresarial. En Power Query:

1. tipar IDs, cédula y código de empleado como texto;
2. tipar fechas y booleanos explícitamente;
3. filtrar `Activo = TRUE` y `Eliminado = FALSE`;
4. ocultar o enmascarar sensibilidad antes de entregar el dataset;
5. deduplicar dimensiones por su ID, no por nombre;
6. expandir respuestas múltiples si se necesitan conteos por opción;
7. conservar zona horaria `America/Guayaquil` y definir la política de conversión a UTC.

### Indicadores base

- Casos abiertos/cerrados: conteo distinto de `Casos.IdCaso` por `EstadoCaso`.
- Seguimientos próximos: `Seguimientos.FechaProximaAccion` futura y registro vigente.
- Compromisos vencidos: `FechaLimite` anterior a hoy y estado no final.
- Recorridos: conteo distinto de `IdRecorrido` por fecha, planta, área y turno.
- Tasa de conversión: atenciones con `GeneraCaso = TRUE` sobre atenciones vigentes; si se requiere trazabilidad exacta, debe existir el enlace de negocio al caso y no inferirse solo por nombre o fecha.

## Evolución del modelo

- No agregue columnas directamente en una hoja productiva. Primero cambie `TSConfig.schemas`, incremente la versión de setup y ejecute una migración idempotente.
- No reutilice un ID ni cambie el significado de una columna existente.
- Añada nuevas entidades en hojas separadas y registre su módulo, clave y permisos.
- Antes de importar históricos, homologue únicamente equivalencias confirmadas; preserve el valor original y marque dudas para revisión.
- Para migrar a Cloud SQL, Dataverse o Firebase, mantenga estos UUID como claves naturales de transición y conserve los identificadores de origen.
