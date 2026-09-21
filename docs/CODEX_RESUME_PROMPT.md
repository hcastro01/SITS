# Reanudación de Correos y seguimiento

Continúa en `C:\Proyectos`, rama `codex/correos-n8n-production-readiness`. Lee `AGENTS.md`, `docs/CODEX_MASTER_CORREOS.md`, `docs/CODEX_STATE.md`, `docs/CODEX_BLOCKERS.md`, `docs/CODEX_DECISIONS.md`, `docs/CODEX_TEST_RESULTS.md` y `docs/CODEX_HANDOFF_CORREOS.md` antes de actuar.

Conserva el límite: sólo entorno `sits-correos-local`, sin merge, despliegue, producción ni workflows reales n8n. No agregues archivos de `outputs/`, secretos, bases ni artefactos locales.

La UI ya permite revisar errores y confirmar lotes `ANALIZADO` desde el historial. El lote local `cb189146-a0c4-4628-8231-97b2bb67d5be` ya está `CONFIRMADO` y no se reconfirma: 37.591 procesadas, 37.590 importadas, 0 duplicadas y 1 error. Las 9.314 filas de revisión fueron preservadas como evidencia histórica.

Puertos Compose: fijar `BACKEND_PORT=18000` y `FRONTEND_PORT=18081` en cada terminal. Para Python dentro del contenedor usa `/opt/venv/bin/python`, pues `docker compose exec` no hereda el `PATH` del servicio.

QA visual está completado en navegador integrado aislado; un fixture sintético verificó el flujo UI sin modificar el lote real. Las últimas validaciones de código no comprometido son backend 325/325, frontend 158/158, TypeScript/build y smoke Docker PASS. El pendiente ejecutable es el checkpoint selectivo/push y luego el PR: `gh` no tiene sesión, PR abierto=0. Nunca extraigas tokens/cookies, no hagas merge ni producción.
