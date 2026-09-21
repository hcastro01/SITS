# Bloqueos

## Técnicos ya resueltos

- La UI ahora permite recuperar errores y retomar un lote histórico `ANALIZADO`.
- La metadata ORM ahora coincide con 0025/0026; no se modificaron migraciones publicadas.
- Las suites completas backend y frontend ya fueron ejecutadas con éxito.

## Requieren intervención humana o capacidad no instalada

- QA visual autenticado: el navegador de gstack no está instalado. Su instalación única requiere confirmación explícita de la herramienta; hasta entonces, login, navegación, historial, filtros, detalle y vista móvil quedan `PENDIENTE QA MANUAL/NO EJECUTADO`.
- PR: no existe PR abierto y `gh` no tiene autenticación. Se requiere una sesión/token GitHub autorizado para crear o actualizar el PR. El push de la rama se intentará sólo tras el commit final.
- Configuración real de `N8N_SITS_API_KEY`, workflow externo n8n, merge y despliegue requieren autorización y acceso externos. La API n8n local sí fue validada.
