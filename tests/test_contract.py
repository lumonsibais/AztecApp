"""Conformidad: el spec contra el servidor de verdad.

Un OpenAPI escrito a mano y nunca contrastado es documentación optimista. Este
archivo recorre CADA operación del spec, la llama contra la base sembrada y
valida la respuesta con jsonschema.

Si alguien cambia un `to_dict()` y no toca el spec, esto se pone rojo. Ese es
todo el propósito: que el contrato no pueda mentirle al frontend sin que nos
enteremos antes de que Flutter se estrelle.

Dos cosas que se comprueban aparte de la forma:

  - COBERTURA: que no haya rutas de la app fuera del spec. Un endpoint sin
    documentar es un endpoint que el frontend no sabe que existe.
  - El sobre {success, data}, que es lo primero que toca cualquier cliente.
"""
import copy
import json
import pathlib
import re

import pytest
from jsonschema import Draft202012Validator

from app.extensions import db
from app.historical.models import HistoricalContent, Timeline
from app.historical.services import LakeViewService
from app.places.models import Place
from app.shared.constants import (
    CURATION_MUST_SEE, CURATION_QUICK_STOP, ERA_HISTORIC_YEAR,
    SURFACE_LAND, SURFACE_WATER,
)
from app.tours.models import Tour, TourStop

SPEC = json.loads((pathlib.Path(__file__).parent.parent / "openapi.json").read_text())


def _a_json_schema(nodo):
    """Traduce el dialecto de OpenAPI 3.0 al de JSON Schema.

    OpenAPI 3.0 marca los nulos con `nullable: true` junto a un `type` simple;
    JSON Schema no conoce esa palabra y solo acepta `type: [X, "null"]`. Sin
    esta traducción, cualquier campo que el servidor manda como null —una
    imagen que falta, la distancia sin coordenadas, `isSaved` sin sesión— daría
    un fallo falso.
    """
    if isinstance(nodo, list):
        return [_a_json_schema(x) for x in nodo]
    if not isinstance(nodo, dict):
        return nodo

    salida = {k: _a_json_schema(v) for k, v in nodo.items()}

    if salida.pop("nullable", False):
        tipo = salida.get("type")
        if isinstance(tipo, str):
            salida["type"] = [tipo, "null"]
        elif isinstance(tipo, list) and "null" not in tipo:
            salida["type"] = tipo + ["null"]
        elif tipo is None:
            # nullable sobre un $ref o un allOf: se relaja a "o null".
            if "$ref" in salida or "allOf" in salida:
                salida = {"anyOf": [salida, {"type": "null"}]}

    return salida


SPEC_JS = _a_json_schema(copy.deepcopy(SPEC))


def _normaliza_ruta(regla_flask: str) -> str:
    """`/api/places/<place_id>` -> `/api/places/{place_id}`.

    Flask y OpenAPI escriben los parámetros de ruta distinto. Comparar las
    cadenas tal cual daba once rutas "sin documentar" que sí lo estaban.
    """
    return re.sub(r"<(?:[^:<>]+:)?([^<>]+)>", r"{\1}", regla_flask)


# ---------------------------------------------------------------------------
# datos: un mundo pequeño pero completo, para que ninguna rama quede sin ver
# ---------------------------------------------------------------------------

