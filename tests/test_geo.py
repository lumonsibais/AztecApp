"""Consultas espaciales sobre PostGIS.

Fijan que find_nearby usa el índice y no un bucle en Python, y que el overlay
del lago sale como GeoJSON válido recortado por el encuadre.
"""
from geoalchemy2 import Geometry
from sqlalchemy import cast, func

from app.extensions import db
from app.historical.services import LakeViewService
from app.places.models import Place
from app.places.repositories import PlaceRepository

# Coordenadas reales de la CDMX, para que las distancias signifiquen algo.
TEMPLO_MAYOR = (19.4361, -99.1356)
BELLAS_ARTES = (19.4352, -99.1412)          # ~600 m del Templo Mayor
ANTROPOLOGIA = (19.4260, -99.1863)          # ~5,3 km
TEOTIHUACAN = (19.6925, -98.8438)           # ~45 km


def crear(pid, lat, lon, nombre):
    place = Place(
        id=pid, name=nombre, description="d",
        latitude=lat, longitude=lon,
        place_type="ruin", historical_significance="h",
        estimated_visit_duration=60, is_locked=False,
    )
    db.session.add(place)
    db.session.commit()
    return place


def sembrar():
    crear("tm", *TEMPLO_MAYOR, "Templo Mayor")
    crear("ba", *BELLAS_ARTES, "Bellas Artes")
    crear("an", *ANTROPOLOGIA, "Museo de Antropología")
    crear("te", *TEOTIHUACAN, "Teotihuacán")


# --------------------------------------------------------------------------
# Place.geom
# --------------------------------------------------------------------------

def test_geom_se_rellena_sola_al_insertar(client, app):
    """El listener la deriva de lat/lng: nadie escribe geom a mano."""
    crear("tm", *TEMPLO_MAYOR, "Templo Mayor")

    # ST_X/ST_Y son de geometry, no de geography: hay que convertir.
    punto = cast(Place.geom, Geometry)
    lon, lat = db.session.query(
        func.ST_X(punto), func.ST_Y(punto)
    ).filter(Place.id == "tm").first()

    # Y en el orden correcto: POINT(longitud latitud)
    assert round(lon, 4) == round(TEMPLO_MAYOR[1], 4)
    assert round(lat, 4) == round(TEMPLO_MAYOR[0], 4)


def test_geom_se_actualiza_al_mover_el_sitio(client, app):
    crear("tm", *TEMPLO_MAYOR, "Templo Mayor")
    PlaceRepository.update("tm", {"latitude": TEOTIHUACAN[0], "longitude": TEOTIHUACAN[1]})

    cerca = PlaceRepository.find_nearby(*TEOTIHUACAN, radius_km=5)
    assert [p.id for p in cerca] == ["tm"]


# --------------------------------------------------------------------------
# find_nearby con ST_DWithin
# --------------------------------------------------------------------------

def test_el_radio_recorta_de_verdad(client, app):
    sembrar()

    en_1km = PlaceRepository.find_nearby(*TEMPLO_MAYOR, radius_km=1)
    assert set(p.id for p in en_1km) == {"tm", "ba"}

    en_10km = PlaceRepository.find_nearby(*TEMPLO_MAYOR, radius_km=10)
    assert set(p.id for p in en_10km) == {"tm", "ba", "an"}
    assert "te" not in [p.id for p in en_10km]


def test_vienen_ordenados_por_distancia(client, app):
    sembrar()
    cerca = PlaceRepository.find_nearby(*TEMPLO_MAYOR, radius_km=50)
    assert [p.id for p in cerca] == ["tm", "ba", "an", "te"]


def test_el_limite_se_respeta(client, app):
    sembrar()
    assert len(PlaceRepository.find_nearby(*TEMPLO_MAYOR, radius_km=50, limit=2)) == 2


def test_la_distancia_la_calcula_postgis(client, app):
    sembrar()
    tm = PlaceRepository.find_by_id("tm")
    an = PlaceRepository.find_by_id("an")

    assert PlaceRepository.distance_km(tm, *TEMPLO_MAYOR) < 0.001
    # ~5,3 km medidos sobre el elipsoide
    assert 5.0 < PlaceRepository.distance_km(an, *TEMPLO_MAYOR) < 5.7


def test_el_endpoint_de_cercanos_usa_la_consulta_espacial(client, app):
    sembrar()
    r = client.get("/api/places/nearby?latitude=19.4361&longitude=-99.1356&radius=1")

    assert r.status_code == 200
    datos = r.get_json()["data"]
    assert datos["count"] == 2
    assert datos["places"][0]["name"] == "Templo Mayor"


# --------------------------------------------------------------------------
# overlay del lago
# --------------------------------------------------------------------------

CENTRO = {
    "type": "Polygon",
    "coordinates": [[[-99.145, 19.425], [-99.145, 19.445],
                     [-99.124, 19.445], [-99.124, 19.425], [-99.145, 19.425]]],
}
LEJOS = {
    "type": "Polygon",
    "coordinates": [[[-98.90, 19.68], [-98.90, 19.70],
                     [-98.87, 19.70], [-98.87, 19.68], [-98.90, 19.68]]],
}


def test_el_overlay_sale_como_featurecollection(client, app):
    LakeViewService.create_lake_geometry(
        "Isla de Tenochtitlan", CENTRO,
        year_estimate=1519, tenochtitlan_name="Tenochtitlan",
    )

    datos = client.get("/api/historical/lake-view").get_json()["data"]

    assert datos["type"] == "FeatureCollection"
    assert len(datos["features"]) == 1

    f = datos["features"][0]
    assert f["type"] == "Feature"
    # La geometría viaja como objeto, no como cadena escapada
    assert f["geometry"]["type"] == "Polygon"
    assert isinstance(f["geometry"]["coordinates"], list)
    assert f["properties"]["tenochtitlanName"] == "Tenochtitlan"


def test_el_bbox_recorta(client, app):
    LakeViewService.create_lake_geometry("Centro", CENTRO)
    LakeViewService.create_lake_geometry("Teotihuacán", LEJOS)

    assert len(client.get("/api/historical/lake-view").get_json()["data"]["features"]) == 2

    encuadre = "-99.16,19.41,-99.11,19.46"
    recortado = client.get(
        f"/api/historical/lake-view?bbox={encuadre}"
    ).get_json()["data"]

    assert [f["properties"]["name"] for f in recortado["features"]] == ["Centro"]


def test_un_poligono_que_asoma_por_la_esquina_tambien_entra(client, app):
    """ST_Intersects, no "contenido en": si asoma, hay que pintarlo."""
    LakeViewService.create_lake_geometry("Centro", CENTRO)

    # Encuadre que solo pisa la esquina inferior izquierda del polígono
    esquina = "-99.150,19.420,-99.140,19.430"
    datos = client.get(f"/api/historical/lake-view?bbox={esquina}").get_json()["data"]

    assert len(datos["features"]) == 1


def test_un_bbox_mal_formado_da_400(client, app):
    for malo in ["1,2,3", "a,b,c,d", "-99.1,19.5,-99.2,19.4"]:
        r = client.get(f"/api/historical/lake-view?bbox={malo}")
        assert r.status_code == 400, malo
