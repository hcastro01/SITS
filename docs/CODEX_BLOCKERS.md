# Bloqueos

## Técnicos ya resueltos

- La UI ahora permite recuperar errores y retomar un lote histórico `ANALIZADO`.
- La metadata ORM ahora coincide con 0025/0026; no se modificaron migraciones publicadas.
- Las suites completas backend y frontend ya fueron ejecutadas con éxito.

## Requieren intervención humana o capacidad externa

- QA visual autenticado: completado con el navegador integrado aislado. El wrapper de gstack en Windows sigue fallando por no localizar `server.ts`; es una limitación de esa herramienta, no de SITS, y no bloqueó QA.
- PR: no existe PR abierto y `gh` no tiene autenticación. Falta una sesión GitHub autorizada para crear o actualizar el PR; no se extrajeron tokens ni cookies personales.
- Configuración real de `N8N_SITS_API_KEY`, workflow externo n8n, merge y despliegue requieren autorización y acceso externos. La API n8n local sí fue validada.