@pytest.fixture
def mundo(client, app):
    """Siembra lo mínimo para que las 36 operaciones devuelvan algo real."""
    app.config["PAYMENTS_ALLOW_UNVERIFIED"] = True

    abierto = Place(
        id="templo-mayor", name="Templo Mayor Remains",
        tagline="The sacred heart of the empire",
        description="What is left of the great temple.",
        latitude=19.4361, longitude=-99.1356, neighborhood="Centro",
        place_type="ruin", curation=CURATION_MUST_SEE, editorial_rating=4.5,
        historical_significance="Epicentre of Aztec life.",
        why_visit="Start here.", how_to_get_there="Metro Zócalo, line 2.",
        estimated_visit_duration=90, visit_duration_text="1-3 hours",
        opening_hours="Tue-Sun, 9-17", entry_fee_mxn=95, entry_fee_usd=5.5,
        entry_fee_text="95 MXN", is_free_entry=False, is_outdoor=True,
        archaeological=True, tenochtitlan_name="Huei Teocalli",
        safety_recommendations="Busy area, watch your belongings.",
        has_bathrooms=True, is_locked=False,
    )
    cerrado = Place(
        id="museo", name="National Museum of Anthropology",
        tagline="The 24-ton Sun Stone", description="Paid body.",
        latitude=19.4260, longitude=-99.1863, neighborhood="Chapultepec",
        place_type="museum", curation=CURATION_QUICK_STOP, editorial_rating=5.0,
        historical_significance="Houses the Sun Stone.",
        why_visit="Paid reason.", how_to_get_there="Metro Auditorio, line 7.",
        estimated_visit_duration=180, visit_duration_text="2-4 hours",
        opening_hours="Tue-Sun, 9-18", entry_fee_mxn=95, entry_fee_usd=5.5,
        is_free_entry=False, is_locked=True,
    )
    db.session.add_all([abierto, cerrado])

    tour = Tour(
        id="ruta", title="Unearth Tenochtitlan", description="Teaser line.",
        content_description="The full script.", status="published",
        is_free=False, is_locked=True, estimated_duration=120,
        duration_text="1 - 2 hours", difficulty_level="easy",
        total_distance=2.4, has_entry_fees=False, editorial_rating=4.8,
    )
    db.session.add(tour)
    db.session.flush()
    db.session.add_all([
        TourStop(id="s0", tour_id="ruta", place_id="templo-mayor", position=0,
                 audio_url="https://cdn.example/a.mp3", audio_duration_seconds=240,
                 transition_text="Next, north to the market."),
        TourStop(id="s1", tour_id="ruta", place_id="museo", position=1,
                 audio_url="https://cdn.example/b.mp3", audio_duration_seconds=180),
    ])

    db.session.add(Timeline(id="cron", title="Mexica chronology",
                            description="From founding to fall.", sort_order=0))
    db.session.add_all([
        HistoricalContent(
            id="founding", title="The eagle and the cactus",
            description="Where the Mexica were told to build.",
            content_type="text", text_content="Long paid body.",
            timeline_id="cron", sort_order=0, topic="Foundation myth",
            era="Aztec Empire (1345-1521)", reading_time_minutes=4,
            place_id="templo-mayor", author="AztecApp editorial", verified=True,
            is_locked=False,
        ),
        HistoricalContent(
            id="fall", title="The fall of Tenochtitlan",
            description="1521.", content_type="text",
            text_content="Paid body.", timeline_id="cron", sort_order=1,
            topic="Conquest", era="Aztec Empire (1345-1521)",
            reading_time_minutes=8, is_locked=True,
        ),
    ])
    db.session.commit()

    for nombre, superficie, caja in [
        ("Lake Texcoco", SURFACE_WATER, (-99.17, 19.39, -99.04, 19.49)),
        ("Island of Tenochtitlan", SURFACE_LAND, (-99.145, 19.425, -99.124, 19.445)),
    ]:
        lon0, lat0, lon1, lat1 = caja
        LakeViewService.create_lake_geometry(
            name=nombre,
            geojson_polygon={"type": "Polygon", "coordinates": [[
                [lon0, lat0], [lon0, lat1], [lon1, lat1], [lon1, lat0], [lon0, lat0]
            ]]},
            year_estimate=ERA_HISTORIC_YEAR,
            surface_type=superficie,
            tenochtitlan_name=nombre,
        )

    r = client.post("/api/users/register",
                    json={"email": "contract@az.com", "password": "testpassword123"})
    tokens = r.get_json()["data"]
    cabecera = {"Authorization": "Bearer " + tokens["accessToken"]}

    client.post("/api/payments/confirm", headers=cabecera,
                json={"provider": "stripe", "externalId": "pi_contract"})
    client.post("/api/places/templo-mayor/save", headers=cabecera)
    client.post("/api/historical/content/founding/read", headers=cabecera)
    client.post("/api/tours/ruta/start", headers=cabecera)

    return {
        "auth": cabecera,
        "refresh": {"Authorization": "Bearer " + tokens["refreshToken"]},
        "userId": tokens["user"]["id"],
    }


# ---------------------------------------------------------------------------
# validación contra el spec
# ---------------------------------------------------------------------------

def validador(esquema):
    """Valida contra un fragmento del spec, resolviendo sus $ref internos.

    Los schemas de respuesta son `{"$ref": "#/components/schemas/..."}`, y esa
    referencia solo se resuelve si el validador tiene delante el documento
    ENTERO. Así que se le pasa el documento con el $ref pegado en la raíz: en
    JSON Schema 2020-12 las claves hermanas de un $ref conviven con él, y las
    del documento OpenAPI (`openapi`, `paths`, `info`) no son palabras clave de
    validación, de modo que se ignoran.

    Antes esto usaba `RefResolver`, que jsonschema deprecó en la 4.18 y acabará
    quitando.
    """
    documento = dict(SPEC_JS)
    documento.pop("$ref", None)
    documento.update(esquema)
    return Draft202012Validator(documento)


