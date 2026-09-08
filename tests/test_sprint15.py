"""Sprint 1.5 — desbloqueo, Saved, History Guide, ficha y paradas de tour.

Cada test fija una decisión de producto de las que cerró el equipo, o un
agujero que el diseño destapó.
"""
import pytest

from app.extensions import db
from app.historical.models import HistoricalContent, Timeline
from app.payments.services import AlreadyPurchased, PurchaseService
from app.places.models import Place
from app.shared.constants import CURATION_MUST_SEE, CURATION_QUICK_STOP
from app.tours.models import Tour, TourStop
from app.users.repositories import UserRepository

TEMPLO_MAYOR = (19.4361, -99.1356)
BELLAS_ARTES = (19.4352, -99.1412)   # ~600 m


def registrar(client, email="user@example.com"):
    r = client.post("/api/users/register",
                    json={"email": email, "password": "testpassword123"})
    assert r.status_code == 201, r.get_json()
    return r.get_json()["data"]


def auth(tokens):
    return {"Authorization": "Bearer " + tokens["accessToken"]}


def crear_place(pid, nombre="Templo Mayor", bloqueado=False, curacion=None,
                lat=None, lon=None, **extra):
    place = Place(
        id=pid, name=nombre, description="Body", tagline="One line hook",
        latitude=lat if lat is not None else TEMPLO_MAYOR[0],
        longitude=lon if lon is not None else TEMPLO_MAYOR[1],
        place_type="ruin", historical_significance="Significance",
        estimated_visit_duration=60, is_locked=bloqueado, curation=curacion,
        **extra,
    )
    db.session.add(place)
    db.session.commit()
    return place


# --------------------------------------------------------------------------
# desbloqueo único
# --------------------------------------------------------------------------

def test_el_acceso_arranca_cerrado_y_se_concede_al_confirmar(client, app):
    app.config["PAYMENTS_ALLOW_UNVERIFIED"] = True
    tokens = registrar(client, "compra@example.com")

    estado = client.get("/api/payments/access", headers=auth(tokens)).get_json()["data"]
    assert estado["hasFullAccess"] is False
    assert estado["price"] == 15.0
    assert estado["currency"] == "USD"

    assert client.post("/api/payments/checkout", headers=auth(tokens)).status_code == 201

    r = client.post("/api/payments/confirm",
                    json={"provider": "stripe", "externalId": "pi_123"},
                    headers=auth(tokens))
    assert r.status_code == 200

    estado = client.get("/api/payments/access", headers=auth(tokens)).get_json()["data"]
    assert estado["hasFullAccess"] is True
    assert estado["since"] is not None


def test_el_mismo_recibo_dos_veces_no_duplica(client, app):
    """Un reintento del cliente o un webhook repetido no pueden cobrar dos veces."""
    app.config["PAYMENTS_ALLOW_UNVERIFIED"] = True
    tokens = registrar(client, "idem@example.com")

    for _ in range(3):
        r = client.post("/api/payments/confirm",
                        json={"provider": "apple", "externalId": "tx_abc"},
                        headers=auth(tokens))
        assert r.status_code == 200

    compras = client.get("/api/payments/purchases",
                         headers=auth(tokens)).get_json()["data"]["purchases"]
    completadas = [c for c in compras if c["status"] == "completed"]
    assert len(completadas) == 1


def test_el_checkout_no_deja_filas_muertas(client, app):
    """Un solo apunte por compra.

    /checkout abre una compra pendiente y /confirm la completa. Si `confirmar`
    insertara una fila nueva en vez de cerrar la abierta, quien pagara una vez
    vería dos apuntes en su historial: uno "pending" para siempre y uno
    "completed". Y tocar el botón tres veces dejaría tres pendientes.
    """
    app.config["PAYMENTS_ALLOW_UNVERIFIED"] = True
    tokens = registrar(client, "limpio@example.com")

    for _ in range(3):
        assert client.post(
            "/api/payments/checkout", headers=auth(tokens)
        ).status_code == 201

    client.post("/api/payments/confirm",
                json={"provider": "stripe", "externalId": "pi_limpio"},
                headers=auth(tokens))

    compras = client.get("/api/payments/purchases",
                         headers=auth(tokens)).get_json()["data"]["purchases"]

    assert len(compras) == 1
    assert compras[0]["status"] == "completed"
    assert compras[0]["provider"] == "stripe"


