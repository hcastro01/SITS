# Estado remoto y PR

- Upstream: `origin` apunta a `https://github.com/hcastro01/SITS.git`.
- La rama remota `codex/correos-n8n-production-readiness` está comprobada en `35860b5343458f2a7c93c1753f186c505fd97f42`; coincide con HEAD local y upstream.
- Consulta pública GitHub: no existe PR contra `master` para esa rama.
- `gh` está instalado, pero no autenticado; no se creó PR. La consulta pública devolvió 0 PR abiertos contra `master` para la rama.
- El checkpoint incluye QA visual y correcciones de login/seguimiento. Si se crea el PR, hay que reconsultar sus checks para `35860b5`; no usar resultados de `d687cbe` como CI del nuevo SHA.

## PR preparado, no creado

- Título: `feat(correos): cerrar importación y seguimiento con n8n seguro`.
- Base: `master`; head: `codex/correos-n8n-production-readiness`.
- Descripción: incluye migraciones `0025`/`0026`, importación XLSX trazable y deduplicada, dashboard/filtros/detalle/seguimientos, endpoint n8n Bearer idempotente validado sólo localmente, lote histórico comprobado, fixture UI sintético y QA visual. Señalar explícitamente: sin workflow n8n real, sin merge, sin despliegue ni cambios de producción.
- Procedimiento humano mínimo: ejecutar `gh auth login --web --hostname github.com`, crear el PR contra `master` con la rama anterior y revisar los checks asociados a `35860b5`. No usar tokens/cookies extraídos ni force-push.
- No hubo merge ni auto-merge.
