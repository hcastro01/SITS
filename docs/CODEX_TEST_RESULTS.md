# Últimos resultados de pruebas

| Fecha | Entorno y comando | Resultado |
| --- | --- | --- |
| 2026-09-21 | `docker compose -p sits-correos-local exec -T backend /opt/venv/bin/python -m unittest discover -s tests -v` | 324/324 PASS, 239.796 s, exit 0 |
| 2026-09-21 | `frontend: npm.cmd test -- --pool=forks --maxWorkers=1 --reporter=verbose` | 156/156 PASS, 25 archivos, 161.65 s, exit 0 |
| 2026-09-21 | `frontend: npm.cmd test -- ... CorreosDashboardPage.test.tsx` | 4/4 PASS, exit 0 |
| 2026-09-21 | `frontend: npm.cmd exec tsc -- -b` | PASS, exit 0 |
| 2026-09-21 | `frontend: npm.cmd run build` | PASS, exit 0; advertencia no bloqueante de chunk JS 535.58 kB |
| 2026-09-21 | Alembic desechable `0024 → 0025 → 0026 → 0024 → 0026` | PASS; tablas e índice de errores verificados |
| 2026-09-21 | HTTP n8n local, token efímero en memoria | sin token 401; incorrecto 401; válido 201; replay 200; inválido 422; endpoint ajeno 401 |
| 2026-09-21 | SQL local | 0 grupos MessageId duplicados; 0 seguimientos huérfanos |
| 2026-09-21 | QA visual autenticado en navegador integrado aislado | PASS: login, navegación, historial/error, dashboard, filtros combinados, orden, vacío, paginación, detalle, seguimiento, recarga y viewport 390×844; consola sin errores/advertencias |
| 2026-09-21 | Fixture XLSX sintético desde UI | PASS: 3 procesadas; 1 clasificada importada; 1 revisión preservada; 1 error persistido |
| 2026-09-21 | `docker compose -p sits-correos-local exec -T -w /app backend /opt/venv/bin/python -m unittest discover -s tests -v` | 325/325 PASS, 163.680 s, exit 0 |
| 2026-09-21 | `frontend: npm.cmd test -- --pool=forks --maxWorkers=1 --reporter=verbose` | 158/158 PASS, 25 archivos, 103.43 s, exit 0 |
| 2026-09-21 | `frontend: npm.cmd exec tsc -- -b` y `npm.cmd run build` | PASS, exit 0; advertencia no bloqueante de chunk JS 535.81 kB |

Las 156/156 y 324/324 anteriores corresponden al checkpoint `f139c6d`; los totales 158/158 y 325/325 corresponden al árbol de código posterior a las correcciones de QA, antes del commit final.
