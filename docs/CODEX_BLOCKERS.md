# Bloqueos

## Técnicos ya resueltos

- La UI ahora permite recuperar errores y retomar un lote histórico `ANALIZADO`.
- La metadata ORM ahora coincide con 0025/0026; no se modificaron migraciones publicadas.
- Las suites completas backend y frontend ya fueron ejecutadas con éxito.

## Requieren intervención humana o capacidad externa

- QA visual autenticado: completado con el navegador integrado aislado. El wrapper de gstack en Windows sigue fallando por no localizar `server.ts`; es una limitación de esa herramienta, no de SITS, y no bloqueó QA.
- GitHub, Vercel y PythonAnywhere ya están autenticados; no son bloqueos. El PR todavía no existe y será creado durante el cierre controlado.
- n8n real sigue `NOT_RUN`: falta identificar una instancia y un workflow de ingesta aislado. Esto no bloquea la publicación web, pero impedirá declarar cierre total si no se resuelve o documenta como bloqueo externo.
