# Reanudación de Correos y seguimiento

Continúa en `C:\Proyectos`, rama `codex/correos-n8n-production-readiness`. Lee `AGENTS.md`, `docs/CODEX_PRODUCTION_MASTER.md`, `docs/CODEX_STATE.md`, `docs/CODEX_BLOCKERS.md`, `docs/CODEX_DECISIONS.md`, `docs/CODEX_TEST_RESULTS.md` y `docs/CODEX_HANDOFF_CORREOS.md` antes de actuar.

La misión actual SÍ autoriza PR, merge controlado, Vercel, PythonAnywhere, migraciones, importación histórica deduplicada y n8n limitado a ingesta. Conserva los controles de recuperación y no agregues `outputs/`, secretos, bases ni artefactos locales.

La UI ya permite revisar errores y confirmar lotes `ANALIZADO` desde el historial. El lote local `cb189146-a0c4-4628-8231-97b2bb67d5be` ya está `CONFIRMADO` y no se reconfirma: 37.591 procesadas, 37.590 importadas, 0 duplicadas y 1 error. Las 9.314 filas de revisión fueron preservadas como evidencia histórica.

Puertos Compose: fijar `BACKEND_PORT=18000` y `FRONTEND_PORT=18081` en cada terminal. Para Python dentro del contenedor usa `/opt/venv/bin/python`, pues `docker compose exec` no hereda el `PATH` del servicio.

QA visual local está completado; `35860b5` incluye backend 325/325, frontend 158/158, TypeScript/build y smoke Docker PASS. El PR #12 fue integrado mediante `c857995`; PythonAnywhere avanzó por fast-forward, migró a `0026_correos_operational_hardening`, pasó `production_check` y se recargó correctamente. Vercel publicó `c857995` en Production Ready y el dominio habitual cargó con sesión administrativa y el módulo Correos.

No repetir pruebas ni despliegues ya comprobados. El XLSX histórico prevalidado pesa 30.189.403 bytes, tiene 37.591 filas fuente, 1 ID ausente y 0 duplicados. La carga no empezó porque la extensión de Chrome bloqueó el acceso a archivos antes de transmitirlo. Tras habilitar `Allow access to file URLs` en la extensión ChatGPT de Chrome, analiza el archivo una vez, revisa el lote y confirma la importación incluyendo o excluyendo revisión según el resultado real. Luego verifica conteos, deduplicación, paginación, filtros, detalle y un seguimiento en el dominio productivo. n8n sigue bloqueado hasta que haya una instancia autenticada y un flujo exclusivamente de ingesta; nunca actives un flujo que opere el buzón ni reveles la clave ya configurada.
