"""cobro desde las tiendas

Revision ID: a71f4c8d2e90
Revises: e3332baa1517
Create Date: 2026-09-29 22:40:12.004311

El desbloqueo se cobra desde la App Store y desde Google Play. Eso cambia qué
se guarda de cada compra:

  external_id -> de VARCHAR(255) a TEXT. No es cosmético. El purchaseToken de
                 Google Play ronda los 350 caracteres, así que la primera compra
                 real en Android habría muerto con "value too long for type
                 character varying(255)" al insertar. Ampliar una columna de
                 texto en PostgreSQL no reescribe la tabla ni bloquea lecturas.

  original_transaction_id -> la referencia que traen las notificaciones de
                 reembolso (originalTransactionId de Apple, orderId de Google),
                 que no siempre coincide con la de la transacción concreta. Sin
                 esto, una notificación de reembolso no se puede casar con la
                 compra que hay que revocar.

  store_environment -> Sandbox o Production.

  acknowledged_at -> Google reembolsa automáticamente toda compra que no se
                 acuse en 3 días. Esta columna es lo que permite barrer las que
                 se quedaron sin acusar porque la llamada de acuse falló.

Todas nuevas y NULL: no hay relleno que hacer ni riesgo sobre las filas que ya
estén. La restricción única (provider, external_id) se conserva tal cual; el
cambio de tipo no la toca porque PostgreSQL reconstruye su índice solo.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a71f4c8d2e90'
down_revision = 'e3332baa1517'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('purchases', schema=None) as batch_op:
        batch_op.alter_column(
            'external_id',
            existing_type=sa.String(length=255),
            type_=sa.Text(),
            existing_nullable=True,
        )
        batch_op.add_column(
            sa.Column('original_transaction_id', sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column('store_environment', sa.String(length=20), nullable=True))
        batch_op.add_column(
            sa.Column('acknowledged_at', sa.DateTime(), nullable=True))
        batch_op.create_index(
            batch_op.f('ix_purchases_original_transaction_id'),
            ['original_transaction_id'], unique=False)


def downgrade():
    with op.batch_alter_table('purchases', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_purchases_original_transaction_id'))
        batch_op.drop_column('acknowledged_at')
        batch_op.drop_column('store_environment')
        batch_op.drop_column('original_transaction_id')
        # Volver a 255 TRUNCA: un purchaseToken de Google no cabe y PostgreSQL
        # aborta el ALTER en vez de cortarlo, que es lo correcto. Si esta bajada
        # falla es porque ya hay compras de Android registradas, y entonces la
        # bajada no se debe forzar: se arregla hacia delante.
        batch_op.alter_column(
            'external_id',
            existing_type=sa.Text(),
            type_=sa.String(length=255),
            existing_nullable=True,
        )
