"""Datos de prueba.

Doble función: sirve para desarrollar el backend y es el fixture contra el que
va a programar el frontend, así que intenta parecerse a lo que verá la app.

El contenido va en INGLÉS porque es el idioma base del producto: lo que vive en
las columnas de cada modelo. El español entra como traducción en la tabla
`translations`, igual que entrará cualquier otro idioma.
"""
import uuid

from app import create_app, db
from app.historical.models import HistoricalContent, Timeline
from app.historical.services import LakeViewService
from app.places.models import Place
from app.shared.constants import (
    CURATION_MUST_SEE,
    CURATION_QUICK_STOP,
    ERA_HISTORIC_YEAR,
    SURFACE_LAND,
    SURFACE_WATER,
)
from app.shared.translations import ENTITY_HISTORICAL, ENTITY_PLACE, ENTITY_TOUR
from app.shared.translations_repository import TranslationRepository
from app.tours.models import Tour, TourStop

app = create_app()


# --------------------------------------------------------------------------
# Sitios
# --------------------------------------------------------------------------

SITIOS = [
    {
        "id": "templo-mayor",
        "name": "Templo Mayor Remains",
        "tagline": "Witness the sacred beating heart of the Aztec Empire.",
        "description": "What's left of the great Temple of Tenochtitlan, "
                       "uncovered by accident in 1978 and excavated ever since.",
        "latitude": 19.4361, "longitude": -99.1356,
        "neighborhood": "Centro Histórico",
        "place_type": "ruin",
        "curation": CURATION_MUST_SEE,
        "editorial_rating": 4.5,
        "historical_significance": "The epicentre of Aztec religious and political life.",
        "why_visit": "Your exploration of Mexico City's archaeology must start "
                     "here. This is where the empire measured the centre of its "
                     "world, and there is a lot to take in even from outside.",
        "how_to_get_there": "República de Guatemala 60, Centro Histórico. "
                            "Metro Zócalo, line 2, two minutes on foot.",
        "estimated_visit_duration": 90,
        "visit_duration_text": "30 min if you only observe from the outside "
                               "viewpoint. 1-3 hours with the museum.",
        "opening_hours": "Tuesday to Sunday, 9 AM to 5 PM",
        "entry_fee_mxn": 95, "entry_fee_usd": 5.50,
        "entry_fee_text": "Free from the outside viewpoint, or 95 MXN for the "
                          "museum and the archaeological site.",
        "is_free_entry": False, "is_outdoor": True, "archaeological": True,
        "tenochtitlan_name": "Huei Teocalli",
        "has_bathrooms": True, "has_cafes": True,
        "is_locked": False,
        "es": {
            "name": "Restos del Templo Mayor",
            "tagline": "Asómate al corazón sagrado del imperio azteca.",
            "description": "Lo que queda del gran templo de Tenochtitlan, "
                           "descubierto por accidente en 1978.",
        },
    },
    {
        "id": "museo-antropologia",
        "name": "National Museum of Anthropology",
        "tagline": "Come face-to-face with the legendary 24-ton Aztec Sun Stone.",
        "description": "The largest collection of pre-Hispanic artifacts in "
                       "the world, inside a landmark of modern architecture.",
        "latitude": 19.4260, "longitude": -99.1863,
        "neighborhood": "Bosque de Chapultepec",
        "place_type": "museum",
        "curation": CURATION_MUST_SEE,
        "editorial_rating": 5.0,
        "historical_significance": "Houses the Sun Stone and the Aztec hall.",
        "why_visit": "If you only enter one building in Mexico City, this is "
                     "the one. The Mexica hall alone justifies the trip.",
        "how_to_get_there": "Av. Paseo de la Reforma s/n. Metro Auditorio, "
                            "line 7, ten minutes on foot through the park.",
        "estimated_visit_duration": 180,
        "visit_duration_text": "2-4 hours. Half a day for the whole museum.",
        "opening_hours": "Tuesday to Sunday, 9 AM to 6 PM",
        "entry_fee_mxn": 95, "entry_fee_usd": 5.50,
        "entry_fee_text": "95 MXN. Free for Mexican residents on Sundays.",
        "is_free_entry": False, "is_outdoor": False,
        "has_bathrooms": True, "has_cafes": True,
        "is_locked": True,
        "es": {
            "name": "Museo Nacional de Antropología",
            "tagline": "Ponte frente a la Piedra del Sol y sus 24 toneladas.",
        },
    },
    {
        "id": "tlatelolco",
        "name": "Plaza de las Tres Culturas",
        "tagline": "Walk the best preserved Aztec site where 3 eras collide.",
        "description": "Aztec ruins, a colonial church and modern housing "
                       "sharing one square.",
        "latitude": 19.4510, "longitude": -99.1370,
        "neighborhood": "Tlatelolco",
        "place_type": "historical_site",
        "curation": CURATION_MUST_SEE,
        "editorial_rating": 4.0,
        "historical_significance": "Site of the last stand of the Mexica in 1521.",
        "why_visit": "Three periods of the country stacked on a single square, "
                     "and the clearest place to understand what was lost.",
        "how_to_get_there": "Metro Tlatelolco, line 3, five minutes on foot.",
        "estimated_visit_duration": 60,
        "visit_duration_text": "About an hour, walking around the square.",
        "entry_fee_mxn": 0, "entry_fee_usd": 0,
        "entry_fee_text": "Free.",
        "is_free_entry": True, "is_outdoor": True, "archaeological": True,
        "tenochtitlan_name": "Tlatelolco",
        "is_locked": False,
        "es": {
            "name": "Plaza de las Tres Culturas",
            "tagline": "El sitio azteca mejor conservado, donde chocan 3 épocas.",
        },
    },
    {
        "id": "monumento-mexicanidad",
        "name": "Monument of Mexicanity",
        "tagline": "Discover the Aztec founding myth.",
        "description": "A modern sculpture of the eagle on the cactus, where "
                       "the founding legend begins.",
        "latitude": 19.4340, "longitude": -99.1420,
        "neighborhood": "Centro Histórico",
        "place_type": "monument",
        "curation": CURATION_QUICK_STOP,
        "editorial_rating": 3.5,
        "historical_significance": "Represents the founding of Tenochtitlan.",
        "why_visit": "A five-minute stop that sets up everything else you are "
                     "about to see.",
        "how_to_get_there": "On the corner of the Alameda, walking distance "
                            "from Bellas Artes.",
        "estimated_visit_duration": 15,
        "visit_duration_text": "5-10 minutes.",
        "entry_fee_mxn": 0, "entry_fee_usd": 0,
        "entry_fee_text": "Free.",
        "is_free_entry": True, "is_outdoor": True,
        "is_locked": False,
        "es": {
            "name": "Monumento a la Mexicanidad",
            "tagline": "Conoce el mito fundacional azteca.",
        },
    },
]


