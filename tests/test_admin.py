"""La API de administración, y sobre todo que esté cerrada.

El grueso de este archivo no prueba que crear un sitio funcione —eso es lo
fácil— sino que **nadie que no deba pueda escribir en el catálogo**. Es la
segunda vez que este backend abre una puerta de escritura, y la primera acabó
en una escalada de privilegios: un PUT al propio perfil con `has_full_access`
concedía el desbloqueo. Estos tests existen para que esa historia no se repita
con un permiso mucho más caro.
"""
import pytest

from app.extensions import db
from app.historical.models import HistoricalContent, Timeline
from app.places.models import Place
from app.shared.translations import ENTITY_PLACE
from app.shared.translations_repository import TranslationRepository
from app.users.repositories import UserRepository


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def registrar(client, email):
    r = client.post("/api/users/register",
                    json={"email": email, "password": "testpassword123"})
    assert r.status_code == 201, r.get_json()
    return r.get_json()["data"]


def auth(tokens):
    return {"Authorization": "Bearer " + tokens["accessToken"]}


def admin(client, email="admin@example.com"):
    """Una cuenta con el rol, concedido como se concede de verdad."""
    tokens = registrar(client, email)
    UserRepository.update(tokens["user"]["id"], {"is_admin": True})
    return tokens


SITIO_MINIMO = {
    "id": "sitio-nuevo",
    "name": "A new place",
    "description": "Body text",
    "latitude": 19.4361,
    "longitude": -99.1356,
    "place_type": "ruin",
    "historical_significance": "Significance",
    "estimated_visit_duration": 60,
}


# --------------------------------------------------------------------------
# la puerta
# --------------------------------------------------------------------------

RUTAS = [
    ("GET", "/api/admin/places"),
    ("POST", "/api/admin/places"),
    ("PUT", "/api/admin/places/templo-mayor"),
    ("GET", "/api/admin/tours"),
    ("POST", "/api/admin/tours"),
    ("GET", "/api/admin/content"),
    ("POST", "/api/admin/content"),
    ("GET", "/api/admin/lake-geometries"),
    ("POST", "/api/admin/lake-geometries"),
]


@pytest.mark.parametrize("metodo,ruta", RUTAS,
                         ids=[f"{m} {r}" for m, r in RUTAS])
def test_sin_token_no_se_entra(client, metodo, ruta):
    assert client.open(ruta, method=metodo, json={}).status_code == 401


@pytest.mark.parametrize("metodo,ruta", RUTAS,
                         ids=[f"{m} {r}" for m, r in RUTAS])
def test_un_usuario_normal_no_entra(client, metodo, ruta):
    """Y recibe 404, no 403.

    Un 403 confirma que la ruta existe. La API de administración no tiene por
    qué ser descubrible desde la app: quien la necesita ya sabe que está ahí.
    """
    tokens = registrar(client, f"normal-{metodo}-{ruta.count('/')}@example.com")
    r = client.open(ruta, method=metodo, headers=auth(tokens), json={})
    assert r.status_code == 404


def test_el_rol_no_se_concede_por_la_api(client, app):
    """No existe ningún endpoint que conceda `is_admin`.

    Se concede con `flask admin grant`, que exige acceso al servidor. Si algún
    día alguien añade una ruta para hacerlo cómodo, este test no se va a
    enterar — pero el de abajo, que prueba el perfil, sí.
    """
    tokens = registrar(client, "aspirante@example.com")

    r = client.put("/api/users/profile",
                   json={"is_admin": True}, headers=auth(tokens))
    assert r.status_code == 400
    assert "is_admin" in r.get_json()["details"]

    usuario = UserRepository.find_by_id(tokens["user"]["id"])
    assert usuario.is_admin is False


def test_el_comando_de_consola_concede_y_retira(client, app):
    from app.cli import grant, revoke

    tokens = registrar(client, "porconsola@example.com")
    runner = app.test_cli_runner()

    runner.invoke(grant, ["porconsola@example.com"])
    assert UserRepository.find_by_id(tokens["user"]["id"]).is_admin is True

    runner.invoke(revoke, ["porconsola@example.com"])
    assert UserRepository.find_by_id(tokens["user"]["id"]).is_admin is False