def comprobar(respuesta, ruta_spec, metodo, esperado):
    """Valida el cuerpo contra el schema que el spec promete para ese status."""
    assert respuesta.status_code == esperado, (
        f"{metodo.upper()} {ruta_spec} devolvió {respuesta.status_code}, "
        f"el spec dice {esperado}: {respuesta.get_data(as_text=True)[:300]}"
    )

    operacion = SPEC_JS["paths"][ruta_spec][metodo]
    definicion = operacion["responses"].get(str(esperado))
    assert definicion is not None, (
        f"{metodo.upper()} {ruta_spec} devolvió {esperado}, "
        f"que el spec no documenta"
    )

    esquema = definicion["content"]["application/json"]["schema"]
    cuerpo = respuesta.get_json()

    errores = sorted(validador(esquema).iter_errors(cuerpo), key=lambda e: e.path)
    if errores:
        detalle = "\n".join(
            f"    {'/'.join(str(p) for p in e.absolute_path) or '(raíz)'}: {e.message}"
            for e in errores[:8]
        )
        raise AssertionError(
            f"{metodo.upper()} {ruta_spec} ({esperado}) no cumple el spec:\n{detalle}"
        )


# ---------------------------------------------------------------------------
# el barrido: cada operación documentada, contra el servidor
# ---------------------------------------------------------------------------

# (ruta del spec, método, url real, status, necesita auth)
LLAMADAS = [
    ("/api/users/register", "post", "/api/users/register", 201, None),
    ("/api/users/login", "post", "/api/users/login", 200, None),
    ("/api/users/refresh", "post", "/api/users/refresh", 200, "refresh"),
    ("/api/users/profile", "get", "/api/users/profile", 200, "auth"),
    ("/api/users/profile", "put", "/api/users/profile", 200, "auth"),
    ("/api/users/location-permission", "post",
     "/api/users/location-permission", 200, "auth"),

    ("/api/places/", "get", "/api/places/", 200, None),
    ("/api/places/", "get", "/api/places/?curation=must_see", 200, "auth"),
    ("/api/places/{place_id}", "get", "/api/places/templo-mayor", 200, None),
    ("/api/places/{place_id}", "get", "/api/places/museo", 200, None),
    ("/api/places/{place_id}", "get", "/api/places/museo", 200, "auth"),
    ("/api/places/{place_id}", "get", "/api/places/no-existe", 404, None),
    ("/api/places/nearby", "get",
     "/api/places/nearby?latitude=19.4326&longitude=-99.1332&radius=5", 200, None),
    ("/api/places/nearby", "get", "/api/places/nearby", 400, None),
    ("/api/places/recommended", "get",
     "/api/places/recommended?latitude=19.4326&longitude=-99.1332", 200, None),
    ("/api/places/saved", "get", "/api/places/saved", 200, "auth"),
    ("/api/places/saved", "get", "/api/places/saved", 401, None),
    ("/api/places/{place_id}/save", "post", "/api/places/museo/save", 201, "auth"),
    ("/api/places/{place_id}/save", "delete", "/api/places/museo/save", 200, "auth"),

    ("/api/tours/", "get", "/api/tours/", 200, None),
    ("/api/tours/free", "get", "/api/tours/free", 200, None),
    ("/api/tours/{tour_id}", "get", "/api/tours/ruta", 200, None),
    ("/api/tours/{tour_id}", "get", "/api/tours/ruta", 200, "auth"),
    ("/api/tours/{tour_id}", "get", "/api/tours/no-existe", 404, None),
    ("/api/tours/user/tours", "get", "/api/tours/user/tours", 200, "auth"),
    ("/api/tours/{tour_id}/start", "post", "/api/tours/ruta/start", 201, "auth"),
    ("/api/tours/{tour_id}/progress", "put", "/api/tours/ruta/progress", 200, "auth"),
    ("/api/tours/{tour_id}/complete", "post", "/api/tours/ruta/complete", 200, "auth"),

    ("/api/historical/chronology", "get", "/api/historical/chronology", 200, None),
    ("/api/historical/topics", "get", "/api/historical/topics", 200, None),
    ("/api/historical/content", "get", "/api/historical/content", 200, None),
    ("/api/historical/content/{content_id}", "get",
     "/api/historical/content/founding", 200, "auth"),
    ("/api/historical/content/{content_id}", "get",
     "/api/historical/content/fall", 200, None),
    ("/api/historical/content/{content_id}", "get",
     "/api/historical/content/no-existe", 404, None),
    ("/api/historical/content/topic", "get",
     "/api/historical/content/topic?topic=Conquest", 200, None),
    ("/api/historical/content/era", "get",
     "/api/historical/content/era?era=Aztec Empire (1345-1521)", 200, None),
    ("/api/historical/content/place/{place_id}", "get",
     "/api/historical/content/place/templo-mayor", 200, None),
    ("/api/historical/content/{content_id}/read", "post",
     "/api/historical/content/fall/read", 200, "auth"),
    ("/api/historical/content/{content_id}/read", "delete",
     "/api/historical/content/fall/read", 200, "auth"),
    ("/api/historical/timelines", "get", "/api/historical/timelines", 200, None),
    ("/api/historical/lake-view", "get",
     f"/api/historical/lake-view?year={ERA_HISTORIC_YEAR}", 200, None),
    ("/api/historical/lake-view", "get",
     "/api/historical/lake-view?year=2026", 200, None),
    ("/api/historical/lake-view", "get",
     "/api/historical/lake-view?bbox=-99.2,19.3,-99.0,19.5", 200, None),

    ("/api/payments/access", "get", "/api/payments/access", 200, "auth"),
    ("/api/payments/access", "get", "/api/payments/access", 401, None),
    ("/api/payments/purchases", "get", "/api/payments/purchases", 200, "auth"),
    ("/api/payments/checkout", "post", "/api/payments/checkout", 409, "auth"),
]

