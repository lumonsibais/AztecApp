"""Prueba de humo del contrato, contra la base sembrada.

No es un test: es la comprobación de que lo que la app Flutter va a llamar
responde lo que el diseño necesita. Se ejecuta contra `aztec_seed`, la base
migrada desde cero y sembrada con seed.py.
"""
import logging
import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql://aztec:aztec@localhost:5432/aztec_seed"
)

from app import create_app  # noqa: E402

app = create_app("development")
app.config["PAYMENTS_ALLOW_UNVERIFIED"] = True
# El echo de SQLAlchemy se activa en el motor, no en la config: apagarlo aquí
# ya no sirve de nada, hay que bajarle el nivel al logger.
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
c = app.test_client()


def titulo(t):
    print("\n" + "=" * 70)
    print(t)
    print("=" * 70)


def get(url, tok=None, **kw):
    h = {"Authorization": "Bearer " + tok} if tok else {}
    h.update(kw.pop("headers", {}))
    return c.get(url, headers=h, **kw)


def post(url, tok=None, **kw):
    h = {"Authorization": "Bearer " + tok} if tok else {}
    h.update(kw.pop("headers", {}))
    return c.post(url, headers=h, **kw)


with app.app_context():
    from app.extensions import db
    from app.payments.models import Purchase
    from app.users.models import ContentRead, SavedPlace, User

    for modelo in (Purchase, SavedPlace, ContentRead, User):
        db.session.query(modelo).delete()
    from app.tours.models import TourProgress
    db.session.query(TourProgress).delete()
    db.session.commit()

    # ------------------------------------------------------------------
    titulo("1. EXPLORE — anónimo, sin cuenta")
    d = get("/api/places/").get_json()["data"]["places"]
    for p in d:
        print(f"  {p['name'][:32]:<34} {str(p['curation']):<11} "
              f"⭐{p['rating']}  saved={p['isSaved']}  "
              f"locked={p['contentAccess']['isLocked']}")

    titulo("2. Filtros de la barra: Must See / Quick Stops")
    for f in ("must_see", "quick_stop"):
        ids = [p["id"] for p in get(f"/api/places/?curation={f}").get_json()["data"]["places"]]
        print(f"  {f:<12} -> {ids}")
    print("  filtro inválido ->", get("/api/places/?curation=xxx").status_code)

    titulo("3. NEAR — distancia desde el Zócalo")
    for p in get("/api/places/nearby?latitude=19.4326&longitude=-99.1332&radius=5"
                 ).get_json()["data"]["places"]:
        print(f"  {p['name'][:32]:<34} {p['location']['distanceKm']} km  "
              f"({p['location']['neighborhood']})")

    titulo("4. Ficha de sitio — dónde cae la línea del paywall")
    p = get("/api/places/museo-antropologia").get_json()["data"]
    print("  ANÓNIMO, sitio de pago:")
    print(f"    {p['name']} — {p['tagline']}")
    print(f"    duración: {p['estimatedVisitDuration']} min / "
          f"'{p['visitDurationText']}'")
    print("    LOGÍSTICA (del mundo real, viaja siempre):")
    print(f"      taquilla:  {p['entryFee']}")
    print(f"      horarios:  {p['openingHours']}")
    print(f"      llegar:    {str(p['howToGetThere'])[:56]}...")
    print("    CONTENIDO (lo escribimos nosotros, va con el desbloqueo):")
    print(f"      description:      {p['description']}")
    print(f"      whyVisit:         {'presente' if 'whyVisit' in p else 'ausente'}")
    print(f"      historicalContext:{' presente' if 'historicalContext' in p else ' ausente'}")

    titulo("5. Idioma — Accept-Language y preferencia de cuenta")
    print("  EN:", get("/api/places/templo-mayor").get_json()["data"]["name"])
    print("  ES:", get("/api/places/templo-mayor",
                       headers={"Accept-Language": "es-MX"}).get_json()["data"]["name"])

    # ------------------------------------------------------------------
    titulo("6. Cuenta nueva -> todo cerrado")
    tk = post("/api/users/register",
              json={"email": "smoke@az.com", "password": "testpassword123"}
              ).get_json()["data"]["accessToken"]
    print("  access:", get("/api/payments/access", tk).get_json()["data"])
    tour_id = get("/api/tours/").get_json()["data"]["tours"][0]["id"]
    print(f"  POST /tours/{tour_id}/start ->",
          post(f"/api/tours/{tour_id}/start", tk).status_code, "(esperado 403)")

    titulo("7. SAVED — el corazón")
    print("  guardar   ->", post("/api/places/templo-mayor/save", tk).status_code)
    print("  otra vez  ->", post("/api/places/templo-mayor/save", tk).status_code)
    guardados = get("/api/places/saved", tk).get_json()["data"]["places"]
    print("  /saved    ->", [g["name"] for g in guardados])
    listado = get("/api/places/", tk).get_json()["data"]["places"]
    print("  corazones en el listado:",
          {p["id"]: p["isSaved"] for p in listado})

    titulo("8. HISTORY — cronología, temas y leídos")
    cron = get("/api/historical/chronology").get_json()["data"]["content"]
    for a in cron:
        print(f"  {a['sortOrder']}. {a['title'][:36]:<38} "
              f"{a['readingTimeMinutes']} min  [{a['topic']}]")
    for cid in ("founding", "lake-city", "fall"):
        det = get(f"/api/historical/content/{cid}").get_json()["data"]
        print(f"  siguiente tras '{cid}': {det['nextContentId']}")
    print("  marcar leído ->", post("/api/historical/content/founding/read", tk).status_code)
    cron2 = get("/api/historical/chronology", tk).get_json()["data"]["content"]
    print("  estado de lectura:", {a["id"]: a["isRead"] for a in cron2})

    titulo("9. MAP — conmutador 1500 / 2026")
    fc = get("/api/historical/lake-view?year=1500").get_json()["data"]
    print(f"  1500: {len(fc['features'])} polígonos, en orden de pintado")
    for f in fc["features"]:
        print(f"    {f['properties']['surfaceType']:<6} {f['properties']['name']}")
    fc = get("/api/historical/lake-view?year=2026").get_json()["data"]
    print(f"  2026: {len(fc['features'])} polígonos — el mapa de Google sin capa, "
          f"que es lo que pide el diseño")

    # ------------------------------------------------------------------
    titulo("10. COMPRA — 15 USD, desbloqueo único")
    co = post("/api/payments/checkout", tk).get_json()["data"]
    print(f"  checkout -> {co['status']} {co['amount']} {co['currency']}")
    print("  checkout otra vez ->",
          post("/api/payments/checkout", tk).get_json()["data"]["id"] == co["id"],
          "(misma fila, no duplica)")
    r = post("/api/payments/confirm", tk,
             json={"provider": "stripe", "externalId": "pi_smoke"})
    print(f"  confirm  -> {r.status_code} {r.get_json()['message']}")
    print("  confirm otra vez ->",
          post("/api/payments/confirm", tk,
               json={"provider": "stripe", "externalId": "pi_smoke"}
               ).get_json()["message"])
    hist = get("/api/payments/purchases", tk).get_json()["data"]["purchases"]
    print(f"  historial: {len(hist)} apunte(s) -> "
          f"{[(h['status'], h['provider']) for h in hist]}")
    print("  access:", get("/api/payments/access", tk).get_json()["data"])

    titulo("11. La misma ficha, ya comprada — aparece lo nuestro")
    p = get("/api/places/museo-antropologia", tk).get_json()["data"]
    print(f"    {p['name']}")
    print(f"    description: {str(p['description'])[:62]}...")
    print(f"    whyVisit:    {str(p['whyVisit'])[:62]}...")
    print(f"    contexto:    {p['historicalContext']}")
    print(f"    (la taquilla sigue igual: {p['entryFee']['mxn']} MXN)")

    titulo("12. TOUR ya desbloqueado — paradas y audio")
    print(f"  POST /tours/{tour_id}/start ->",
          post(f"/api/tours/{tour_id}/start", tk).status_code)
    t = get(f"/api/tours/{tour_id}", tk).get_json()["data"]
    print(f"  {t['title']} | {t['durationText']} | {t['stopsCount']} paradas | "
          f"audio={t['includesAudio']} | tarifas={t['hasEntryFees']}")
    for s in t["stops"]:
        print(f"    {s['position']}. {s['place']['name'][:30]:<32} "
              f"audio={s['audio']['url']} ({s['audio']['durationSeconds']}s) "
              f"locked={s['audio']['isLocked']}")
        if s["transitionText"]:
            print(f"       ↳ \"{s['transitionText'][:56]}\"")

    titulo("13. El mismo tour, sin comprar -> el audio no viaja")
    tk2 = post("/api/users/register",
               json={"email": "gorron@az.com", "password": "testpassword123"}
               ).get_json()["data"]["accessToken"]
    t2 = get(f"/api/tours/{tour_id}", tk2).get_json()["data"]
    print(f"  stops en la respuesta: {'stops' in t2}  "
          f"(metadata sí: {t2['stopsCount']} paradas, audio={t2['includesAudio']})")

    print("\n" + "=" * 70)
    print("humo OK")
    print("=" * 70)