def test_el_comando_avisa_si_la_cuenta_no_existe(client, app):
    from app.cli import grant

    resultado = app.test_cli_runner().invoke(grant, ["nadie@example.com"])
    assert resultado.exit_code != 0
    assert "No hay ninguna cuenta" in resultado.output


# --------------------------------------------------------------------------
# borrador y publicado
# --------------------------------------------------------------------------

def test_un_sitio_nuevo_nace_en_borrador_y_no_sale_en_explore(client, app):
    """Lo importante de todo el bloque.

    Cargar un catálogo son varias sesiones de escribir. Si cada ficha a medias
    apareciera en Explore, el equipo estaría publicando borradores sin querer
    cada vez que guarda.
    """
    a = admin(client)

    r = client.post("/api/admin/places", json=SITIO_MINIMO, headers=auth(a))
    assert r.status_code == 201
    assert r.get_json()["data"]["isPublished"] is False

    publico = client.get("/api/places/").get_json()["data"]["places"]
    assert [p["id"] for p in publico] == []

    # y el detalle tampoco: un borrador no existe para la app
    assert client.get("/api/places/sitio-nuevo").status_code == 404

    # pero el administrador sí lo ve
    suyos = client.get("/api/admin/places", headers=auth(a)).get_json()["data"]
    assert [p["id"] for p in suyos["places"]] == ["sitio-nuevo"]
    assert suyos["drafts"] == 1


def test_publicar_lo_saca_a_la_calle(client, app):
    a = admin(client)
    client.post("/api/admin/places", json=SITIO_MINIMO, headers=auth(a))

    r = client.put("/api/admin/places/sitio-nuevo",
                   json={"is_published": True}, headers=auth(a))
    assert r.status_code == 200

    publico = client.get("/api/places/").get_json()["data"]["places"]
    assert [p["id"] for p in publico] == ["sitio-nuevo"]
    assert client.get("/api/places/sitio-nuevo").status_code == 200


def test_despublicar_lo_retira_tambien_de_guardados(client, app):
    """Un sitio retirado no debe quedar como tarjeta que lleva a un 404."""
    a = admin(client)
    client.post("/api/admin/places",
                json={**SITIO_MINIMO, "is_published": True}, headers=auth(a))

    lector = registrar(client, "lector@example.com")
    assert client.post("/api/places/sitio-nuevo/save",
                       headers=auth(lector)).status_code == 201
    guardados = client.get("/api/places/saved",
                           headers=auth(lector)).get_json()["data"]
    assert guardados["count"] == 1

    client.put("/api/admin/places/sitio-nuevo",
               json={"is_published": False}, headers=auth(a))

    guardados = client.get("/api/places/saved",
                           headers=auth(lector)).get_json()["data"]
    assert guardados["count"] == 0


def test_un_borrador_tampoco_sale_en_cercanos(client, app):
    """La ruta de PostGIS es otra consulta, y se le podría olvidar el filtro."""
    a = admin(client)
    client.post("/api/admin/places", json=SITIO_MINIMO, headers=auth(a))

    cerca = client.get(
        "/api/places/nearby?latitude=19.4361&longitude=-99.1356&radius=5"
    ).get_json()["data"]["places"]
    assert cerca == []


# --------------------------------------------------------------------------
# escritura: lista blanca y traducciones
# --------------------------------------------------------------------------

def test_un_campo_fuera_de_la_lista_devuelve_400(client, app):
    """Y no se ignora en silencio.

    Ignorar es peor de lo que parece: quien carga el catálogo cree que guardó
    algo que no se guardó, y se entera semanas después.
    """
    a = admin(client)

    r = client.post("/api/admin/places",
                    json={**SITIO_MINIMO, "views_count": 9999}, headers=auth(a))
    assert r.status_code == 400
    assert "views_count" in r.get_json()["details"]


def test_el_id_no_se_puede_cambiar(client, app):
    """Renombrar la clave rompería los guardados y las paradas de tour."""
    a = admin(client)
    client.post("/api/admin/places", json=SITIO_MINIMO, headers=auth(a))

    r = client.put("/api/admin/places/sitio-nuevo",
                   json={"id": "otro-id"}, headers=auth(a))
    assert r.status_code == 400


