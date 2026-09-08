"""Regresiones de internacionalización.

Cada test fija un fallo concreto que salió en la primera vuelta del crew.
"""
import pytest

from app.extensions import db
from app.places.models import Place
from app.shared.i18n import apply_translations, parse_accept_language
from app.shared.translations import ENTITY_PLACE
from app.shared.translations_repository import TranslationRepository


def crear_place(pid="p1", nombre="Great Temple", desc="The main temple"):
    place = Place(
        id=pid,
        name=nombre,
        description=desc,
        latitude=19.4361,
        longitude=-99.1356,
        place_type="ruin",
        historical_significance="Heart of the Mexica world",
        estimated_visit_duration=90,
        is_locked=False,
    )
    db.session.add(place)
    db.session.commit()
    return place


# --------------------------------------------------------------------------
# cabecera Accept-Language
# --------------------------------------------------------------------------

@pytest.mark.parametrize("header, esperado", [
    ("es-MX,es;q=0.9,en;q=0.8", "es"),
    ("es-MX", "es"),          # los móviles mandan la etiqueta con región
    ("ES-mx", "es"),          # sin distinguir mayúsculas
    ("en-US", "en"),
    ("fr-FR,de;q=0.8", "en"),  # nada soportado -> el idioma base
    ("*", "en"),
    ("", "en"),
    (None, "en"),
])
def test_locale_por_prefijo_de_dos_letras(header, esperado):
    """Comparar la etiqueta entera dejaba a un iPhone en español viendo inglés."""
    assert parse_accept_language(header) == esperado


def test_el_header_llega_hasta_la_respuesta(client, app):
    crear_place()
    TranslationRepository.upsert(ENTITY_PLACE, "p1", "es", "name", "Templo Mayor")

    r = client.get("/api/places/p1", headers={"Accept-Language": "es-MX"})
    assert r.get_json()["data"]["name"] == "Templo Mayor"

    r = client.get("/api/places/p1")
    assert r.get_json()["data"]["name"] == "Great Temple"


# --------------------------------------------------------------------------
# repositorio
# --------------------------------------------------------------------------

def test_la_carga_masiva_no_pisa_campos(client, app):
    """Una comprensión de diccionario directa se queda solo con el último campo."""
    crear_place("p1")
    crear_place("p2", "Tlatelolco Market", "The great market")
    TranslationRepository.upsert(ENTITY_PLACE, "p1", "es", "name", "Templo Mayor")
    TranslationRepository.upsert(
        ENTITY_PLACE, "p1", "es", "description", "El templo principal"
    )
    TranslationRepository.upsert(
        ENTITY_PLACE, "p2", "es", "name", "Mercado de Tlatelolco"
    )

    resultado = TranslationRepository.find_for_entities(
        ENTITY_PLACE, ["p1", "p2"], "es"
    )

    assert resultado["p1"] == {
        "name": "Templo Mayor", "description": "El templo principal"
    }
    assert resultado["p2"] == {"name": "Mercado de Tlatelolco"}


def test_upsert_es_idempotente(client, app):
    crear_place()
    TranslationRepository.upsert(ENTITY_PLACE, "p1", "es", "name", "Primera")
    TranslationRepository.upsert(ENTITY_PLACE, "p1", "es", "name", "Segunda")

    assert TranslationRepository.find_for_entity(ENTITY_PLACE, "p1", "es") == {
        "name": "Segunda"
    }


def test_sin_ids_no_consulta(client, app):
    assert TranslationRepository.find_for_entities(ENTITY_PLACE, [], "es") == {}


# --------------------------------------------------------------------------
# serialización
# --------------------------------------------------------------------------

def test_lo_no_traducido_cae_al_idioma_base(client, app):
    crear_place()
    TranslationRepository.upsert(ENTITY_PLACE, "p1", "es", "name", "Templo Mayor")

    data = client.get(
        "/api/places/p1", headers={"Accept-Language": "es-MX"}
    ).get_json()["data"]

    assert data["name"] == "Templo Mayor"
    # description no está traducida: conserva el inglés, no se vacía
    assert data["description"] == "The main temple"


def test_el_listado_traduce_con_una_sola_consulta(client, app):
    """Traducir dentro del bucle daría 1 + N consultas en cada listado."""
    for i in range(12):
        crear_place(f"p{i}", f"Site {i}", f"Description {i}")
        TranslationRepository.upsert(ENTITY_PLACE, f"p{i}", "es", "name", f"Sitio {i}")

    items = [{"id": f"p{i}", "name": f"Site {i}"} for i in range(12)]

    llamadas = {"n": 0}
    original = TranslationRepository.find_for_entities

    def contando(*args, **kwargs):
        llamadas["n"] += 1
        return original(*args, **kwargs)

    TranslationRepository.find_for_entities = staticmethod(contando)
    try:
        traducidos = apply_translations(items, ENTITY_PLACE, "es", {"name": "name"})
    finally:
        TranslationRepository.find_for_entities = original

    assert llamadas["n"] == 1
    assert traducidos[3]["name"] == "Sitio 3"


def test_en_el_idioma_base_no_se_consulta_nada(client, app):
    """El inglés vive en la tabla del modelo: pedirlo no toca translations."""
    llamadas = {"n": 0}
    original = TranslationRepository.find_for_entities

    def contando(*args, **kwargs):
        llamadas["n"] += 1
        return original(*args, **kwargs)

    TranslationRepository.find_for_entities = staticmethod(contando)
    try:
        apply_translations(
            [{"id": "p1", "name": "Great Temple"}], ENTITY_PLACE, "en", {"name": "name"}
        )
    finally:
        TranslationRepository.find_for_entities = original

    assert llamadas["n"] == 0
