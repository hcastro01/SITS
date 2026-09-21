# Estado operativo

- Rama: `codex/correos-n8n-production-readiness`; el remoto conserva el checkpoint `209ba75` hasta el próximo push.
- Entorno aislado saludable: backend `18000`, frontend `18081`, SQLite local en revisión `0026_correos_operational_hardening`.
- El lote real `cb189146-a0c4-4628-8231-97b2bb67d5be` está confirmado desde `2026-09-21T05:39:07Z`: 37.591 procesadas, 37.590 importadas, 0 duplicadas, 0 omitidas y 1 error. Incluyó las filas en revisión antes de esta continuación; no se revierte ni se repite.
- Integridad local comprobada: 37.592 correos activos, 0 grupos `MessageId` duplicados, 1 error de importación y 0 seguimientos huérfanos. Dos correos son pruebas n8n locales de esta sesión.
- UI ampliada: historial permite ver errores y confirmar sólo lotes `ANALIZADO`; filtros server-side completos expuestos. Las pruebas de componente pasan 4/4.
- Validación final automatizada: backend 324/324 PASS; frontend 156/156 PASS; TypeScript PASS; build PASS con advertencia existente de chunk de 535.58 kB.
- Producción, merge y workflows reales n8n: no realizados.
