"""Tests configuration.

La suite necesita PostgreSQL con PostGIS. Arranca la base con:

    docker compose up -d db

Este archivo se encarga del resto: crea la base de test si no existe y habilita
la extensión antes de crear las tablas.
"""
import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

from app import create_app, db


def _asegurar_base_de_test(uri: str) -> None:
    """Crea la base de datos de test y su extensión PostGIS si hacen falta.

    Se conecta a la base `postgres` de mantenimiento porque CREATE DATABASE no
    puede ejecutarse dentro de una transacción ni desde la base que va a crear.
    """
    url = make_url(uri)
    nombre = url.database

    mantenimiento = sa.create_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    with mantenimiento.connect() as con:
        existe = con.execute(
            sa.text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": nombre}
        ).scalar()
        if not existe:
            con.execute(sa.text(f'CREATE DATABASE "{nombre}"'))
    mantenimiento.dispose()

    destino = sa.create_engine(url, isolation_level="AUTOCOMMIT")
    with destino.connect() as con:
        con.execute(sa.text("CREATE EXTENSION IF NOT EXISTS postgis"))
    destino.dispose()


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app("testing")

    _asegurar_base_de_test(app.config["SQLALCHEMY_DATABASE_URI"])

    with app.app_context():
        # drop_all antes de create_all: si un test anterior se cayó a media
        # ejecución las tablas siguen ahí, y create_all no las tocaría.
        db.drop_all()
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create test CLI runner"""
    return app.test_cli_runner()
