# Misión vigente: Correos y seguimiento

## Objetivo autorizado

Cerrar de forma local y verificable `Trabajo Social → Correos y seguimiento`: análisis XLSX, confirmación conservadora, persistencia, trazabilidad por lote y error, consulta, filtros, detalle, dashboard, endpoint n8n de mínimo privilegio, pruebas, documentación y preparación de PR contra `master`.

La fuente de autoridad es `C:\Users\HCast\Downloads\CODEX_MAESTRO_UNIFICADO_CORREOS.md`, autorizada explícitamente por el usuario el 2026-09-21. Este documento conserva sus decisiones operativas sin incluir secretos ni datos privados.

## Límites invariables

- Sólo Docker y SQLite locales del proyecto `sits-correos-local`.
- No merge ni auto-merge, no despliegue, no promoción, no producción y no workflows reales de n8n.
- No incluir `outputs/`, XLSX reales, bases, `.env`, tokens, cookies, logs ni capturas sensibles en Git.
- No reset, clean, borrado de volúmenes ni modificación directa del estado de un lote para simular éxito.
- La prueba del XLSX real importa sólo filas `CLASIFICADO`; revisión y error se conservan recuperables. Es un criterio conservador de QA, no una regla empresarial nueva.

## Estado de partida comprobado

- Rama: `codex/correos-n8n-production-readiness`.
- Checkpoint de partida: `209ba756bc0fefd69c6773d9f53a43641fedf06e` (`209ba75`), presente y publicado en `origin`.
- Entorno: frontend `http://localhost:18081`, backend `http://localhost:18000`.
- Lote real pendiente informado: `cb189146-a0c4-4628-8231-97b2bb67d5be`.
- Análisis histórico: 37.591 filas totales/procesadas, 28.276 clasificadas, 9.314 en revisión, 1 error, 0 omitidas. Esos valores describen análisis, no importación.

## Secuencia de cierre

1. Mantener respaldo consistente local antes de cualquier confirmación.
2. Ejecutar navegador real local: login, historial, errores, confirmación de sólo clasificados, listado, filtros, detalle y recarga. No sacar capturas con datos reales.
3. Verificar SQL de lotes, orígenes, referencias e identidades duplicadas.
4. Validar n8n sólo contra endpoint local con token aleatorio efímero no impreso: 401 sin/incorrecto, 201 válido, 200 reintento y una sola identidad.
5. Ejecutar migraciones desechables, suites backend/frontend, TypeScript, build, smoke Docker y auditoría de diff.
6. Actualizar estado, informes y, tras validación final, commit, push y PR contra `master` si la autenticación remota lo permite. Nunca fusionar.

## Evidencia inicial de recuperación

Se creó un respaldo consistente de la SQLite local en el volumen aislado antes de E2E. No se versiona. Su hash SHA-256 está registrado únicamente en el contexto operativo de esta sesión, no en documentación pública.