CUERPOS = {
    ("/api/users/register", "post"):
        {"email": "nuevo@az.com", "password": "testpassword123"},
    ("/api/users/login", "post"):
        {"email": "contract@az.com", "password": "testpassword123"},
    ("/api/users/profile", "put"): {"firstName": "Bertin"},
    ("/api/users/location-permission", "post"): {"response": "granted"},
    ("/api/tours/{tour_id}/progress", "put"): {"currentStopIndex": 1},
    ("/api/tours/{tour_id}/complete", "post"): {"rating": 5},
}


@pytest.mark.parametrize(
    "ruta_spec,metodo,url,esperado,cabeceras",
    LLAMADAS,
    ids=[f"{m.upper()} {u}" for _, m, u, _, _ in LLAMADAS],
)
def test_la_respuesta_cumple_el_spec(
    client, app, mundo, ruta_spec, metodo, url, esperado, cabeceras
):
    headers = mundo[cabeceras] if cabeceras else {}
    r = client.open(url, method=metodo.upper(), headers=headers,
                    json=CUERPOS.get((ruta_spec, metodo)))
    comprobar(r, ruta_spec, metodo, esperado)


# ---------------------------------------------------------------------------
# cobertura: nada de la app puede quedarse fuera del spec
# ---------------------------------------------------------------------------

def test_el_spec_cubre_todas_las_rutas_de_la_app(app):
    """Un endpoint sin documentar es un endpoint que el front no sabe que existe."""
    reales = set()
    for regla in app.url_map.iter_rules():
        ruta = _normaliza_ruta(str(regla))
        if not ruta.startswith("/api"):
            continue
        for metodo in regla.methods - {"HEAD", "OPTIONS"}:
            reales.add((ruta, metodo.lower()))

    documentadas = {
        (ruta, metodo)
        for ruta, ops in SPEC["paths"].items()
        for metodo in ops
        if metodo in ("get", "post", "put", "patch", "delete")
    }

    sin_documentar = reales - documentadas
    inventadas = documentadas - reales

    assert not sin_documentar, f"rutas de la app fuera del spec: {sorted(sin_documentar)}"
    assert not inventadas, f"rutas del spec que la app no sirve: {sorted(inventadas)}"


def test_el_spec_del_repo_esta_regenerado(app):
    """openapi.json tiene que ser el que produce `python spec.py` HOY.

    Si alguien toca los schemas y no regenera, el frontend genera su capa de
    datos contra una versión vieja y se entera en runtime.
    """
    from app.api_spec import build_spec

    assert build_spec().to_dict() == SPEC, (
        "openapi.json está desactualizado: corre `python spec.py`"
    )
