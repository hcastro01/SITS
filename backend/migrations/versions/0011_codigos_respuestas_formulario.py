"""Código funcional correlativo para respuestas definitivas de formularios.

Revision ID: 0011_codigos_respuesta
Revises: 0010_formularios_dinamicos
"""

from alembic import op
import sqlalchemy as sa

revision = "0011_codigos_respuesta"
down_revision = "0010_formularios_dinamicos"
branch_labels = None
depends_on = None

PREFIX = "TTHH_RRLL_"
MAX_SEQUENCE = 99_999_999_999


def _format_code(sequence: int) -> str:
    return f"{PREFIX}{sequence:011d}"


def upgrade() -> None:
    op.create_table(
        "secuencias_respuestas_formulario",
        sa.Column("nombre", sa.String(), primary_key=True),
        sa.Column("ultimo_numero", sa.Integer(), nullable=False, server_default="0"),
        sa.CheckConstraint("ultimo_numero >= 0", name="secuencia_respuesta_non_negative"),
        sa.CheckConstraint("ultimo_numero <= 99999999999", name="secuencia_respuesta_max_11_digits"),
    )
    op.add_column("envios_formulario", sa.Column("numero_secuencial", sa.Integer(), nullable=True))
    op.add_column("envios_formulario", sa.Column("codigo_respuesta", sa.String(length=21), nullable=True))
    op.create_index("ux_envios_formulario_numero_secuencial", "envios_formulario", ["numero_secuencial"], unique=True)
    op.create_index("ux_envios_formulario_codigo_respuesta", "envios_formulario", ["codigo_respuesta"], unique=True)

    bind = op.get_bind()
    rows = bind.execute(sa.text(
        "SELECT id_respuesta FROM envios_formulario "
        "WHERE UPPER(TRIM(COALESCE(estado, ''))) = 'REGISTRADO' "
        "ORDER BY COALESCE(fecha_creacion, fecha_respuesta, ''), id_respuesta"
    )).all()
    if len(rows) > MAX_SEQUENCE:
        raise RuntimeError("Las respuestas históricas superan la capacidad del correlativo de 11 dígitos.")
    for sequence, row in enumerate(rows, start=1):
        bind.execute(sa.text(
            "UPDATE envios_formulario SET numero_secuencial = :sequence, codigo_respuesta = :code "
            "WHERE id_respuesta = :response_id"
        ), {"sequence": sequence, "code": _format_code(sequence), "response_id": row.id_respuesta})
    bind.execute(sa.text(
        "INSERT INTO secuencias_respuestas_formulario (nombre, ultimo_numero) VALUES ('GLOBAL', :last_number)"
    ), {"last_number": len(rows)})


def downgrade() -> None:
    op.drop_index("ux_envios_formulario_codigo_respuesta", table_name="envios_formulario")
    op.drop_index("ux_envios_formulario_numero_secuencial", table_name="envios_formulario")
    op.drop_column("envios_formulario", "codigo_respuesta")
    op.drop_column("envios_formulario", "numero_secuencial")
    op.drop_table("secuencias_respuestas_formulario")