def test_el_id_tiene_que_ser_legible(client, app):
    a = admin(client)
    for malo in ["Con Mayúsculas", "con espacios", "con_guion_bajo", "acentuación"]:
        r = client.post("/api/admin/places",
                        json={**SITIO_MINIMO, "id": malo}, headers=auth(a))
        assert r.status_code == 400, malo


def test_no_se_puede_crear_dos_veces_el_mismo_id(client, app):
    a = admin(client)
    assert client.post("/api/admin/places", json=SITIO_MINIMO,
                       headers=auth(a)).status_code == 201
    assert client.post("/api/admin/places", json=SITIO_MINIMO,
                       headers=auth(a)).status_code == 409


def test_gratis_y_con_precio_a_la_vez_se_rechaza(client, app):
    a = admin(client)
    r = client.post("/api/admin/places",
                    json={**SITIO_MINIMO, "is_free_entry": True,
                          "entry_fee_mxn": 95},
                    headers=auth(a))
    assert r.status_code == 400


def test_las_traducciones_entran_en_la_misma_llamada(client, app):
    """Cargar una ficha bilingüe en dos peticiones invita a dejar la segunda
    sin hacer, y el resultado es contenido a medio traducir."""
    a = admin(client)

    r = client.post("/api/admin/places", json={
        **SITIO_MINIMO,
        "is_published": True,
        "tagline": "An English hook",
        "translations": {"es": {
            "name": "Un sitio nuevo",
            "tagline": "Un gancho en español",
        }},
    }, headers=auth(a))
    assert r.status_code == 201

    guardadas = TranslationRepository.find_for_entity(
        ENTITY_PLACE, "sitio-nuevo", "es")
    assert guardadas["name"] == "Un sitio nuevo"

    # y la app las sirve por la cabecera
    es = client.get("/api/places/sitio-nuevo",
                    headers={"Accept-Language": "es-MX"}).get_json()["data"]
    assert es["name"] == "Un sitio nuevo"
    assert es["tagline"] == "Un gancho en español"

    en = client.get("/api/places/sitio-nuevo").get_json()["data"]
    assert en["name"] == "A new place"


def test_un_idioma_no_soportado_se_rechaza(client, app):
    a = admin(client)
    r = client.post("/api/admin/places", json={
        **SITIO_MINIMO,
        "translations": {"fr": {"name": "Un nouveau lieu"}},
    }, headers=auth(a))
    assert r.status_code == 400


# --------------------------------------------------------------------------
# tours y sus paradas
# --------------------------------------------------------------------------

TOUR_MINIMO = {
    "id": "ruta-nueva",
    "title": "A new tour",
    "description": "Teaser",
    "estimated_duration": 120,
}


def _dos_sitios(client, a):
    for i in (1, 2):
        client.post("/api/admin/places", json={
            **SITIO_MINIMO, "id": f"sitio-{i}", "name": f"Place {i}",
            "is_published": True,
        }, headers=auth(a))


def test_un_tour_se_crea_con_sus_paradas(client, app):
    a = admin(client)
    _dos_sitios(client, a)

    r = client.post("/api/admin/tours", json={
        **TOUR_MINIMO,
        "stops": [
            {"place_id": "sitio-1", "position": 0,
             "audio_url": "https://cdn.example/a.mp3"},
            {"place_id": "sitio-2", "position": 1},
        ],
    }, headers=auth(a))
    assert r.status_code == 201

    tour = r.get_json()["data"]
    assert tour["stopsCount"] == 2
    assert [s["position"] for s in tour["stops"]] == [0, 1]


def test_una_parada_a_un_sitio_inexistente_da_409_y_no_500(client, app):
    """Sin esta comprobación sería un error de clave foránea, que le llega al
    editor como un 500 sin explicación."""
    a = admin(client)

    r = client.post("/api/admin/tours", json={
        **TOUR_MINIMO,
        "stops": [{"place_id": "no-existe", "position": 0}],
    }, headers=auth(a))
    assert r.status_code == 409
    assert "no-existe" in r.get_json()["error"]


