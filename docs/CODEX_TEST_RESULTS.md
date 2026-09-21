# Últimos resultados de pruebas

| Fecha | Comando | Resultado |
| --- | --- | --- |
| 2026-09-21 | `docker compose -p sits-correos-local exec -T backend python -m unittest discover -s tests -p 'test_correos*.py' -v` | 8/8 PASS |
| 2026-09-21 | `cd frontend; npm.cmd exec tsc -- -b` | PASS |
| 2026-09-21 | `cd frontend; npm.cmd run build` | PASS; warning no bloqueante de chunk >500 kB |
| 2026-09-21 | XLSX real vía `http://localhost:18081/api/v1/correos/importar/analizar` | PASS de análisis HTTP; 37,591 filas, sin confirmación E2E |

No se ejecutó la suite backend completa ni una suite Vitest específica de Correos en este checkpoint. No etiquetar el módulo como QA completo.