def test_sin_verificacion_no_se_concede_nada(client, app):
    """La costura del proveedor está sin implementar: debe negarse, no confiar."""
    app.config["PAYMENTS_ALLOW_UNVERIFIED"] = False
    tokens = registrar(client, "listo@example.com")

    r = client.post("/api/payments/confirm",
                    json={"provider": "stripe", "externalId": "pi_falso"},
                    headers=auth(tokens))
    assert r.status_code == 501

    estado = client.get("/api/payments/access", headers=auth(tokens)).get_json()["data"]
    assert estado["hasFullAccess"] is False


def test_no_se_puede_comprar_dos_veces(client, app):
    app.config["PAYMENTS_ALLOW_UNVERIFIED"] = True
    tokens = registrar(client, "otra@example.com")
    client.post("/api/payments/confirm",
                json={"provider": "google", "externalId": "gp_1"},
                headers=auth(tokens))

    assert client.post("/api/payments/checkout",
                       headers=auth(tokens)).status_code == 409


def test_el_reembolso_retira_el_acceso(client, app):
    """Marcar la compra sin quitar el permiso dejaría el contenido gratis."""
    app.config["PAYMENTS_ALLOW_UNVERIFIED"] = True
    tokens = registrar(client, "reembolso@example.com")
    r = client.post("/api/payments/confirm",
                    json={"provider": "stripe", "externalId": "pi_ref"},
                    headers=auth(tokens))
    compra_id = r.get_json()["data"]["id"]

    PurchaseService.reembolsar(compra_id, "prueba")

    usuario = UserRepository.find_by_id(tokens["user"]["id"])
    assert usuario.has_full_access is False


# --------------------------------------------------------------------------
# Saved
# --------------------------------------------------------------------------

def test_guardar_y_quitar_un_sitio(client, app):
    crear_place("p1")
    tokens = registrar(client, "saved@example.com")

    vacio = client.get("/api/places/saved", headers=auth(tokens)).get_json()["data"]
    assert vacio["count"] == 0

    assert client.post("/api/places/p1/save", headers=auth(tokens)).status_code == 201

    guardados = client.get("/api/places/saved", headers=auth(tokens)).get_json()["data"]
    assert [p["id"] for p in guardados["places"]] == ["p1"]
    assert guardados["places"][0]["isSaved"] is True

    assert client.delete("/api/places/p1/save", headers=auth(tokens)).status_code == 200
    assert client.get("/api/places/saved",
                      headers=auth(tokens)).get_json()["data"]["count"] == 0


def test_guardar_es_idempotente(client, app):
    crear_place("p1")
    tokens = registrar(client, "doble@example.com")

    for _ in range(3):
        client.post("/api/places/p1/save", headers=auth(tokens))

    assert client.get("/api/places/saved",
                      headers=auth(tokens)).get_json()["data"]["count"] == 1


def test_el_listado_trae_el_estado_del_corazon(client, app):
    crear_place("p1")
    crear_place("p2", "Tlatelolco")
    tokens = registrar(client, "corazon@example.com")
    client.post("/api/places/p1/save", headers=auth(tokens))

    places = client.get("/api/places/", headers=auth(tokens)).get_json()["data"]["places"]
    estado = {p["id"]: p["isSaved"] for p in places}
    assert estado == {"p1": True, "p2": False}


def test_sin_sesion_el_corazon_no_viaja(client, app):
    crear_place("p1")
    place = client.get("/api/places/p1").get_json()["data"]
    assert place["isSaved"] is None


def test_guardar_un_sitio_inexistente_da_404(client, app):
    tokens = registrar(client, "fantasma@example.com")
    assert client.post("/api/places/no-existe/save",
                       headers=auth(tokens)).status_code == 404


# --------------------------------------------------------------------------
# ficha: distancia, curación, monedas
# --------------------------------------------------------------------------

def test_la_distancia_viaja_en_la_respuesta(client, app):
    """PostGIS ya la calculaba para ordenar; el diseño la pinta en la tarjeta."""
    crear_place("tm", "Templo Mayor")
    crear_place("ba", "Bellas Artes", lat=BELLAS_ARTES[0], lon=BELLAS_ARTES[1])

    datos = client.get(
        "/api/places/nearby?latitude=19.4361&longitude=-99.1356&radius=2"
    ).get_json()["data"]

    por_id = {p["id"]: p["location"]["distanceKm"] for p in datos["places"]}
    assert por_id["tm"] == 0.0
    assert 0.4 < por_id["ba"] < 0.8