def test_dos_paradas_en_la_misma_posicion_se_rechazan(client, app):
    a = admin(client)
    _dos_sitios(client, a)

    r = client.post("/api/admin/tours", json={
        **TOUR_MINIMO,
        "stops": [
            {"place_id": "sitio-1", "position": 0},
            {"place_id": "sitio-2", "position": 0},
        ],
    }, headers=auth(a))
    assert r.status_code == 400


def test_editar_las_paradas_las_sustituye_enteras(client, app):
    """Se mandan completas a propósito: así no existen estados intermedios en
    los que el recorrido queda con dos paradas en la misma posición."""
    a = admin(client)
    _dos_sitios(client, a)
    client.post("/api/admin/tours", json={
        **TOUR_MINIMO,
        "stops": [{"place_id": "sitio-1", "position": 0},
                  {"place_id": "sitio-2", "position": 1}],
    }, headers=auth(a))

    r = client.put("/api/admin/tours/ruta-nueva", json={
        "stops": [{"place_id": "sitio-2", "position": 0}],
    }, headers=auth(a))
    assert r.status_code == 200

    tour = r.get_json()["data"]
    assert tour["stopsCount"] == 1
    assert tour["stops"][0]["placeId"] == "sitio-2"


def test_mandar_una_lista_vacia_deja_el_tour_sin_paradas(client, app):
    """Distinto de no mencionarlas: una lista vacía es una instrucción."""
    a = admin(client)
    _dos_sitios(client, a)
    client.post("/api/admin/tours", json={
        **TOUR_MINIMO,
        "stops": [{"place_id": "sitio-1", "position": 0}],
    }, headers=auth(a))

    r = client.put("/api/admin/tours/ruta-nueva",
                   json={"stops": []}, headers=auth(a))
    assert r.get_json()["data"]["stopsCount"] == 0

    # y no mencionarlas no las toca
    client.put("/api/admin/tours/ruta-nueva",
               json={"stops": [{"place_id": "sitio-1", "position": 0}]},
               headers=auth(a))
    r = client.put("/api/admin/tours/ruta-nueva",
                   json={"title": "Otro título"}, headers=auth(a))
    assert r.get_json()["data"]["stopsCount"] == 1


# --------------------------------------------------------------------------
# guía histórica
# --------------------------------------------------------------------------

def test_un_articulo_de_texto_necesita_texto(client, app):
    a = admin(client)
    r = client.post("/api/admin/content", json={
        "id": "articulo", "title": "T", "description": "D",
        "content_type": "text",
    }, headers=auth(a))
    assert r.status_code == 400
    assert "text_content" in r.get_json()["details"]


def test_un_articulo_de_audio_necesita_audio(client, app):
    a = admin(client)
    r = client.post("/api/admin/content", json={
        "id": "articulo", "title": "T", "description": "D",
        "content_type": "audio",
    }, headers=auth(a))
    assert r.status_code == 400


def test_editar_el_titulo_no_exige_repetir_el_cuerpo(client, app):
    """Una edición parcial no debería obligar a remandar todo el artículo."""
    a = admin(client)
    client.post("/api/admin/content", json={
        "id": "articulo", "title": "T", "description": "D",
        "content_type": "text", "text_content": "Cuerpo largo",
    }, headers=auth(a))

    r = client.put("/api/admin/content/articulo",
                   json={"title": "Título corregido"}, headers=auth(a))
    assert r.status_code == 200
    assert r.get_json()["data"]["title"] == "Título corregido"


def test_un_articulo_no_puede_colgar_de_una_cronologia_inexistente(client, app):
    a = admin(client)
    r = client.post("/api/admin/content", json={
        "id": "articulo", "title": "T", "description": "D",
        "content_type": "text", "text_content": "Cuerpo",
        "timeline_id": "no-existe",
    }, headers=auth(a))
    assert r.status_code == 409


# --------------------------------------------------------------------------
# polígonos del lago
# --------------------------------------------------------------------------

CUADRADO = {
    "type": "Polygon",
    "coordinates": [[[-99.17, 19.39], [-99.17, 19.49],
                     [-99.04, 19.49], [-99.04, 19.39], [-99.17, 19.39]]],
}


