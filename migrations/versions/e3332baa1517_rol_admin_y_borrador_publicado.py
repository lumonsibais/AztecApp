"""rol admin y borrador publicado

Revision ID: e3332baa1517
Revises: 405e85a697c4
Create Date: 2026-09-29 21:12:01.890641

Dos columnas NOT NULL sobre tablas con filas, y cada una necesita un valor de
arranque distinto:

  users.is_admin     -> false para todo el mundo. Nadie se convierte en
                        administrador por aplicar una migración; el rol se
                        concede a mano con `flask admin grant`.

  places.is_published -> TRUE para los sitios que ya existen, aunque el modelo
                        tenga default false. Si entrara en false, todo el
                        catálogo desaparecería de la app en el momento del
                        despliegue: lo que ya está en la calle, sigue en la
                        calle. El default false es para los sitios NUEVOS, que
                        nacen en borrador.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3332baa1517'
down_revision = '405e85a697c4'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('places', schema=None) as batch_op:
        # server_default true: rellena las filas existentes en el mismo ALTER.
        batch_op.add_column(sa.Column(
            'is_published', sa.Boolean(),
            nullable=False, server_default=sa.true(),
        ))
        batch_op.create_index(
            batch_op.f('ix_places_is_published'), ['is_published'], unique=False)

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'is_admin', sa.Boolean(),
            nullable=False, server_default=sa.false(),
        ))

    # Los defaults de servidor eran el andamio del relleno. Se retiran para que
    # el esquema coincida con el modelo, donde el default de `is_published` es
    # false: un sitio nuevo nace en borrador y se publica cuando está listo.
    with op.batch_alter_table('places', schema=None) as batch_op:
        batch_op.alter_column('is_published', server_default=None)

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('is_admin', server_default=None)


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('is_admin')

    with op.batch_alter_table('places', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_places_is_published'))
        batch_op.drop_column('is_published')
