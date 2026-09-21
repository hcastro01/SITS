# Decisiones de Correos

- `MessageId` se conserva como identificador natural (`id_externo_correo`) con constraint único; reintentos son 200 idempotentes, no una duplicación ni actualización silenciosa.
- n8n usa Bearer token de entorno y comparación de tiempo constante. Es una ruta dedicada de mínimo privilegio, no una cookie simulada ni un permiso administrativo.
- Las filas XLSX fallidas se trazan individualmente; sólo errores estructurales del libro invalidan el análisis completo.
- Fechas sin zona se interpretan en `America/Guayaquil`; los valores persistidos incluyen offset.
- Se elevó el límite coherentemente a 50 MiB en frontend, Nginx y backend, sin permitir tamaño ilimitado.
- El cuerpo del correo se renderiza como texto; nunca se inyecta HTML del correo en el DOM.