def test_sin_coordenadas_no_hay_distancia(client, app):
    crear_place("p1")
    place = client.get("/api/places/p1").get_json()["data"]
    assert place["location"]["distanceKm"] is None


def test_los_filtros_editoriales_recortan(client, app):
    crear_place("must", "Templo Mayor", curacion=CURATION_MUST_SEE)
    crear_place("quick", "Monumento", curacion=CURATION_QUICK_STOP)
    crear_place("sin", "Otro")

    todos = client.get("/api/places/").get_json()["data"]
    assert todos["total"] == 3

    solo = client.get("/api/places/?curation=must_see").get_json()["data"]
    assert [p["id"] for p in solo["places"]] == ["must"]

    # Un valor que no existe se ignora en vez de devolver una lista vacía
    raro = client.get("/api/places/?curation=inventado").get_json()["data"]
    assert raro["total"] == 3


def test_las_tarifas_viajan_en_los_dos_importes(client, app):
    crear_place("p1", entry_fee_mxn=95, entry_fee_usd=5.5,
                entry_fee_text="95 MXN for the museum", is_free_entry=False)

    place = client.get("/api/places/p1").get_json()["data"]
    assert place["entryFee"]["mxn"] == 95.0
    assert place["entryFee"]["usd"] == 5.5
    assert place["entryFee"]["isFree"] is False


def test_la_taquilla_del_museo_no_esta_detras_del_candado(client, app):
    """El precio de la entrada es del museo, no nuestro.

    Son dos dineros distintos: los 15 USD del desbloqueo son lo que cobramos
    nosotros; los 95 pesos son lo que cobra el Museo de Antropología en su
    taquilla. Lo segundo está en internet, así que esconderlo no vende nada:
    solo saca al viajero de la app a buscarlo. Si alguien vuelve a meter la
    logística dentro del bloque de pago, este test se pone rojo.
    """
    crear_place("p1", bloqueado=True, entry_fee_mxn=95, entry_fee_usd=5.5,
                opening_hours="Tue-Sun, 9-18", how_to_get_there="Metro Auditorio")

    place = client.get("/api/places/p1").get_json()["data"]

    assert place["contentAccess"]["unlockedForViewer"] is False
    assert place["entryFee"]["mxn"] == 95.0
    assert "openingHours" in place
    assert "howToGetThere" in place

    # y lo que sí es nuestro sigue cerrado
    assert "whyVisit" not in place


def test_la_duracion_lleva_numero_y_texto(client, app):
    crear_place("p1", visit_duration_text="30 min outside, 1-3 hours inside")

    place = client.get("/api/places/p1").get_json()["data"]
    assert place["estimatedVisitDuration"] == 60          # ordena y filtra
    assert "1-3 hours" in place["visitDurationText"]      # es lo que se muestra


# --------------------------------------------------------------------------
# History Guide
# --------------------------------------------------------------------------

def sembrar_guia():
    linea = Timeline(id="tl", title="Legacy of the Aztec", sort_order=0)
    db.session.add(linea)
    db.session.flush()

    for i, (slug, tema, minutos) in enumerate(
        [("a", "Foundation", 4), ("b", "Daily life", 6), ("c", "Conquest", 8)]
    ):
        db.session.add(HistoricalContent(
            id=slug, title=f"Article {slug}", description="Summary",
            content_type="text", text_content="Body",
            timeline_id=linea.id, sort_order=i,
            topic=tema, reading_time_minutes=minutos,
        ))
    db.session.commit()


def test_la_cronologia_sale_ordenada(client, app):
    sembrar_guia()
    contenido = client.get("/api/historical/chronology").get_json()["data"]["content"]
    assert [c["id"] for c in contenido] == ["a", "b", "c"]
    assert contenido[0]["readingTimeMinutes"] == 4


def test_el_siguiente_articulo_encadena(client, app):
    """El botón "Next" necesita saber cuál va después."""
    sembrar_guia()
    assert client.get("/api/historical/content/a").get_json()["data"]["nextContentId"] == "b"
    assert client.get("/api/historical/content/c").get_json()["data"]["nextContentId"] is None


def test_los_temas_vienen_con_su_cuenta(client, app):
    sembrar_guia()
    temas = client.get("/api/historical/topics").get_json()["data"]["topics"]
    assert {t["topic"] for t in temas} == {"Foundation", "Daily life", "Conquest"}
    assert all(t["count"] == 1 for t in temas)


