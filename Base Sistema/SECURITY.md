# Seguridad y protección de datos

El sistema procesa datos laborales y sociales potencialmente sensibles. Debe desplegarse como aplicación interna de Google Workspace, con mínimo privilegio, una cuenta propietaria administrada y controles organizacionales de Drive. Esta versión no debe publicarse para acceso anónimo.

## Modelo de amenazas

Activos principales:

- expedientes y detalle sensible de casos;
- datos personales de colaboradores;
- documentos y evidencias en Drive;
- matriz de usuarios, roles y permisos;
- historial de auditoría;
- IDs de Spreadsheet y carpeta raíz;
- código y despliegues del proyecto Apps Script.

Actores considerados:

- usuario autenticado con permisos válidos;
- usuario interno que intenta exceder su rol;
- usuario deshabilitado o no registrado;
- persona con acceso directo indebido a Sheet, Drive o al proyecto;
- contenido malicioso ingresado en texto o archivos;
- operación concurrente, reenvío o manipulación del payload del navegador.

Límites de confianza:

1. El navegador es no confiable: la visibilidad de botones solo mejora la experiencia y nunca concede autorización.
2. Las funciones públicas de Apps Script son la frontera de autorización.
3. Sheets, Drive y Script Properties son recursos privilegiados bajo la identidad del despliegue.
4. Power BI, CSV y hojas exportadas abandonan el perímetro transaccional y requieren una política de acceso propia.

## Controles implementados

| Riesgo | Control en la implementación |
|---|---|
| Identidad falsa o ausente | `TSAuth.activeEmail()` usa `Session.getActiveUser().getEmail()`. Con `allowTestIdentity = false`, una identidad vacía falla con `IDENTITY_UNAVAILABLE`; no existe contraseña local ni identidad de respaldo en producción. |
| Usuario no autorizado | `TSAuth.current()` exige una fila vigente en `Usuarios`, estado `ACTIVO`, rol vigente y permisos configurados. |
| Escalada por interfaz | `TSAuth.authorize(modulo, accion)` comprueba servidor-side `PuedeCrear`, `PuedeLeer`, `PuedeEditar`, `PuedeEliminar`, `PuedeSensible` o `PuedeExportar`. Ocultar navegación no sustituye esta validación. |
| Acceso a caso sensible | El nivel se resuelve en `Catalogos` (`Tipo = NIVEL_SENSIBILIDAD`, `EsSensible = TRUE`). El detalle requiere `PuedeSensible`; las vistas sin permiso reciben datos enmascarados. Los accesos relevantes se auditan. |
| Exposición en auditoría | `AuditService` reemplaza valores de campos sensibles por `[VALOR SENSIBLE MODIFICADO]` y no conserva su contenido anterior/nuevo. |
| Payload con columnas arbitrarias | `TSValidation.record()` y `TSData.prepare()` filtran contra el esquema permitido en `TSConfig`; el servidor aplica reglas de negocio. |
| Fórmula inyectada en Sheets | `TSUtils.stringifyCell()` antepone apóstrofo a texto que comienza por `=`, `+`, `-` o `@`. |
| XSS | El servidor limpia caracteres de control y ofrece `escapeHtml`; la interfaz debe insertar valores con `textContent`/atributos seguros, no con `innerHTML` construido desde entradas. |
| ID predecible o duplicado | Los IDs usan UUID; las escrituras críticas usan `LockService` y vuelven a comprobar duplicados. |
| Pérdida por edición concurrente | Cada fila tiene `Version`; las actualizaciones con `expectedVersion` desactualizada fallan con `VERSION_CONFLICT`. |
| Eliminación silenciosa | El flujo normal usa soft delete con motivo, usuario y fecha. `hardDeleteRecord` está bloqueado por `allowHardDelete = false`; al habilitarlo exige `ADMINISTRACION:edit`, permiso de eliminar la entidad, sensibilidad cuando aplique, soft delete previo, motivo, confirmación exacta y cero dependencias/documentos. La auditoría se escribe antes de retirar la fila. |
| Archivo camuflado | Se comprueban extensión, MIME declarado, tamaño estimado y real, y firma binaria para JPG/JPEG, PNG, PDF, DOC/XLS y DOCX/XLSX. |
| Exceso de archivos | Configuración inicial: máximo 10 MiB por archivo y 10 archivos vigentes por registro. La cuenta se valida de nuevo dentro del bloqueo. |
| Nombre de archivo peligroso | `safeFileName()` elimina caracteres inválidos y limita la longitud. |
| Archivo público | La carga crea archivos dentro de la carpeta privada configurada; el código no ejecuta `setSharing(...ANYONE...)`. |
| Lectura arbitraria al importar | Un `spreadsheetId` solo se acepta si el archivo es Google Sheets nativo y su padre directo es la carpeta de staging `TrabajoSocial/Importaciones` creada por setup. |
| Enumeración de Drive | Los listados eliminan `DriveFileId` y `Url`. `accessFile()` entrega el enlace solo después de validar registro, rol y sensibilidad y registra `DOWNLOAD_FILE`. |
| Stack trace al usuario | `TSErrors.guard()` devuelve un mensaje amigable y un `correlationId`; el detalle técnico permanece en el registro de ejecuciones. |
| IDs de infraestructura en cliente | `TS_SPREADSHEET_ID`, `TS_ROOT_FOLDER_ID` y `TS_IMPORT_FOLDER_ID` viven en Script Properties. No deben incluirse en el bootstrap, HTML, URLs de navegación ni mensajes de error. |
| Reconfiguración de infraestructura | `setupApplication()` exige que usuario activo y efectivo sean la cuenta propietaria; en una instalación existente exige además `ADMINISTRACION:edit`. Un usuario del dominio no puede sustituir los IDs mediante RPC. |
| Lecturas repetitivas | La caché tiene versión por tabla y se invalida al escribir. CacheService es una optimización, no una fuente de autorización ni de verdad. |

