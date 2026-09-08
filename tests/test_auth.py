"""Regresiones de autenticación, autorización y paywall.

Cada test de este archivo fija un agujero real encontrado en la revisión del
backend. Si alguno vuelve a ponerse en rojo, es que volvió el agujero.
"""
from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.historical.models import HistoricalContent
from app.places.models import Place
from app.tours.models import Tour
from app.shared.utils import utc_ahora
from app.users.repositories import UserRepository


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def registrar(client, email="user@example.com", password="testpassword123"):
    r = client.post("/api/users/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.get_json()
    return r.get_json()["data"]


def auth(tokens):
    return {"Authorization": "Bearer " + tokens["accessToken"]}


def crear_place(app, bloqueado, nombre="Templo Mayor"):
    # Sin `with app.app_context()`: el fixture ya tiene uno activo y las
    # peticiones del test client lo reutilizan. Abrir uno anidado crea una
    # sesión aparte y el test acaba leyendo datos rancios.
    place = Place(
        id="place-" + ("lock" if bloqueado else "open"),
        name=nombre,
        description="Descripción de pago",
        latitude=19.4361,
        longitude=-99.1356,
        place_type="ruin",
        historical_significance="Templo principal de Tenochtitlan",
        estimated_visit_duration=90,
        is_locked=bloqueado,
    )
    db.session.add(place)
    db.session.commit()
    return place.id


def crear_tour(app, bloqueado):
    tour = Tour(
        id="tour-" + ("lock" if bloqueado else "open"),
        title="Ruta por la Tenochtitlan sumergida",
        description="Resumen visible para todos",
        content_description="Guion completo del tour",
        status="published",
        is_free=not bloqueado,
        is_locked=bloqueado,
        estimated_duration=120,
    )
    db.session.add(tour)
    db.session.commit()
    return tour.id


def desbloquea(app, user_id):
    """Concede el acceso completo, como haría una compra confirmada."""
    UserRepository.update(user_id, {
        "has_full_access": True,
        "full_access_since": utc_ahora(),
    })


# --------------------------------------------------------------------------
# escalada de privilegios
# --------------------------------------------------------------------------

def test_no_se_puede_subir_de_tier_desde_el_perfil(client, app):
    """El agujero original: PUT /profile con un campo privilegiado => acceso gratis."""
    tokens = registrar(client)
    assert tokens["user"]["hasFullAccess"] is False

    r = client.put("/api/users/profile",
                   json={"has_full_access": True},
                   headers=auth(tokens))

    assert r.status_code == 400
    assert "has_full_access" in r.get_json()["details"]

    perfil = client.get("/api/users/profile", headers=auth(tokens)).get_json()
    assert perfil["data"]["hasFullAccess"] is False


@pytest.mark.parametrize("campo", ["is_verified", "is_active", "total_tours_completed",
                                   "email", "password_hash", "id"])
def test_ningun_campo_privilegiado_pasa_por_el_perfil(client, campo):
    tokens = registrar(client, email=campo + "@example.com")
    r = client.put("/api/users/profile", json={campo: "x"}, headers=auth(tokens))
    assert r.status_code == 400


def test_los_campos_de_perfil_si_se_actualizan(client):
    tokens = registrar(client, email="perfil@example.com")
    r = client.put("/api/users/profile",
                   json={"firstName": "Bertin", "lastName": "Salas"},
                   headers=auth(tokens))

    assert r.status_code == 200
    assert r.get_json()["data"]["firstName"] == "Bertin"


def test_el_progreso_no_puede_cerrar_un_tour(client, app):
    """update_tour_progress aceptaba is_completed del cliente."""
    tour_id = crear_tour(app, bloqueado=False)
    tokens = registrar(client, email="progreso@example.com")

    client.post("/api/tours/" + tour_id + "/start", headers=auth(tokens))

    r = client.put("/api/tours/" + tour_id + "/progress",
                   json={"is_completed": True},
                   headers=auth(tokens))
    assert r.status_code == 400

    ok = client.put("/api/tours/" + tour_id + "/progress",
                    json={"currentStopIndex": 2},
                    headers=auth(tokens))
    assert ok.status_code == 200


# --------------------------------------------------------------------------
# paywall
# --------------------------------------------------------------------------

def test_el_query_param_ya_no_desbloquea_nada(client, app):
    """`?subscription=vip` abría el contenido de pago sin token."""
    place_id = crear_place(app, bloqueado=True)

    r = client.get("/api/places/?subscription=vip")
    assert r.status_code == 200

    place = next(p for p in r.get_json()["data"]["places"] if p["id"] == place_id)
    assert place["contentAccess"]["unlockedForViewer"] is False
    assert place["description"] is None


def test_el_bloqueado_viaja_como_teaser(client, app):
    """Metadata y logística sí; nuestro contenido no.

    La línea la marca dónde nace el dato. La taquilla del museo, su horario y
    cómo se llega son del mundo real: esconderlos no cobra nada, solo manda al
    viajero a buscarlo a Google y a salirse de la app. Lo que escribimos
    nosotros —el porqué visitarlo, el contexto histórico— sí es el producto.
    """
    place_id = crear_place(app, bloqueado=True)

    place = client.get("/api/places/" + place_id).get_json()["data"]

    assert place["name"] == "Templo Mayor"

    # logística: viaja siempre
    assert "openingHours" in place
    assert "entryFee" in place
    assert "howToGetThere" in place
    assert "safetyRecommendations" in place

    # contenido: solo con el desbloqueo
    assert place["description"] is None
    assert "whyVisit" not in place
    assert "historicalContext" not in place


def test_premium_ve_el_contenido_completo(client, app):
    place_id = crear_place(app, bloqueado=True)
    tokens = registrar(client, email="premium@example.com")
    desbloquea(app, tokens["user"]["id"])

    place = client.get("/api/places/" + place_id,
                       headers=auth(tokens)).get_json()["data"]

    assert place["contentAccess"]["unlockedForViewer"] is True
    assert place["description"] == "Descripción de pago"
    assert "whyVisit" in place
    assert "historicalContext" in place
    assert "openingHours" in place


def test_una_cuenta_nueva_no_ve_lo_de_pago(client, app):
    """El desbloqueo se concede, no se presupone."""
    place_id = crear_place(app, bloqueado=True)
    tokens = registrar(client, email="nueva@example.com")

    place = client.get("/api/places/" + place_id,
                       headers=auth(tokens)).get_json()["data"]
    assert place["contentAccess"]["unlockedForViewer"] is False

    perfil = client.get("/api/users/profile", headers=auth(tokens)).get_json()["data"]
    assert perfil["hasFullAccess"] is False
    assert perfil["fullAccessSince"] is None

    desbloquea(app, tokens["user"]["id"])
    place = client.get("/api/places/" + place_id,
                       headers=auth(tokens)).get_json()["data"]
    assert place["contentAccess"]["unlockedForViewer"] is True


def test_no_se_puede_iniciar_un_tour_de_pago(client, app):
    """start_tour no comprobaba nada: bastaba tener token."""
    tour_id = crear_tour(app, bloqueado=True)
    tokens = registrar(client, email="gorron@example.com")

    r = client.post("/api/tours/" + tour_id + "/start", headers=auth(tokens))
    assert r.status_code == 403

    desbloquea(app, tokens["user"]["id"])
    r2 = client.post("/api/tours/" + tour_id + "/start", headers=auth(tokens))
    assert r2.status_code == 201


def test_el_contenido_historico_respeta_su_propio_candado(client, app):
    """historical ignoraba is_locked y servía el cuerpo a todo el mundo."""
    db.session.add(HistoricalContent(
        id="hc-1",
        title="La caída de Tenochtitlan",
        description="Resumen abierto",
        content_type="text",
        text_content="Texto largo de pago",
        is_locked=True,
    ))
    db.session.commit()

    anonimo = client.get("/api/historical/content/hc-1").get_json()["data"]
    assert anonimo["unlockedForViewer"] is False
    assert "content" not in anonimo
    assert anonimo["title"] == "La caída de Tenochtitlan"

    tokens = registrar(client, email="historia@example.com")
    desbloquea(app, tokens["user"]["id"])
    abierto = client.get("/api/historical/content/hc-1",
                         headers=auth(tokens)).get_json()["data"]
    assert abierto["content"] == "Texto largo de pago"


# --------------------------------------------------------------------------
# ciclo de vida del token
# --------------------------------------------------------------------------

def test_refresh_entrega_un_access_nuevo(client):
    tokens = registrar(client, email="refresh@example.com")

    r = client.post("/api/users/refresh",
                    headers={"Authorization": "Bearer " + tokens["refreshToken"]})

    assert r.status_code == 200
    nuevo = r.get_json()["data"]["accessToken"]
    assert client.get("/api/users/profile",
                      headers={"Authorization": "Bearer " + nuevo}).status_code == 200


def test_el_access_no_sirve_como_refresh(client):
    tokens = registrar(client, email="tipo@example.com")
    assert client.post("/api/users/refresh", headers=auth(tokens)).status_code == 401


def test_logout_revoca_el_token(client):
    """Sin blocklist, el token seguía vivo 30 días después del logout."""
    tokens = registrar(client, email="logout@example.com")
    assert client.get("/api/users/profile", headers=auth(tokens)).status_code == 200

    assert client.post("/api/users/logout", headers=auth(tokens)).status_code == 200
    assert client.get("/api/users/profile", headers=auth(tokens)).status_code == 401


def test_un_token_revocado_navega_como_anonimo(client, app):
    """En endpoints públicos un token muerto degrada a free, no da 401."""
    place_id = crear_place(app, bloqueado=True)
    tokens = registrar(client, email="revocado@example.com")
    desbloquea(app, tokens["user"]["id"])

    client.post("/api/users/logout", headers=auth(tokens))

    r = client.get("/api/places/" + place_id, headers=auth(tokens))
    assert r.status_code == 200
    assert r.get_json()["data"]["contentAccess"]["unlockedForViewer"] is False


def test_una_cuenta_desactivada_no_entra(client, app):
    tokens = registrar(client, email="baja@example.com")
    UserRepository.update(tokens["user"]["id"], {"is_active": False})

    assert client.get("/api/users/profile", headers=auth(tokens)).status_code == 403

    r = client.post("/api/users/login",
                    json={"email": "baja@example.com", "password": "testpassword123"})
    assert r.status_code == 401


def test_sin_token_los_endpoints_protegidos_responden_401(client):
    assert client.get("/api/users/profile").status_code == 401
    assert client.get("/api/tours/user/tours").status_code == 401
    assert client.get("/api/payments/purchases").status_code == 401
    assert client.get("/api/places/saved").status_code == 401


def test_el_registro_valida_la_entrada(client):
    assert client.post("/api/users/register",
                       json={"email": "malo", "password": "12345678"}).status_code == 400
    assert client.post("/api/users/register",
                       json={"email": "a@b.com", "password": "corta"}).status_code == 400
    assert client.post("/api/users/register", json={}).status_code == 400
