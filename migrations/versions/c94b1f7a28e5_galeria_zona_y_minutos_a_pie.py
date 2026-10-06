"""galería de fotos, zona del tour y minutos a pie

Revision ID: c94b1f7a28e5
Revises: a71f4c8d2e90
Create Date: 2026-10-01 21:40:55.117204

Tres huecos que destapó el diseño de Figma al leerlo contra el contrato. Los
tres son aditivos y ninguno toca lo que ya existe:

  place_images                 el hero de la ficha es un CARRUSEL y el contrato
                               daba una sola `imageUrl`. Tabla y no un array en
                               una columna porque cada foto lleva su pie y su
                               orden: eso son campos, no una cadena dentro de
                               otra.

  tours.neighborhood           la zona del recorrido ("Centro Histórico"), que
                               la cabecera del diseño enseña junto a la duración.

  tour_stops.walk_minutes_to_next
                               los minutos andando hasta la parada siguiente,
                               que el diseño pinta en el conector entre dos
                               tarjetas. Sin esto, el conector no se puede
                               dibujar.

Todo nullable: no hay relleno que hacer y las filas existentes no se enteran.
`imageUrl` se queda donde estaba —está en el contrato congelado— y pasa a ser la
portada; la galería se sirve aparte.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c94b1f7a28e5'
down_revision = 'a71f4c8d2e90'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'place_images',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('place_id', sa.String(length=36), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('caption', sa.String(length=255), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['place_id'], ['places.id']),
        sa.PrimaryKeyConstraint('id'),
        # Dos fotos en la misma posición saldrían en orden arbitrario, que es
        # justo lo que la posición existe para evitar.
        sa.UniqueConstraint('place_id', 'position', name='uq_place_image_pos'),
    )
    with op.batch_alter_table('place_images', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_place_images_place_id'), ['place_id'], unique=False)

    with op.batch_alter_table('tours', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('neighborhood', sa.String(length=120), nullable=True))

    with op.batch_alter_table('tour_stops', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('walk_minutes_to_next', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('tour_stops', schema=None) as batch_op:
        batch_op.drop_column('walk_minutes_to_next')

    with op.batch_alter_table('tours', schema=None) as batch_op:
        batch_op.drop_column('neighborhood')

    with op.batch_alter_table('place_images', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_place_images_place_id'))
    op.drop_table('place_images')
