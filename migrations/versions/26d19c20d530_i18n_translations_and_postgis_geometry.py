"""i18n translations and postgis geometry

Revision ID: 26d19c20d530
Revises: 8cc48c3b2ce4
Create Date: 2026-09-05 04:29:35.870991

Retoques sobre lo que autogeneró Alembic:

1. Se quitó `op.drop_table('spatial_ref_sys')`. Esa tabla es de PostGIS, no del
   proyecto: Alembic la ve como "sobrante" porque no tiene modelo, y borrarla
   deja la extensión inservible. env.py ahora la excluye para que no vuelva a
   colarse en un autogenerate.
2. Se añadió el import de geoalchemy2, que la plantilla no incluye y sin el
   cual la migración revienta con NameError.
3. Se añadió el relleno de places.geom desde latitude/longitude, para que las
   filas que ya existen entren en las consultas espaciales. Sin esto,
   find_nearby las ignora todas: filtra por `geom IS NOT NULL`.
4. Los índices GiST no se declaran aquí: geoalchemy2 los crea junto con la
   columna. Declararlos a mano da "relation already exists".
"""
import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '26d19c20d530'
down_revision = '8cc48c3b2ce4'
branch_labels = None
depends_on = None


def upgrade():
    # ---------------------------------------------------------------- i18n
    op.create_table(
        'translations',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.String(length=36), nullable=False),
        sa.Column('locale', sa.String(length=5), nullable=False),
        sa.Column('field', sa.String(length=50), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint(
            'entity_type', 'entity_id', 'locale', 'field', name='uq_translation'
        ),
    )
    op.create_index(
        'ix_translation_lookup',
        'translations',
        ['entity_type', 'entity_id', 'locale'],
        unique=False,
    )

    # ------------------------------------------------------------- PostGIS
    op.create_table(
        'lake_geometries',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column(
            'geom',
            geoalchemy2.types.Geography(
                geometry_type='POLYGON', srid=4326, dimension=2,
                from_text='ST_GeogFromText', name='geography', nullable=False,
            ),
            nullable=False,
        ),
        sa.Column('year_estimate', sa.Integer(), nullable=True),
        sa.Column('tenochtitlan_name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    op.add_column(
        'places',
        sa.Column(
            'geom',
            geoalchemy2.types.Geography(
                geometry_type='POINT', srid=4326, dimension=2,
                from_text='ST_GeogFromText', name='geography',
            ),
            nullable=True,
        ),
    )

    # Relleno de las filas que ya existen. POINT(longitud latitud), en ese orden.
    op.execute(
        """
        UPDATE places
           SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography
         WHERE latitude IS NOT NULL
           AND longitude IS NOT NULL
        """
    )

    # lake_views guardaba puntos sueltos con un booleano was_water, y con eso no
    # se puede dibujar una orilla. Lo sustituye lake_geometries con polígonos.
    op.drop_table('lake_views')


def downgrade():
    op.create_table(
        'lake_views',
        sa.Column('id', sa.VARCHAR(length=36), autoincrement=False, nullable=False),
        sa.Column('latitude', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
        sa.Column('longitude', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=False),
        sa.Column('was_water', sa.BOOLEAN(), autoincrement=False, nullable=False),
        sa.Column('year_estimate', sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column('description', sa.TEXT(), autoincrement=False, nullable=True),
        sa.Column('tenochtitlan_name', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
        sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('lake_views_pkey')),
    )

    op.drop_column('places', 'geom')
    op.drop_table('lake_geometries')

    op.drop_index('ix_translation_lookup', table_name='translations')
    op.drop_table('translations')
