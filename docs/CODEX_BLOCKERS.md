# Bloqueos

## Resolubles por Codex

- La confirmación E2E del XLSX quedó pendiente porque una nueva sesión PowerShell no reenvió la cookie de SITS. Usar un navegador real o depurar el cliente de prueba sin exponer tokens.
- Faltan pruebas frontend específicas y la repetición de migración downgrade/upgrade limpia.
- Falta mostrar el detalle de errores de lote en la UI, aunque el endpoint está implementado.

## Requieren intervención humana

- Configurar una credencial real de `N8N_SITS_API_KEY` en el almacenamiento seguro de n8n y en el entorno destino.
- Autorizar cualquier configuración de workflow n8n real, push, revisión/merge o despliegue.
- No hay bloqueo humano para seguir pruebas locales aisladas.
