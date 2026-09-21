# Reanudación de Correos y seguimiento

Continúa en `C:\Proyectos`, rama `codex/correos-n8n-production-readiness`. Lee `AGENTS.md`, `docs/CODEX_MASTER_CORREOS.md`, `docs/CODEX_STATE.md`, `docs/CODEX_BLOCKERS.md`, `docs/CODEX_DECISIONS.md`, `docs/CODEX_TEST_RESULTS.md` y `docs/CODEX_HANDOFF_CORREOS.md` antes de actuar.

Conserva el límite: sólo entorno `sits-correos-local`, sin merge, despliegue, producción ni workflows reales n8n. No agregues archivos de `outputs/`, secretos, bases ni artefactos locales.

La UI ya permite revisar errores y confirmar lotes `ANALIZADO` desde el historial. El objetivo E2E prioritario es el lote local `cb189146-a0c4-4628-8231-97b2bb67d5be`, seleccionando **Sólo clasificados**. Verifica primero el lote y los conteos; no incluyas los 9.314 registros en revisión.

Puertos Compose: fijar `BACKEND_PORT=18000` y `FRONTEND_PORT=18081` en cada terminal. Para Python dentro del contenedor usa `/opt/venv/bin/python`, pues `docker compose exec` no hereda el `PATH` del servicio.

Después de la confirmación, registrar conteos antes/después, verificar `GROUP BY id_externo_correo HAVING COUNT(*) > 1`, lotes, errores, origen y referencias. Validar UI mediante navegador real, n8n local con token efímero no impreso, suites completas y PR seguro. Actualizar los documentos de estado tras cada hito.