def test_se_puede_cargar_un_poligono_y_sale_en_el_overlay(client, app):
    a = admin(client)

    r = client.post("/api/admin/lake-geometries", json={
        "name": "Lake Texcoco", "surface_type": "water",
        "year_estimate": 1500, "geometry": CUADRADO,
    }, headers=auth(a))
    assert r.status_code == 201

    fc = client.get("/api/historical/lake-view?year=1500").get_json()["data"]
    assert len(fc["features"]) == 1
    assert fc["features"][0]["properties"]["surfaceType"] == "water"


def test_un_anillo_sin_cerrar_se_rechaza(client, app):
    """GeoJSON exige que el último punto repita el primero. Dejarlo pasar
    acabaría en un error de PostGIS que no dice qué polígono falló."""
    a = admin(client)
    abierto = {"type": "Polygon", "coordinates": [[
        [-99.17, 19.39], [-99.17, 19.49], [-99.04, 19.49], [-99.04, 19.39]]]}

    r = client.post("/api/admin/lake-geometries", json={
        "name": "Roto", "surface_type": "water", "geometry": abierto,
    }, headers=auth(a))
    assert r.status_code == 400
    assert "geometry" in r.get_json()["details"]


def test_una_superficie_inventada_se_rechaza(client, app):
    a = admin(client)
    r = client.post("/api/admin/lake-geometries", json={
        "name": "Lava", "surface_type": "lava", "geometry": CUADRADO,
    }, headers=auth(a))
    assert r.status_code == 400


def test_un_poligono_si_se_puede_borrar(client, app):
    """El único borrado real de la API: un trazado mal hecho no tiene nada
    colgando, al revés que un sitio o un artículo."""
    a = admin(client)
    r = client.post("/api/admin/lake-geometries", json={
        "name": "Provisional", "surface_type": "land",
        "year_estimate": 1500, "geometry": CUADRADO,
    }, headers=auth(a))
    geo_id = r.get_json()["data"]["id"]

    assert client.delete(f"/api/admin/lake-geometries/{geo_id}",
                         headers=auth(a)).status_code == 200
    assert client.delete(f"/api/admin/lake-geometries/{geo_id}",
                         headers=auth(a)).status_code == 404


def test_la_siembra_deja_el_catalogo_publicado(client, app):
    """seed.py tiene que publicar lo que siembra.

    `is_published` nace en false —un sitio nuevo es un borrador— y la siembra no
    lo ponía. El resultado era una instalación limpia con la base llena y la app
    vacía, sin un solo error en ningún log: `docker compose up`, siembra "OK 4
    sitios", y Explore en blanco. Lo destapó el smoke, no la suite.
    """
    from seed import seed_places

    seed_places()

    places = client.get("/api/places/").get_json()["data"]["places"]
    assert places, "la siembra dejó el catálogo invisible"
    assert len(places) == 4


# --------------------------------------------------------------------------
# galería, zona del tour y minutos a pie
#
# Los tres huecos que destapó el diseño de Figma al leerlo contra el contrato.
# --------------------------------------------------------------------------

FOTOS = [
    {"url": "https://cdn.example/1.jpg", "caption": "Desde la calle",
     "position": 0},
    {"url": "https://cdn.example/2.jpg", "position": 1},
    {"url": "https://cdn.example/3.jpg", "caption": "El detalle",
     "position": 2},
]


def test_la_galeria_llega_en_orden(client, app):
    a = admin(client)
    r = client.post("/api/admin/places",
                    json={**SITIO_MINIMO, "images": FOTOS}, headers=auth(a))
    assert r.status_code == 201, r.get_json()

    fotos = client.get(f"/api/places/{SITIO_MINIMO['id']}").get_json()
    # El sitio nace en borrador, así que no sale por la ruta pública todavía.
    assert fotos["success"] is False

    datos = r.get_json()["data"]
    assert [f["url"] for f in datos["images"]] == [f["url"] for f in FOTOS]
    assert datos["images"][0]["caption"] == "Desde la calle"
    assert datos["images"][1]["caption"] is None


def test_sin_galeria_images_trae_la_portada(client, app):
    """Así el cliente puede usar SIEMPRE `images` sin preguntarse por imageUrl."""
    a = admin(client)
    r = client.post("/api/admin/places",
                    json={**SITIO_MINIMO,
                          "image_url": "https://cdn.example/portada.jpg"},
                    headers=auth(a))

    datos = r.get_json()["data"]
    assert datos["imageUrl"] == "https://cdn.example/portada.jpg"
    assert datos["images"] == [
        {"url": "https://cdn.example/portada.jpg", "caption": None}]