def seed_places():
    creados = []
    for datos in SITIOS:
        campos = dict(datos)
        traducciones = campos.pop("es", {})
        place = Place(**campos)
        db.session.add(place)
        creados.append((place, traducciones))
    db.session.commit()

    for place, traducciones in creados:
        for campo, valor in traducciones.items():
            TranslationRepository.upsert(ENTITY_PLACE, place.id, "es", campo, valor)

    print(f"OK  {len(creados)} sitios (con traducciones al español)")
    return [p for p, _ in creados]


# --------------------------------------------------------------------------
# Tours con sus paradas
# --------------------------------------------------------------------------

def seed_tours(places):
    tour = Tour(
        id="unearth-tenochtitlan",
        title="Unearth Tenochtitlan",
        description="Peel back the layers of the modern capital on a targeted "
                    "walk through its foundational sites.",
        content_description="A self-paced walk through the ceremonial centre "
                            "of the Mexica world, stop by stop.",
        status="published",
        is_free=False,
        is_locked=True,
        estimated_duration=105,
        duration_text="1 - 2 hours",
        difficulty_level="easy",
        total_distance=2.4,
        has_entry_fees=False,
        editorial_rating=4.5,
    )
    db.session.add(tour)
    db.session.flush()

    # El orden ES el recorrido: sin `position` las paradas salían arbitrarias,
    # que en un tour a pie es sencillamente estar perdido.
    recorrido = [
        ("monumento-mexicanidad", 0, 95,
         "Next, let's go to the Aztec's sacred precinct."),
        ("templo-mayor", 1, 240,
         "From the temple we walk north, to where the empire made its last stand."),
        ("tlatelolco", 2, 180, None),
    ]

    for place_id, posicion, duracion, transicion in recorrido:
        db.session.add(TourStop(
            id=str(uuid.uuid4()),
            tour_id=tour.id,
            place_id=place_id,
            position=posicion,
            audio_url=f"https://cdn.example/audio/{place_id}.mp3",
            audio_duration_seconds=duracion,
            transition_text=transicion,
        ))

    db.session.commit()

    TranslationRepository.upsert(
        ENTITY_TOUR, tour.id, "es", "title", "Desenterrar Tenochtitlan"
    )
    TranslationRepository.upsert(
        ENTITY_TOUR, tour.id, "es", "duration_text", "1 - 2 horas"
    )

    print(f"OK  1 tour con {len(recorrido)} paradas ordenadas y audio")
    return [tour]


