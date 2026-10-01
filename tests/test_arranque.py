"""Que arrancar el backend no dependa de lo que lleves exportado en la shell.

Esto no prueba lógica de negocio: prueba que las tres fuentes que dicen DÓNDE
está la base de datos digan lo mismo. Son `docker-compose.yml`, `.env.example`
y el valor por defecto de `Config`, y llevaban sin coincidir desde el principio:
el andamio inicial puso `user:password` en `Config`, que no existe en ningún
otro sitio del proyecto. El síntoma era medio minuto de traza de SQLAlchemy
—`password authentication failed for user "user"`— cada vez que alguien corría
`flask db upgrade` en una terminal nueva, y la causa estaba a seis líneas del
principio de un archivo que nadie vuelve a mirar.

Un test en vez de un comentario porque un comentario no se ejecuta.
"""
import os
import pathlib
import re

import yaml

from app.config import DEFAULT_DATABASE_URL, DEFAULT_TEST_DATABASE_URL

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def _usuario_y_clave(uri):
    """('aztec', 'aztec') a partir de postgresql://aztec:aztec@host:5432/base."""
    m = re.match(r"postgresql(?:\+\w+)?://([^:]+):([^@]+)@", uri)
    assert m, f"no reconozco la forma de la URI: {uri}"
    return m.group(1), m.group(2)


def _base(uri):
    return uri.rsplit("/", 1)[-1].split("?")[0]


def test_el_default_de_config_es_el_postgres_de_docker_compose():
    """El valor por defecto tiene que llevar al Postgres que el repo levanta.

    Si no, el camino sin Docker no arranca y el error que da no apunta a esto.
    """
    compose = yaml.safe_load((RAIZ / "docker-compose.yml").read_text())
    entorno = compose["services"]["db"]["environment"]

    usuario, clave = _usuario_y_clave(DEFAULT_DATABASE_URL)

    assert usuario == entorno["POSTGRES_USER"], (
        f"Config usa el usuario '{usuario}' y docker-compose crea "
        f"'{entorno['POSTGRES_USER']}'")
    assert clave == entorno["POSTGRES_PASSWORD"], (
        "Config usa una contraseña distinta de la que crea docker-compose")
    assert _base(DEFAULT_DATABASE_URL) == entorno["POSTGRES_DB"]


def test_env_example_coincide_con_el_default():
    """`.env.example` es lo que se copia a `.env`: no puede contradecir al default."""
    texto = (RAIZ / ".env.example").read_text()
    m = re.search(r"^DATABASE_URL=(.+)$", texto, re.M)
    assert m, ".env.example ya no declara DATABASE_URL"

    assert _usuario_y_clave(m.group(1).strip()) == \
        _usuario_y_clave(DEFAULT_DATABASE_URL)


def test_la_base_de_tests_no_es_la_de_desarrollo():
    """Correr los tests no puede vaciar la base con la que estás trabajando.

    conftest hace `drop_all`, así que esto no es cosmético.
    """
    assert _base(DEFAULT_TEST_DATABASE_URL) != _base(DEFAULT_DATABASE_URL)


def test_el_env_se_carga_al_importar_la_configuracion():
    """Importar `app.config` tiene que haber cargado el `.env` si existe.

    El Flask CLI carga `.env` él solo, pero `pytest`, `seed.py`, `smoke.py` y
    `python run.py` no. Cargarlo en `app/config.py` —que es por donde pasan los
    cinco— es lo que hace que la misma orden se comporte igual venga de donde
    venga. Y tiene que ser al importar, no en `create_app`: las clases leen
    `os.getenv` al definirse.
    """
    import app.config as modulo

    assert "load_dotenv" in pathlib.Path(modulo.__file__).read_text(), (
        "app/config.py ya no carga el .env; vuelve el problema de que "
        "`flask db upgrade` funcione y `pytest` no, o al revés")

    archivo = RAIZ / ".env"
    if not archivo.exists():
        return  # sin .env no hay nada que comprobar, y es un caso legítimo

    for linea in archivo.read_text().splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave = linea.split("=", 1)[0].strip()
        assert clave in os.environ, (
            f"'{clave}' está en .env pero no llegó al entorno: el .env no se "
            "cargó al importar la configuración")
