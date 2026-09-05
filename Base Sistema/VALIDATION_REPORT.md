# Informe de validación

Fecha: 2026-08-23  
Proyecto: Sistema Integral de Gestión de Trabajo Social

## Resultado

La validación local terminó sin fallos bloqueantes.

## Comprobaciones superadas

- sintaxis V8 válida en los 17 archivos `.gs`;
- sintaxis válida del JavaScript completo de `Scripts.html`;
- `appsscript.json` parseable y con scopes explícitos;
- los 10 parciales declarados por `Index.html` existen;
- los 41 métodos RPC consumidos por el cliente tienen endpoint público en Apps Script;
- 24 hojas definidas, con identificador presente y sin encabezados duplicados;
- 249 identificadores HTML estáticos únicos;
- 203 referencias `byId(...)` resueltas contra elementos existentes;
- 55 etiquetas HTML asociadas a controles existentes;
- ausencia de `innerHTML`, `insertAdjacentHTML`, `eval` y `new Function` en el código entregado;
- HTML ensamblado localmente: HTTP 200, 211 KB y presencia de Dashboard, Captura, Formularios, Casos, Consulta y Administración;
- importación de Google Sheets limitada a la carpeta segura `TrabajoSocial/Importaciones`;
- revisión de permisos, herencia sensible, doble envío, locks, soft delete, hard delete deshabilitado por defecto y firmas binarias.

## Hallazgos corregidos durante QA

- riesgo de autoelevación mediante reejecución de setup;
- adjuntos hijos que no heredaban sensibilidad del caso;
- doble envío validado fuera del bloqueo;
- valores personales visibles en auditoría;
- encabezados duplicados en `Importaciones`;
- pregunta de archivo obligatoria no incluida en la respuesta estructurada;
- módulos de navegación desalineados con la matriz RBAC;
- error de sintaxis en el render de detalle;
- importación por `spreadsheetId` susceptible a uso delegado del acceso del propietario.

## Validaciones que requieren Google Workspace

No es posible ejecutar localmente `SpreadsheetApp`, `DriveApp`, `Session`, `LockService`, `CacheService` ni el despliegue real de HTML Service. Antes de producción se debe ejecutar en un dominio de prueba el recorrido completo de `TEST_CHECKLIST.md`, incluidos permisos por rol, caso sensible, carga/descarga, concurrencia, importación y rollback.

La revisión visual automatizada con el navegador integrado no pudo iniciarse por una restricción de permisos del runtime de escritorio. Se sustituyó por ensamblado HTTP local y comprobaciones estáticas de DOM, CSS y JavaScript; se recomienda completar una revisión visual manual en las resoluciones indicadas en el checklist después del despliegue `/dev`.