def test_marcar_leido_y_desmarcar(client, app):
    sembrar_guia()
    tokens = registrar(client, "lector@example.com")

    assert client.get("/api/historical/content/a",
                      headers=auth(tokens)).get_json()["data"]["isRead"] is False

    assert client.post("/api/historical/content/a/read",
                       headers=auth(tokens)).status_code == 200
    assert client.get("/api/historical/content/a",
                      headers=auth(tokens)).get_json()["data"]["isRead"] is True

    client.delete("/api/historical/content/a/read", headers=auth(tokens))
    assert client.get("/api/historical/content/a",
                      headers=auth(tokens)).get_json()["data"]["isRead"] is False


def test_sin_sesion_no_hay_estado_de_lectura(client, app):
    sembrar_guia()
    assert client.get("/api/historical/content/a").get_json()["data"]["isRead"] is None


# --------------------------------------------------------------------------
# paradas de tour
# --------------------------------------------------------------------------

def sembrar_tour(bloqueado=True):
    for i, pid in enumerate(["p0", "p1", "p2"]):
        crear_place(pid, f"Stop {i}")

    tour = Tour(id="t1", title="Unearth Tenochtitlan", description="Walk",
                content_description="Script", status="published",
                is_locked=bloqueado, estimated_duration=105,
                duration_text="1 - 2 hours")
    db.session.add(tour)
    db.session.flush()

    # A propósito en desorden: lo que manda es `position`, no el orden de alta.
    for pid, pos, transicion in [("p2", 2, None),
                                 ("p0", 0, "Next, the sacred precinct."),
                                 ("p1", 1, "Now north.")]:
        db.session.add(TourStop(
            id=f"s-{pid}", tour_id=tour.id, place_id=pid, position=pos,
            audio_url=f"https://cdn/{pid}.mp3", audio_duration_seconds=90,
            transition_text=transicion,
        ))
    db.session.commit()
    return tour


def test_las_paradas_salen_en_orden(client, app):
    """`order` existía y no lo leía nadie: las paradas salían arbitrarias."""
    sembrar_tour(bloqueado=False)
    tour = client.get("/api/tours/t1").get_json()["data"]

    assert [s["position"] for s in tour["stops"]] == [0, 1, 2]
    assert [s["placeId"] for s in tour["stops"]] == ["p0", "p1", "p2"]
    assert tour["stopsCount"] == 3


def test_el_audio_es_lo_que_se_paga(client, app):
    """Las capas del diseño se llaman locked-audio-content."""
    sembrar_tour(bloqueado=True)

    cerrado = client.get("/api/tours/t1").get_json()["data"]
    assert cerrado["unlockedForViewer"] is False
    assert "stops" not in cerrado
    assert "contentDescription" not in cerrado

    tokens = registrar(client, "audio@example.com")
    UserRepository.update(tokens["user"]["id"], {"has_full_access": True})

    abierto = client.get("/api/tours/t1", headers=auth(tokens)).get_json()["data"]
    assert abierto["stops"][0]["audio"]["url"] == "https://cdn/p0.mp3"
    assert abierto["stops"][0]["audio"]["durationSeconds"] == 90
    assert abierto["stops"][0]["transitionText"] == "Next, the sacred precinct."


def test_completar_un_tour_mueve_los_contadores(client, app):
    """views_count, completion_count y el contador del perfil estaban muertos."""
    sembrar_tour(bloqueado=False)
    tokens = registrar(client, "contador@example.com")

    client.post("/api/tours/t1/start", headers=auth(tokens))
    assert client.post("/api/tours/t1/complete", json={"rating": 5},
                       headers=auth(tokens)).status_code == 200

    tour = client.get("/api/tours/t1").get_json()["data"]
    assert tour["statistics"]["completions"] == 1

    perfil = client.get("/api/users/profile", headers=auth(tokens)).get_json()["data"]
    assert perfil["stats"]["toursCompleted"] == 1


# --------------------------------------------------------------------------
# overlay del lago por época
# --------------------------------------------------------------------------

CENTRO = {
    "type": "Polygon",
    "coordinates": [[[-99.145, 19.425], [-99.145, 19.445],
                     [-99.124, 19.445], [-99.124, 19.425], [-99.145, 19.425]]],
}