# --------------------------------------------------------------------------
# Guía histórica
# --------------------------------------------------------------------------

def seed_history():
    cronologia = Timeline(
        id="mexica-chronology",
        title="Understanding the legacy of the Aztec",
        description="From the founding of Tenochtitlan to the fall of the empire.",
        sort_order=0,
    )
    db.session.add(cronologia)
    db.session.flush()

    articulos = [
        ("founding", "The eagle and the cactus", "Foundation myth",
         "An eagle perched on a cactus told the Mexica where to build.", 4, 0, False),
        ("lake-city", "A city built on water", "Daily life",
         "Tenochtitlan grew on an island, connected by causeways and canals.", 6, 1, False),
        ("fall", "The fall of Tenochtitlan", "Conquest",
         "When we saw all those cities built in the water, we were amazed.", 8, 2, True),
    ]

    creados = []
    for slug, titulo, tema, cuerpo, minutos, orden, bloqueado in articulos:
        contenido = HistoricalContent(
            id=slug,
            title=titulo,
            description=cuerpo,
            content_type="text",
            text_content=" ".join([cuerpo] * 12),
            timeline_id=cronologia.id,
            sort_order=orden,
            era="Aztec Empire (1345-1521)",
            topic=tema,
            reading_time_minutes=minutos,
            is_locked=bloqueado,
            author="AztecApp editorial",
            verified=True,
        )
        db.session.add(contenido)
        creados.append(contenido)

    db.session.commit()

    TranslationRepository.upsert(
        ENTITY_HISTORICAL, "founding", "es", "title", "El águila y el nopal"
    )

    print(f"OK  1 cronología con {len(creados)} artículos, tiempos de lectura y temas")
    return creados


# --------------------------------------------------------------------------
# Overlay del lago
# --------------------------------------------------------------------------

def seed_lake():
    """Polígonos del lago.

    Los trazados son APROXIMACIONES para desarrollo, no cartografía histórica.
    Todos llevan el mismo año porque es lo que consulta el conmutador
    «1500 / 2026» del mapa.
    """
    # El orden importa al pintar: el agua va primero y las islas encima. La app
    # dibuja en el orden en que llegan los Features.
    poligonos = [
        (SURFACE_WATER, "Lake Texcoco", "Texcoco",
         "The salt lake surrounding the islands, drained over four centuries",
         [(-99.1700, 19.3900), (-99.1700, 19.4900), (-99.0400, 19.4900),
          (-99.0400, 19.3900), (-99.1700, 19.3900)]),
        (SURFACE_LAND, "Island of Tenochtitlan", "Tenochtitlan",
         "The main island, holding the ceremonial precinct",
         [(-99.1450, 19.4250), (-99.1450, 19.4450), (-99.1240, 19.4450),
          (-99.1240, 19.4250), (-99.1450, 19.4250)]),
        (SURFACE_LAND, "Tlatelolco", "Tlatelolco",
         "The twin island to the north, home of the great market",
         [(-99.1450, 19.4450), (-99.1450, 19.4560), (-99.1300, 19.4560),
          (-99.1300, 19.4450), (-99.1450, 19.4450)]),
    ]

    creados = []
    for superficie, nombre, nahuatl, descripcion, coords in poligonos:
        creados.append(LakeViewService.create_lake_geometry(
            name=nombre,
            geojson_polygon={
                "type": "Polygon",
                # GeoJSON usa [longitud, latitud], igual que PostGIS.
                "coordinates": [[[lon, lat] for lon, lat in coords]],
            },
            year_estimate=ERA_HISTORIC_YEAR,
            surface_type=superficie,
            tenochtitlan_name=nahuatl,
            description=descripcion,
        ))

    print(f"OK  {len(creados)} polígonos del lago para el año {ERA_HISTORIC_YEAR}")
    return creados


def main():
    with app.app_context():
        if Place.query.first():
            print("La base ya tiene datos. No se siembra nada.")
            return

        try:
            places = seed_places()
            seed_tours(places)
            seed_history()
            seed_lake()
            print("\nSiembra completada.")
        except Exception as e:
            db.session.rollback()
            print(f"\nError durante la siembra: {e}")
            raise


if __name__ == "__main__":
    main()