def test_sin_foto_ninguna_images_llega_vacia(client, app):
    a = admin(client)
    r = client.post("/api/admin/places", json=SITIO_MINIMO, headers=auth(a))
    assert r.get_json()["data"]["images"] == []


def test_no_mandar_images_deja_la_galeria_como_estaba(client, app):
    """None y [] no son lo mismo, y la diferencia se nota al editar."""
    a = admin(client)
    client.post("/api/admin/places",
                json={**SITIO_MINIMO, "images": FOTOS}, headers=auth(a))

    # Una edición que no menciona las fotos.
    r = client.put(f"/api/admin/places/{SITIO_MINIMO['id']}",
                   json={"name": "Otro nombre"}, headers=auth(a))
    assert r.status_code == 200
    assert len(r.get_json()["data"]["images"]) == 3

    # Y una que las vacía a propósito.
    r = client.put(f"/api/admin/places/{SITIO_MINIMO['id']}",
                   json={"images": []}, headers=auth(a))
    assert r.get_json()["data"]["images"] == []


def test_dos_fotos_en_la_misma_posicion_dan_400(client, app):
    """400 con el motivo, no un 500 de integridad que nadie sabe leer."""
    a = admin(client)
    r = client.post("/api/admin/places", json={
        **SITIO_MINIMO,
        "images": [
            {"url": "https://cdn.example/1.jpg", "position": 0},
            {"url": "https://cdn.example/2.jpg", "position": 0},
        ],
    }, headers=auth(a))

    assert r.status_code == 400
    assert "images" in r.get_json()["details"]


def test_la_zona_y_los_minutos_a_pie_van_y_vuelven(client, app):
    a = admin(client)
    client.post("/api/admin/places", json=SITIO_MINIMO, headers=auth(a))
    client.post("/api/admin/places",
                json={**SITIO_MINIMO, "id": "sitio-dos", "name": "Second"},
                headers=auth(a))

    r = client.post("/api/admin/tours", json={
        "id": "paseo-nuevo",
        "title": "A walk",
        "description": "Body",
        "estimated_duration": 90,
        "neighborhood": "Centro Histórico",
        "stops": [
            {"place_id": SITIO_MINIMO["id"], "position": 0,
             "walk_minutes_to_next": 3},
            {"place_id": "sitio-dos", "position": 1},
        ],
    }, headers=auth(a))
    assert r.status_code == 201, r.get_json()

    datos = r.get_json()["data"]
    assert datos["neighborhood"] == "Centro Histórico"
    assert datos["stops"][0]["walkMinutesToNext"] == 3
    # La última parada no lleva a ninguna otra.
    assert datos["stops"][1]["walkMinutesToNext"] is None


def test_los_minutos_a_pie_viajan_con_el_tour_bloqueado(client, app):
    """Son logística, como la taquilla de un museo.

    Lo que se paga es el guion y el audio. Saber que hay tres minutos de camino
    entre dos plazas no es contenido nuestro, y esconderlo solo empeora la app
    de quien todavía no ha comprado.
    """
    from app.tours.models import Tour, TourStop

    db.session.add(Place(
        id="p-tour", name="Stop", description="B", latitude=19.4, longitude=-99.1,
        place_type="ruin", historical_significance="S",
        estimated_visit_duration=30, is_published=True))
    db.session.add(Tour(id="tour-pago", title="Paid", description="B",
                        estimated_duration=60, is_locked=True, is_free=False,
                        status="published"))
    db.session.flush()
    db.session.add(TourStop(id="s1", tour_id="tour-pago", place_id="p-tour",
                            position=0, walk_minutes_to_next=7,
                            transition_text="Secreto",
                            audio_url="https://cdn.example/a.mp3"))
    db.session.commit()

    parada = db.session.get(TourStop, "s1").to_dict(unlocked=False)

    assert parada["walkMinutesToNext"] == 7     # logística: viaja
    assert parada["transitionText"] is None     # guion: no viaja
    assert parada["audio"]["url"] is None       # audio: no viaja
    assert parada["audio"]["isLocked"] is True
