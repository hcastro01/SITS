# Bloqueos

## Estado posterior al cierre de datos (2026-09-21)

- Importación histórica: **COMPLETADA**. No volver a subir ni confirmar el XLSX; el lote `351a817e-772f-4cf1-8083-1b6ba674e5c5` está `CONFIRMADO` y reconciliado.
- Vista móvil: **NO VERIFICADO**. El override integrado 390×844 mantuvo el área efectiva en 1707×735 CSS. La alternativa permitida de Chrome no aceptó la conexión de automatización de la pestaña autenticada y el control nativo no expuso una ventana; no se copiaron sesiones ni cookies. Falta una ejecución visual en un navegador/dispositivo que confirme el área CSS 390×844.
- n8n: **pendiente independiente, fuera del cierre**. No hay instancia/workflow autenticado de ingesta identificado ni se activó flujo alguno.

## Técnicos ya resueltos

- La UI ahora permite recuperar errores y retomar un lote histórico `ANALIZADO`.
- La metadata ORM ahora coincide con 0025/0026; no se modificaron migraciones publicadas.
- Las suites completas backend y frontend ya fueron ejecutadas con éxito.

## Requieren intervención humana o capacidad externa

- Importación histórica productiva: Chrome bloqueó la selección local del XLSX antes de transmitirlo (`fileChooser.setFiles` no autorizado por la extensión). No hubo carga, análisis, lote ni escritura de correos. Para reintentar, habilitar en Chrome el permiso de la extensión ChatGPT: `chrome://extensions` → Details → `Allow access to file URLs`. Véase la guía oficial enlazada por la extensión. Después, volver a analizar y confirmar una única vez el archivo ya prevalidado.
- n8n real sigue `NOT_RUN`: el inventario local sólo contiene un flujo inactivo de lectura/filtrado de Google Sheets; no se identificó una instancia autenticada ni un workflow de ingesta aislado hacia SITS. La clave de backend se guardó en producción sin revelarla, pero no se activó workflow alguno ni se realizaron operaciones sobre buzón.
