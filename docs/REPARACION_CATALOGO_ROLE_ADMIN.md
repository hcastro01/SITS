# Reparación conjunta: catálogo de navegación y ROLE_ADMIN

## Alcance cerrado

La única aplicación prevista es `python -m app.cli.repair_catalog_role_admin` desde
`backend`. No llama a `seed_module_catalog`, `seed_security` ni a `app.start`; no
modifica permisos existentes, incluido `ROLE_ADMIN:OFICINA`.

Las definiciones están explícitas en
`app/services/catalog_role_admin_repair.py`, trazadas a
`app/services/security_seed.py:MODULOS_ARQUITECTURA` y no a una ejecución mutable
del seed.

| id_modulo | nombre | permiso | ruta | icono | padre | orden |
| --- | --- | --- | --- | --- | --- | ---: |
| `sits-actividades-tabla` | Tabla de actividades | `ACTIVIDADES` | `/trabajo-social/actividades` | `☷` | `sits-actividades` | 21 |
| `sits-actividades-registrar` | Registrar actividad | `ACTIVIDADES` | `/trabajo-social/actividades/registrar` | `+` | `sits-actividades` | 22 |
| `sits-beneficios` | Beneficios | `BENEFICIOS` | `/trabajo-social/oficina/beneficios` | `★` | `sits-oficina` | 51 |
| `sits-prestamos` | Préstamos | `PRESTAMOS` | `/trabajo-social/oficina/prestamos` | `$` | `sits-oficina` | 53 |
| `sits-seguros` | Seguro | `SEGUROS` | `/trabajo-social/oficina/seguro` | `◈` | `sits-oficina` | 54 |

Cada nodo nuevo tiene `activo=true`, `eliminado=false`, `version=1`. Los únicos
permisos que puede añadir son `ROLE_ADMIN:ACTIVIDADES`,
`ROLE_ADMIN:BENEFICIOS`, `ROLE_ADMIN:PRESTAMOS` y `ROLE_ADMIN:SEGUROS`; cada uno
con los seis derechos en `true`, `activo=true`, `eliminado=false`, `version=1`.

## Comportamiento y protecciones

- El modo predeterminado es `--dry-run`, de sólo lectura: no inserta, actualiza,
  elimina ni escribe auditoría.
- Antes de actuar exige una base SQLite de archivo que ya exista. Rechaza memoria,
  otros motores y rutas inexistentes antes de crear cualquier archivo; muestra la
  ruta resuelta, no una URL con posibles secretos.
- Verifica `ROLE_ADMIN`, `ROLE_ADMIN:OFICINA`, el árbol
  `sits-trabajo-social` → (`sits-actividades`, `sits-oficina`) y su estado activo.
- Detecta conflictos por identificador, ruta y permiso. Una fila objetivo ya
  existente sólo se conserva si coincide con todos los valores funcionales
  definidos arriba; una diferencia aborta sin corrección silenciosa. Para
  `ACTIVIDADES`, que es compartido por padre/hijos, acepta únicamente los cuatro
  propietarios conocidos del catálogo.
- `--apply` vuelve a validar dentro de una única transacción. Catálogo, permisos
  y sus eventos `CREATE` comparten la misma `Session`; `log_change` sólo hace
  `session.add_all`, nunca `commit`.
- Cada aplicación que realmente crea filas genera
  `catalog-role-admin-repair:<UUID>`. El resumen de cambios confirmados se imprime
  sólo después del commit. Una segunda aplicación compatible no crea filas, eventos
  ni un identificador efectivo.

## Reversión controlada

`--revert CORRELATION_ID` toma sólo los IDs `CREATE` de `modulos` y `permisos`
auditados por esa ejecución. Antes de eliminar compara cada fila actual con su
valor inicial y aborta si fue modificada o ya no existe. También aborta ante:

- módulos hijos posteriores (`modulos.padre_id_modulo`), relación con FK;
- cualquier permiso posterior, de otro rol o de otro identificador, que use uno
  de los códigos de módulo creados, relación lógica sin FK.

Primero elimina los permisos creados y después los módulos, sin cascada. Conserva
los eventos `CREATE` originales y añade eventos `DELETE` de reversión en la misma
transacción. Nunca elimina una fila que no pueda demostrarse creada por el
`correlation_id` solicitado.

## Sidebar frente a APIs de Oficina

