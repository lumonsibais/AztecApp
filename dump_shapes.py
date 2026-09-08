"""Radiografía del contrato: golpea cada endpoint y describe la forma real.

No es un test. Es la materia prima para escribir el OpenAPI sin inventarme
nada: cada schema sale de lo que el servidor devuelve de verdad, no de lo que
yo creo recordar que devuelve.
"""
import json
import logging
import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql://aztec:aztec@localhost:5432/aztec_paridad"
)

from app import create_app  # noqa: E402

app = create_app("development")
app.config["PAYMENTS_ALLOW_UNVERIFIED"] = True
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
c = app.test_client()


def forma(v, prof=0):
    """Describe la forma de un valor, no su contenido."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, int):
        return "int"
    if isinstance(v, float):
        return "float"
    if isinstance(v, str):
        return "str"
    if isinstance(v, list):
        if not v:
            return []
        return [forma(v[0], prof + 1)]
    if isinstance(v, dict):
        return {k: forma(x, prof + 1) for k, x in sorted(v.items())}
    return type(v).__name__


with app.app_context():
    from app.extensions import db
    from app.payments.models import Purchase
    from app.tours.models import TourProgress
    from app.users.models import ContentRead, SavedPlace, User

    for m in (Purchase, SavedPlace, ContentRead, TourProgress, User):
        db.session.query(m).delete()
    db.session.commit()

    tk = c.post("/api/users/register",
                json={"email": "spec@az.com", "password": "testpassword123"}
                ).get_json()["data"]["accessToken"]
    H = {"Authorization": "Bearer " + tk}

    # desbloquear para ver también las respuestas completas
    c.post("/api/payments/checkout", headers=H)
    c.post("/api/payments/confirm", headers=H,
           json={"provider": "stripe", "externalId": "pi_spec"})
    c.post("/api/places/templo-mayor/save", headers=H)
    c.post("/api/historical/content/founding/read", headers=H)
    c.post("/api/tours/unearth-tenochtitlan/start", headers=H)

    LLAMADAS = [
        ("POST", "/api/users/register", {"json": {"email": "x@y.com", "password": "testpassword123"}}),
        ("POST", "/api/users/login", {"json": {"email": "spec@az.com", "password": "testpassword123"}}),
        ("POST", "/api/users/refresh", {"auth": "refresh"}),
        ("GET", "/api/users/profile", {"auth": 1}),
        ("PUT", "/api/users/profile", {"auth": 1, "json": {"firstName": "Bertin"}}),
        ("POST", "/api/users/location-permission", {"auth": 1, "json": {"response": "granted"}}),

        ("GET", "/api/places/", {}),
        ("GET", "/api/places/?curation=must_see&page=1&limit=2", {}),
        ("GET", "/api/places/templo-mayor", {}),
        ("GET", "/api/places/museo-antropologia", {}),
        ("GET", "/api/places/museo-antropologia", {"auth": 1}),
        ("GET", "/api/places/nearby?latitude=19.4326&longitude=-99.1332&radius=5", {}),
        ("GET", "/api/places/recommended?latitude=19.4326&longitude=-99.1332", {}),
        ("GET", "/api/places/saved", {"auth": 1}),
        ("POST", "/api/places/tlatelolco/save", {"auth": 1}),
        ("DELETE", "/api/places/tlatelolco/save", {"auth": 1}),

        ("GET", "/api/tours/", {}),
        ("GET", "/api/tours/free", {}),
        ("GET", "/api/tours/unearth-tenochtitlan", {"auth": 1}),
        ("GET", "/api/tours/unearth-tenochtitlan", {}),
        ("GET", "/api/tours/user/tours", {"auth": 1}),
        ("PUT", "/api/tours/unearth-tenochtitlan/progress", {"auth": 1, "json": {"currentStopIndex": 1}}),

        ("GET", "/api/historical/chronology", {}),
        ("GET", "/api/historical/topics", {}),
        ("GET", "/api/historical/content", {}),
        ("GET", "/api/historical/content/founding", {"auth": 1}),
        ("GET", "/api/historical/content/founding", {}),
        ("GET", "/api/historical/content/topic?topic=Conquest", {}),
        ("GET", "/api/historical/content/era?era=Aztec Empire (1345-1521)", {}),
        ("GET", "/api/historical/content/place/templo-mayor", {}),
        ("GET", "/api/historical/timelines", {}),
        ("GET", "/api/historical/lake-view?year=1500", {}),
        ("GET", "/api/historical/lake-view?year=1500&bbox=-99.2,19.3,-99.0,19.5", {}),
        ("POST", "/api/historical/content/lake-city/read", {"auth": 1}),
        ("DELETE", "/api/historical/content/lake-city/read", {"auth": 1}),

        ("GET", "/api/payments/access", {"auth": 1}),
        ("GET", "/api/payments/purchases", {"auth": 1}),

        # errores representativos
        ("GET", "/api/places/no-existe", {}),
        ("GET", "/api/users/profile", {}),
        ("POST", "/api/users/register", {"json": {"email": "malo"}}),
        ("GET", "/api/places/nearby", {}),
        ("POST", "/api/payments/checkout", {"auth": 1}),
    ]

    salida = []
    refresh = None
    for metodo, url, opts in LLAMADAS:
        headers = {}
        if opts.get("auth") == "refresh":
            continue  # se prueba aparte, necesita el refresh token
        if opts.get("auth"):
            headers = dict(H)
        r = c.open(url, method=metodo, headers=headers, json=opts.get("json"))
        cuerpo = r.get_json()
        salida.append({
            "method": metodo,
            "url": url,
            "auth": bool(opts.get("auth")),
            "status": r.status_code,
            "shape": forma(cuerpo),
        })

    print(json.dumps(salida, indent=1, ensure_ascii=False))