## Roles y permisos

La instalación crea cinco roles base configurables:

- Administrador: operación y configuración completas.
- Coordinador / Relaciones Laborales: supervisión consolidada según la matriz.
- Trabajador Social: captura y gestión operativa autorizada.
- Consulta: solo lectura de módulos habilitados.
- Gerencia: datos agregados, sin detalle sensible por defecto.

La matriz efectiva está en `Permisos`. La seguridad depende de la combinación `RolId + Modulo`; cambiar el nombre visible del rol no cambia sus permisos. Para un caso sensible deben cumplirse dos condiciones: permiso de lectura del módulo y `PuedeSensible = TRUE`.

Principios operativos:

- ninguna persona debe compartir cuentas;
- una baja laboral debe desactivar primero `Usuarios.Estado`;
- el rol de Administrador debe limitarse a un grupo pequeño y revisarse periódicamente;
- Gerencia no debe recibir `PuedeSensible` salvo autorización formal;
- exportación se concede por separado de lectura;
- las cuentas técnicas/propietarias deben usar MFA y recuperación administrada.

## Despliegue seguro

El manifiesto suministrado usa:

- `executeAs: USER_DEPLOYING`;
- `access: DOMAIN`;
- scopes de lectura/escritura de Sheets, Drive y correo del usuario.

Este perfil centraliza el acceso bajo la cuenta que despliega y limita la URL al dominio. `Session.getActiveUser().getEmail()` puede devolver vacío según la política y modalidad del dominio; la aplicación falla de forma cerrada. Antes de producción, haga una prueba con una cuenta no administradora del mismo dominio. Si la identidad no está disponible, no habilite `allowTestIdentity`: cambie el despliegue a “usuario que accede” o revise la política con el administrador de Workspace.

Consecuencias de ejecutar como propietario:

- el propietario debe conservar acceso a Spreadsheet y carpeta raíz;
- todos los llamados consumen cuotas del despliegue en los casos definidos por Google;
- la cuenta propietaria no debe ser una cuenta personal que pueda darse de baja;
- el código jamás debe enviar el token OAuth del propietario al cliente.

Los scopes declarados son deliberadamente explícitos:

```text
https://www.googleapis.com/auth/spreadsheets
https://www.googleapis.com/auth/drive
https://www.googleapis.com/auth/userinfo.email
```

