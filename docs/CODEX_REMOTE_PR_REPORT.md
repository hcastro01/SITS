# Estado remoto y PR

## Checkpoint posterior (2026-09-21)

- PR #13 `fix(correos): confirmar histórico XLSX por lotes`: checks Vercel observados en éxito; fusionado con merge commit `c15a5ab`.
- PR #14 `fix(correos): reducir E/S de carga histórica`: checks Vercel observados en éxito; fusionado con merge commit `22d09e9`.
- Ambos cambios están desplegados en PythonAnywhere por `git pull --ff-only` y Reload successful. La confirmación real sigue pendiente de una nueva sesión SITS; n8n no fue activado.

- Upstream: `origin` apunta a `https://github.com/hcastro01/SITS.git`.
- La rama remota `codex/correos-n8n-production-readiness` conserva el checkpoint `9feb395d95c152ccaecc28f68e4aa192a8674831`; el código funcional pertenece a `35860b5` y la documentación posterior registra evidencia.
- `gh` está autenticado como `hcastro01` con permiso administrador. El PR #12 se creó contra `master`, se verificó como `CLEAN` y `MERGEABLE`, y se integró con commit de merge `c857995d8203d39e43a0b16e8fbf46a85b3255c9`.
- Checks observados del SHA de PR: `Vercel Preview Comments` y `Vercel` finalizaron `success`. No hubo Actions de backend/frontend remotas; los resultados locales vigentes son 325/325 backend y 158/158 frontend.
- Vercel creó el deployment Production de `c857995` y lo marcó `Ready`. PythonAnywhere aplicó el mismo SHA mediante avance rápido, migró a `0026_correos_operational_hardening` y confirmó la recarga.

## PR #12 integrado

- URL: `https://github.com/hcastro01/SITS/pull/12`.
- Título: `feat(correos): cerrar importación y seguimiento con n8n seguro`.
- Base: `master`; head: `codex/correos-n8n-production-readiness`; SHA de la cabeza al integrar: `9feb395`.
- Método: commit de merge, sin auto-merge, sin squash, sin rebase y sin borrar la rama.
- No crear otro PR para repetir el despliegue de código. Sólo abrir una nueva actualización documental cuando se cierre la importación o se resuelva el bloqueo externo de n8n.
