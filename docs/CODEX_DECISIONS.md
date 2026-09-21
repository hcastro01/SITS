# Decisiones de Correos

- `MessageId` se conserva como identificador natural (`id_externo_correo`) con constraint único; reintentos son 200 idempotentes, no una duplicación ni actualización silenciosa.
- n8n usa Bearer token de entorno y comparación de tiempo constante. Es una ruta dedicada de mínimo privilegio, no una cookie simulada ni un permiso administrativo.
- Las filas XLSX fallidas se trazan individualmente; sólo errores estructurales del libro invalidan el análisis completo.
- Fechas sin zona se interpretan en `America/Guayaquil`; los valores persistidos incluyen offset.
- Se elevó el límite coherentemente a 50 MiB en frontend, Nginx y backend, sin permitir tamaño ilimitado.
- El cuerpo del correo se renderiza como texto; nunca se inyecta HTML del correo en el DOM.
- Las filas `REVISION` no se incluirán en futuras pruebas de confirmación: es el criterio conservador local. El lote histórico ya fue confirmado antes de esta continuación con 37.590 registros; no se revierte ni se altera por SQL.
- Los permisos `sensitive` de `CORREOS` no se otorgan automáticamente a roles no administradores. El detalle y los seguimientos requieren una concesión explícita, coherente con la matriz de seguridad existente.
- El modelo ORM replica los índices realmente creados por 0025/0026. Se corrigió el modelo, no las migraciones publicadas.
- El formulario de acceso consulta `GET /api/v1/auth/requisitos`: en `development_email` permite contraseña vacía; ante error conserva la exigencia estricta. El backend continúa imponiendo contraseña cuando `auth_mode=password`.
- El seguimiento captura la referencia del formulario antes de `await`; así un `201 Created` no se convierte en un falso error al ejecutar el reset del formulario.
- La exportación de Correos reutiliza la misma selección del listado y sólo elimina la paginación. Un XLSX no puede incluir fórmulas de datos externos: los textos que comienzan con prefijos ejecutables se codifican con un U+200B reversible, explicado en `Información_exportación`.
- Cuerpo y seguimientos se consideran contenido sensible de Correos. La pantalla no ofrece esas opciones sin `CORREOS:sensitive` y el endpoint las rechaza aunque se manipule el JSON.