El scope completo de Drive es necesario con `DriveApp` para crear carpetas, escribir evidencias y recuperar archivos existentes por ID. Si la solución evoluciona a Drive API con selección limitada de archivos, reevalúe si puede reducirse a un alcance más estrecho.

### Checklist previo a producción

- [ ] Usar una cuenta propietaria institucional, protegida con MFA y con sucesión definida.
- [ ] Restringir el despliegue a usuarios del dominio; nunca “cualquiera, incluso anónimo”.
- [ ] Confirmar que una cuenta de prueba es identificada por su correo y no hereda la cuenta propietaria.
- [ ] Verificar `allowTestIdentity = false` y eliminar `TS_TEST_USER_EMAIL` de Script Properties.
- [ ] Limitar editores del proyecto, Spreadsheet y carpeta raíz al equipo administrador.
- [ ] Mantener el Spreadsheet sin enlace público y fuera de carpetas compartidas amplias.
- [ ] Mantener Drive con `GENERAL`/`DOMAIN_WITH_LINK` deshabilitado; revisar permisos heredados.
- [ ] Proteger manualmente las hojas `Auditoria`, `Permisos`, `Usuarios`, `DetalleCasosSensibles` y `Configuracion` contra edición directa.
- [ ] Crear usuarios explícitos; una persona del dominio sin fila activa debe recibir 403.
- [ ] Revisar el catálogo de sensibilidad con responsables funcionales; no asumir categorías.
- [ ] Tratar todo cambio de `EsSensible` como cambio de seguridad: revisar impacto sobre casos históricos antes de guardarlo.
- [ ] Probar acceso sensible, descarga, exportación, soft delete y restauración con cada rol.
- [ ] Configurar retención, respaldo, eDiscovery/DLP y alertas según la política de la organización.
- [ ] Mantener `allowHardDelete = false` salvo autorización formal; si se activa, probar confirmación, dependencias y conservación de Auditoría antes de usarlo.
- [ ] Revisar ejecuciones fallidas y auditoría con periodicidad definida.
- [ ] Asegurar que los datasets de Power BI omitan detalle sensible y datos de seguridad.

## Drive y descargas

La estructura es `TrabajoSocial/<Entidad>/<IdRegistro>/Documentos`. La aplicación no hace público un archivo, pero el enlace que devuelve `accessFile()` sigue sujeto a las ACL de Drive.

Esto produce una limitación importante:

- si el usuario no tiene permiso de Drive, Google negará la vista/descarga aunque la aplicación lo autorice;
- si se comparte una carpeta ampliamente, un usuario podría llegar al archivo directamente sin pasar por la auditoría de la Web App.

Por tanto, los permisos de Drive deben alinearse con la matriz de la aplicación. Para un volumen pequeño puede compartirse por grupos funcionales y separar físicamente carpetas sensibles/no sensibles. Si se necesita autorización por archivo exclusivamente desde la aplicación, la alternativa futura es un servicio de descarga autenticado con almacenamiento privado (por ejemplo, Cloud Storage con URLs firmadas de corta vida y comprobación de rol), no enlaces permanentes de Drive.

Revocar un rol en la aplicación no revoca automáticamente permisos otorgados directamente en Drive. La baja debe revisar ambos sistemas.

## Seguridad de archivos: alcance real

La comprobación de firma impide las falsificaciones más simples, pero no es un antivirus, un sandbox de Office ni una solución DLP. Los formatos heredados `.doc` y `.xls` pueden contener contenido activo; los formatos OOXML también pueden contener relaciones o contenido peligroso aunque la extensión sea válida.

Medidas requeridas:

- no abrir archivos sospechosos en equipos no administrados;
- usar las protecciones antimalware y DLP de Google Workspace;
- bloquear tipos adicionales en `TS_CONFIG_JSON` si la política no permite documentos heredados;
- considerar un escáner privado de malware antes de ampliar el uso;
- no integrar servicios públicos de análisis para evidencias sensibles sin acuerdo de tratamiento de datos.

## XSS, HTML e inyección

