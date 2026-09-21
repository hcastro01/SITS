# Reanudación de Correos y seguimiento

Continúa en `C:\Proyectos`, rama `codex/correos-n8n-production-readiness`. Lee `AGENTS.md`, `docs/CODEX_PRODUCTION_MASTER.md`, `docs/CODEX_STATE.md`, `docs/CODEX_BLOCKERS.md`, `docs/CODEX_DECISIONS.md`, `docs/CODEX_TEST_RESULTS.md` y `docs/CODEX_HANDOFF_CORREOS.md` antes de actuar.

La misión actual SÍ autoriza PR, merge controlado, Vercel, PythonAnywhere, migraciones, importación histórica deduplicada y n8n limitado a ingesta. Conserva los controles de recuperación y no agregues `outputs/`, secretos, bases ni artefactos locales.

La UI ya permite revisar errores y confirmar lotes `ANALIZADO` desde el historial. El lote local `cb189146-a0c4-4628-8231-97b2bb67d5be` ya está `CONFIRMADO` y no se reconfirma: 37.591 procesadas, 37.590 importadas, 0 duplicadas y 1 error. Las 9.314 filas de revisión fueron preservadas como evidencia histórica.

Puertos Compose: fijar `BACKEND_PORT=18000` y `FRONTEND_PORT=18081` en cada terminal. Para Python dentro del contenedor usa `/opt/venv/bin/python`, pues `docker compose exec` no hereda el `PATH` del servicio.

QA visual local está completado; `35860b5` incluye backend 325/325, frontend 158/158, TypeScript/build y smoke Docker PASS. El HEAD `e6bd629` sólo agrega documentación. GitHub, Vercel y PythonAnywhere están autenticados; el backend actual está limpio en `08246df`, preflight PASS y respaldo SQLite validado. PR abierto=0. Crea el PR, revisa el SHA exacto y continúa con la secuencia de `CODEX_PRODUCTION_MASTER.md`; nunca extraigas tokens/cookies ni expongas datos.
