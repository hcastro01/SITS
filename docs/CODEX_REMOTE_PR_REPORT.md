# Estado remoto y PR

- Upstream: `origin` apunta a `https://github.com/hcastro01/SITS.git`.
- La rama remota `codex/correos-n8n-production-readiness` está en `e6bd6298f33df6e285e852ccd009595371c799b9`; los cambios posteriores a `35860b5` son documentación de evidencia.
- `gh` está autenticado como `hcastro01` con permiso administrador. No existe aún un PR contra `master` para esta rama.
- La candidata está 11 commits por delante y 0 por detrás de `origin/master` `08246dfbff1db6dcb63d4fb560fc18e3ce556a99`.
- Checks del SHA candidato: `Vercel Preview Comments` y `Vercel` finalizaron `success`. No hay Actions ni checks de backend/frontend remotos; los resultados locales vigentes son 325/325 backend y 158/158 frontend.

## PR preparado, no creado

- Título: `feat(correos): cerrar importación y seguimiento con n8n seguro`.
- Base: `master`; head: `codex/correos-n8n-production-readiness`.
- Descripción: incluye migraciones `0025`/`0026`, importación XLSX trazable y deduplicada, dashboard/filtros/detalle/seguimientos, endpoint n8n Bearer idempotente validado sólo localmente, lote histórico comprobado, fixture UI sintético y QA visual. Señalar explícitamente: sin workflow n8n real, sin merge, sin despliegue ni cambios de producción.
- Procedimiento humano mínimo: ejecutar `gh auth login --web --hostname github.com`, crear el PR contra `master` con la rama anterior y revisar los checks asociados a `35860b5`. No usar tokens/cookies extraídos ni force-push.
- No hubo merge ni auto-merge.
