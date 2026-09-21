# Últimos resultados de pruebas

| 2026-09-21 | `docker compose build backend` y `docker compose run --rm backend python -m unittest tests.test_correos` | 7/7 PASS, exit 0; incluye importación de 1.001 filas con persistencia por lotes. |
| 2026-09-21 | PythonAnywhere tras PR #13 y #14 | `production_check` PASS, `PRAGMA integrity_check = ok`, Alembic `0026_correos_operational_hardening (head)` y Reload successful. |
| 2026-09-21 | XLSX histórico en UI productiva | análisis PASS: 37.591 fuente, 28.276 clasificadas, 9.314 revisión, 1 error. Confirmación E2E: PENDIENTE de nueva sesión; no declarar PASS. |

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

Las 156/156 y 324/324 anteriores corresponden al checkpoint `f139c6d`; los totales 158/158 y 325/325 corresponden al código publicado en `35860b5`.

| 2026-09-21 | PythonAnywhere: `python -m app.cli.production_check` sobre el backend `08246df` | PASS: entorno productivo, SQLite persistente, `quick_check`, claves foráneas, revisión Alembic, administración y contraseñas correctas |
| 2026-09-21 | PythonAnywhere: `python -m app.cli.backup_sqlite --output-dir backups` y apertura read-only | PASS: respaldo consistente creado por API SQLite y `PRAGMA integrity_check = ok`; referencia privada fuera de Git |
| 2026-09-21 | PythonAnywhere: `git pull --ff-only`, dependencias fijadas, `app.cli.initialize` y Alembic | PASS: `c857995` desplegado; `0024_contexto_medico_atenciones → 0026_correos_operational_hardening (head)`; catálogos verificados |
| 2026-09-21 | PythonAnywhere: `python -m app.cli.production_check` posterior y Reload | PASS: todos los controles de configuración, SQLite, migraciones y credenciales; `Reload successful` |
| 2026-09-21 | Vercel Production | PASS: deployment `c857995` marcado `Ready` en el proyecto `sits` |
| 2026-09-21 | Dominio habitual: sesión autenticada, Inicio y Correos | PASS: sesión administrativa vigente, ruta de Correos disponible, resumen vacío y filtros visibles; consola sin errores ni advertencias |
| 2026-09-21 | XLSX histórico local en modo solo lectura | PASS para prevalidación: SHA-256 `EB8311DF5F2EE3407A7D09D7B812D1C094B3ECCBDC32CD42A27A973901D86D32`, 30.189.403 bytes, 37.591 filas fuente, 1 ID ausente, 0 IDs duplicados y sin marcadores de prueba inspeccionados |