`ACTIVIDADES`, `BENEFICIOS`, `PRESTAMOS` y `SEGUROS` controlan la visibilidad del
sidebar. Las rutas y los servicios de Oficina siguen autorizando sus APIs con el
permiso transversal `OFICINA`; esta reparación sólo valida que
`ROLE_ADMIN:OFICINA` ya exista, esté activo y tenga los seis derechos. No cambia
`canAccess`, las APIs ni pretende que los cuatro permisos de navegación sustituyan
`OFICINA`. `SEGUROS` es el permiso de sección; `SEGURO` continúa siendo sólo el
código de destino de Formularios.

## Procedimiento futuro autorizado (no ejecutado en producción)

1. En una consola limpia, identificar checkout y base antes de escribir:

   ```bash
   cd /home/hector00999/SITS
   git status --short
   git rev-parse HEAD
   cd backend
   source /home/hector00999/.virtualenvs/sits/bin/activate
   python -m alembic current
   python -m app.cli.production_check
   ```

   Registrar el SHA exacto aprobado y confirmar que `DATABASE_URL` apunta al
   archivo SQLite productivo existente. No usar la ruta local ni ejecutar seeds.

2. Crear un respaldo consistente y verificarlo, antes de cualquier `--apply`:

   ```bash
   python -m app.cli.backup_sqlite --output-dir backups
   sha256sum backups/<archivo-generado>.db
   sqlite3 backups/<archivo-generado>.db 'PRAGMA integrity_check;'
   sqlite3 backups/<archivo-generado>.db 'PRAGMA foreign_key_check;'
   ```

   Conservar nombre, tamaño, SHA-256 y una copia externa. Si `integrity_check`
   no devuelve `ok`, o no se obtiene checksum, detenerse.

3. Con autorización explícita para esa base y SHA, inspeccionar y aplicar:

   ```bash
   python -m app.cli.repair_catalog_role_admin
   python -m app.cli.repair_catalog_role_admin --apply
   ```

   Guardar el `correlation_id` que imprime el segundo comando. Un dry-run que
   anuncie aborto o filas incompatibles no se fuerza ni se corrige con un seed.

4. Abrir una conexión nueva y verificar integridad, relaciones y matriz:

   ```bash
   sqlite3 "$DATABASE_FILE" 'PRAGMA integrity_check;'
   sqlite3 "$DATABASE_FILE" 'PRAGMA foreign_key_check;'
   sqlite3 "$DATABASE_FILE" "SELECT id_modulo, permiso, ruta, padre_id_modulo, activo, eliminado, version FROM modulos WHERE id_modulo IN ('sits-actividades-tabla','sits-actividades-registrar','sits-beneficios','sits-prestamos','sits-seguros') ORDER BY id_modulo;"
   sqlite3 "$DATABASE_FILE" "SELECT id_permiso, modulo, puede_crear, puede_leer, puede_editar, puede_eliminar, puede_sensible, puede_exportar, activo, eliminado, version FROM permisos WHERE id_permiso IN ('ROLE_ADMIN:ACTIVIDADES','ROLE_ADMIN:BENEFICIOS','ROLE_ADMIN:PRESTAMOS','ROLE_ADMIN:SEGUROS','ROLE_ADMIN:OFICINA') ORDER BY id_permiso;"
   sqlite3 "$DATABASE_FILE" "SELECT p.id_permiso, p.modulo FROM permisos p LEFT JOIN modulos m ON m.permiso = p.modulo AND m.activo = 1 AND m.eliminado = 0 WHERE p.modulo IN ('ACTIVIDADES','BENEFICIOS','PRESTAMOS','SEGUROS') AND m.id_modulo IS NULL;"
   ```

   La última consulta es la comprobación explícita de la relación lógica sin FK
   permiso→catálogo. Recargar la matriz de sesión, comprobar Tabla/Registrar de
   Actividades y Beneficios/Préstamos/Seguro, y confirmar que las APIs de Oficina
   siguen exigiendo `OFICINA` y que los demás roles no cambiaron.

5. Sólo si se aprueba la reversión del cambio concreto y todas las validaciones
   previas de seguridad se mantienen:

   ```bash
   python -m app.cli.repair_catalog_role_admin --revert 'catalog-role-admin-repair:<UUID>'
   ```

## Corrección permanente posterior

Para nuevas instalaciones o datos de catálogo futuros, la solución permanente
debe ser una migración de datos versionada, aprobada y con las mismas
precondiciones/abortos explícitos, más pruebas de upgrade y downgrade. No se debe
invocar automáticamente desde el arranque ni ampliar los seeds existentes: esa
decisión requerirá una fase y autorización independientes.