Reglas para cualquier ampliación:

- usar `textContent` para etiquetas, nombres, resultados y errores;
- no interpolar texto de usuario en plantillas HTML ni en `innerHTML`;
- si es imprescindible renderizar HTML, aplicar una lista blanca de elementos/atributos;
- validar todos los filtros y nombres de tabla en el servidor;
- conservar la neutralización de fórmulas al escribir o exportar CSV;
- no incluir IDs de Drive/Sheet, tokens, stack traces ni datos sensibles en atributos `data-*`;
- no confiar en `disabled`, `hidden` ni en rutas del navegador como controles de acceso.

## Auditoría y privacidad

Acciones auditables: `CREATE`, `UPDATE`, `DELETE`, `RESTORE`, `VIEW_SENSITIVE`, `DOWNLOAD_FILE`, `IMPORT` y `LOGIN`. Cada solicitud genera un `CorrelationId` para relacionar respuesta, ejecución y filas de auditoría.

Limitaciones:

- `Auditoria` es append-only para la aplicación, pero un editor del Spreadsheet aún puede cambiarla;
- los registros de Apps Script/Cloud Logging no deben incluir payloads completos, base64 ni PII;
- los valores sensibles se enmascaran en auditoría, por lo que el histórico registra que cambiaron, no su contenido;
- deben definirse retención y purga legalmente aprobadas; el proyecto no inventa ese plazo.

Para inmutabilidad regulatoria, exporte eventos a un almacén con retención bloqueada y acceso separado.

## Copias de seguridad y recuperación

El setup es idempotente, pero no es una copia de seguridad. Antes de cambios de esquema o importaciones:

1. cree una copia versionada del Spreadsheet;
2. confirme que la carpeta Drive conserva propietario y ACL;
3. exporte configuración, usuarios, permisos y catálogo;
4. pruebe restauración en un proyecto no productivo;
5. conserve el ID del lote de importación y su informe de errores.

No restaure filas copiándolas manualmente sobre producción mientras la Web App está activa. Detenga el uso, reconcilie UUID/versiones y documente la intervención.

## Respuesta a incidentes

Ante exposición o acceso indebido:

1. deshabilite el usuario y, si corresponde, el despliegue;
2. revoque permisos directos y heredados de Drive/Sheets;
3. preserve `Auditoria`, historial de ejecuciones y versiones del archivo;
4. identifique eventos por usuario, registro, acción y `CorrelationId`;
5. rote la cuenta propietaria o vuelva a desplegar si existe riesgo sobre sus credenciales;
6. notifique según la política de privacidad y seguridad aplicable;
7. corrija el control y ejecute nuevamente las pruebas negativas antes de reabrir.

## Riesgos residuales y evolución

| Riesgo residual | Tratamiento actual | Evolución recomendada |
|---|---|---|
| Sheets no ofrece seguridad por fila | RBAC en servicios y hoja no compartida con usuarios finales | Base de datos con Row-Level Security |
| Auditoría editable por propietarios | Acceso restringido y trazabilidad por evento | Log externo inmutable/SIEM |
| Drive ACL y RBAC pueden divergir | Revisión manual por grupos y descarga auditada | Almacenamiento privado con gateway autenticado |
| Archivo válido puede ser malicioso | Allowlist, tamaño y firma | Escaneo antimalware/DLP automatizado |
| Datos sensibles sin cifrado de campo | Cifrado de Google y mínimo acceso | Cifrado de campo/Cloud KMS si el riesgo lo exige |
| Identidad depende del contexto de Apps Script | Fail-closed y prueba de dominio | IdP/IAP o backend con tokens verificables |
| Apps Script/Sheets no tiene transacciones ACID | Lock, versión, auditoría y compensación | Cloud SQL/Dataverse para atomicidad |

Fuentes oficiales relevantes: [identidad de Session](https://developers.google.com/apps-script/reference/base/session), [modalidades de Web Apps](https://developers.google.com/apps-script/guides/web), [autorización y scopes](https://developers.google.com/apps-script/guides/services/authorization) y [cuotas de Apps Script](https://developers.google.com/apps-script/guides/services/quotas).