def test_el_conmutador_de_epoca_filtra(client, app):
    """El mapa alterna «1500 / 2026»: el año decide qué se pinta."""
    from app.historical.services import LakeViewService

    LakeViewService.create_lake_geometry("Tenochtitlan", CENTRO, year_estimate=1500)

    de1500 = client.get("/api/historical/lake-view?year=1500").get_json()["data"]
    assert len(de1500["features"]) == 1
    assert de1500["availableYears"] == [1500]

    de2026 = client.get("/api/historical/lake-view?year=2026").get_json()["data"]
    assert de2026["features"] == []


# --------------------------------------------------------------------------
# perfil
# --------------------------------------------------------------------------

def test_el_idioma_se_guarda_en_la_cuenta(client, app):
    """Pantalla "Save language": manda sobre la cabecera del dispositivo."""
    crear_place("p1", "Great Temple")
    from app.shared.translations import ENTITY_PLACE
    from app.shared.translations_repository import TranslationRepository
    TranslationRepository.upsert(ENTITY_PLACE, "p1", "es", "name", "Templo Mayor")

    tokens = registrar(client, "idioma@example.com")

    r = client.put("/api/users/profile", json={"preferredLocale": "es"},
                   headers=auth(tokens))
    assert r.status_code == 200
    assert r.get_json()["data"]["preferredLocale"] == "es"

    # Aunque el dispositivo pida inglés, la cuenta manda
    place = client.get("/api/places/p1", headers={**auth(tokens),
                                                 "Accept-Language": "en-US"})
    assert place.get_json()["data"]["name"] == "Templo Mayor"


def test_cada_poligono_dice_si_es_agua_o_tierra(client, app):
    """El mapa de 1500 tiene dos colores, y el color no se deduce del nombre.

    En el diseño el lago va en azul y las islas en arena. Sin `surfaceType` en
    las properties, Flutter tendría que adivinar por el nombre del polígono —y
    eso aguanta exactamente hasta que alguien siembre el cuarto.
    """
    from app.historical.services import LakeViewService
    from app.shared.constants import (
        ERA_HISTORIC_YEAR, ERA_PRESENT_YEAR, SURFACE_LAND, SURFACE_WATER,
    )

    def poligono(nombre, superficie, lon0, lat0, lon1, lat1):
        LakeViewService.create_lake_geometry(
            name=nombre,
            geojson_polygon={
                "type": "Polygon",
                "coordinates": [[[lon0, lat0], [lon0, lat1], [lon1, lat1],
                                 [lon1, lat0], [lon0, lat0]]],
            },
            year_estimate=ERA_HISTORIC_YEAR,
            surface_type=superficie,
        )

    poligono("Lake Texcoco", SURFACE_WATER, -99.17, 19.39, -99.04, 19.49)
    poligono("Island of Tenochtitlan", SURFACE_LAND, -99.145, 19.425, -99.124, 19.445)

    fc = client.get(
        f"/api/historical/lake-view?year={ERA_HISTORIC_YEAR}"
    ).get_json()["data"]

    superficies = {
        f["properties"]["name"]: f["properties"]["surfaceType"]
        for f in fc["features"]
    }
    assert superficies["Lake Texcoco"] == SURFACE_WATER
    assert superficies["Island of Tenochtitlan"] == SURFACE_LAND


def test_el_ano_presente_no_lleva_overlay(client, app):
    """2026 devuelve vacío A PROPÓSITO, no por falta de datos.

    En el diseño, con "2026" seleccionado se ve el mapa de Google tal cual. El
    overlay es lo que se AÑADE al pasar a 1500, así que una colección vacía es
    la respuesta correcta y no un hueco por sembrar.
    """
    from app.shared.constants import ERA_PRESENT_YEAR

    fc = client.get(
        f"/api/historical/lake-view?year={ERA_PRESENT_YEAR}"
    ).get_json()["data"]

    assert fc["type"] == "FeatureCollection"
    assert fc["features"] == []


def test_una_superficie_inventada_se_rechaza(client, app):
    from app.historical.services import LakeViewService

    with pytest.raises(ValueError):
        LakeViewService.create_lake_geometry(
            name="Nope",
            geojson_polygon={
                "type": "Polygon",
                "coordinates": [[[-99.1, 19.4], [-99.1, 19.5],
                                 [-99.0, 19.5], [-99.0, 19.4], [-99.1, 19.4]]],
            },
            surface_type="lava",
        )


