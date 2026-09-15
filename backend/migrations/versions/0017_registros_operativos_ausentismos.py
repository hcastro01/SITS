"""Vínculo opcional de Ausentismo con su lote de importación verificable."""

from alembic import op
import sqlalchemy as sa


revision = "0017_registros_operativos_ausentismos"
down_revision = "0016_lotes_importacion_ausentismo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # batch_alter_table conserva la compatibilidad de SQLite, que no permite ADD CONSTRAINT.
    with op.batch_alter_table("ausentismos") as batch:
        batch.add_column(sa.Column("lote_id", sa.String(), nullable=True))
        batch.create_foreign_key(
            "fk_ausentismos_lote_id_lotes_importacion_ausentismo",
            "lotes_importacion_ausentismo", ["lote_id"], ["id_lote"],
        )
        batch.create_index("ix_ausentismos_lote_id", ["lote_id"])


def downgrade() -> None:
    with op.batch_alter_table("ausentismos") as batch:
        batch.drop_index("ix_ausentismos_lote_id")
        batch.drop_constraint("fk_ausentismos_lote_id_lotes_importacion_ausentismo", type_="foreignkey")
        batch.drop_column("lote_id")