def test_mis_tours_lista_el_progreso(client, app):
    """GET /tours/user/tours devolvía 500 por una variable huérfana.

    Quedó un `tier` sin definir del refactor a desbloqueo único, y ningún test
    llamaba a este endpoint: reventaba en cuanto el usuario tuviera un tour
    empezado. Lo destapó recorrer los 36 endpoints uno por uno para el OpenAPI.
    """
    app.config["PAYMENTS_ALLOW_UNVERIFIED"] = True
    tour = Tour(id="t1", title="Ruta", description="d", content_description="guion",
                status="published", is_free=False, is_locked=True,
                estimated_duration=120)
    db.session.add(tour)
    db.session.commit()

    tokens = registrar(client, "mistours@example.com")
    client.post("/api/payments/confirm",
                json={"provider": "stripe", "externalId": "pi_mistours"},
                headers=auth(tokens))
    client.post("/api/tours/t1/start", headers=auth(tokens))
    client.put("/api/tours/t1/progress", json={"currentStopIndex": 2},
               headers=auth(tokens))

    r = client.get("/api/tours/user/tours", headers=auth(tokens))
    assert r.status_code == 200

    tours = r.get_json()["data"]["tours"]
    assert len(tours) == 1
    assert tours[0]["id"] == "t1"
    assert tours[0]["progress"]["currentStopIndex"] == 2
    assert tours[0]["progress"]["isCompleted"] is False
    assert tours[0]["unlockedForViewer"] is True


def test_el_progreso_devuelve_el_estado_guardado(client, app):
    """Los endpoints de avance devuelven el objeto entero, no solo un id.

    Con `{progressId}` el cliente tenía que fiarse de lo que acababa de mandar.
    Ahora lee lo que el servidor guardó, que es lo único que sobrevive a dos
    dispositivos o a dos PUT que se cruzan.
    """
    app.config["PAYMENTS_ALLOW_UNVERIFIED"] = True
    db.session.add(Tour(id="t1", title="Ruta", description="d",
                        content_description="guion", status="published",
                        is_free=True, is_locked=False, estimated_duration=90))
    db.session.commit()

    tokens = registrar(client, "avance@example.com")

    iniciado = client.post("/api/tours/t1/start", headers=auth(tokens))
    assert iniciado.status_code == 201
    progreso = iniciado.get_json()["data"]
    assert progreso["tourId"] == "t1"
    assert progreso["isCompleted"] is False
    assert "id" in progreso

    guardado = client.put("/api/tours/t1/progress",
                          json={"currentStopIndex": 2, "lastLocationLat": 19.43,
                                "lastLocationLon": -99.13},
                          headers=auth(tokens)).get_json()["data"]
    assert guardado["currentStopIndex"] == 2
    assert guardado["lastLocation"]["latitude"] == 19.43
    assert guardado["startedAt"] is not None

    cerrado = client.post("/api/tours/t1/complete",
                          json={"rating": 5},
                          headers=auth(tokens)).get_json()["data"]
    assert cerrado["isCompleted"] is True
    assert cerrado["rating"] == 5
    assert cerrado["completedAt"] is not None
    # el avance no se pierde al cerrar
    assert cerrado["currentStopIndex"] == 2


def test_la_puerta_de_desarrollo_del_cobro_viene_cerrada(client, app):
    """PAYMENTS_ALLOW_UNVERIFIED por defecto en false, y se lee del entorno.

    Dos agujeros a la vez. Uno: si el valor por defecto fuera true, un despliegue
    que se olvide de la variable regala la app entera. Dos: la bandera se leía
    solo de app.config y NADIE la cargaba desde el entorno, así que ponerla en
    docker-compose no hacía absolutamente nada — parecía encendida y estaba
    apagada.
    """
    import importlib
    import os

    from app import config as modulo_config

    previo = os.environ.pop("PAYMENTS_ALLOW_UNVERIFIED", None)
    try:
        importlib.reload(modulo_config)
        assert modulo_config.Config.PAYMENTS_ALLOW_UNVERIFIED is False

        os.environ["PAYMENTS_ALLOW_UNVERIFIED"] = "true"
        importlib.reload(modulo_config)
        assert modulo_config.Config.PAYMENTS_ALLOW_UNVERIFIED is True
    finally:
        os.environ.pop("PAYMENTS_ALLOW_UNVERIFIED", None)
        if previo is not None:
            os.environ["PAYMENTS_ALLOW_UNVERIFIED"] = previo
        importlib.reload(modulo_config)
