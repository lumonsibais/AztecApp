"""Script para cargar datos de prueba (seed)"""
from app import create_app, db
from app.places.models import Place
from app.tours.models import Tour
from app.historical.models import HistoricalContent, Timeline, LakeView
import uuid

app = create_app()


def seed_places():
    """Cargar sitios de prueba"""
    with app.app_context():
        places_data = [
            {
                "name": "Templo Mayor",
                "description": "El templo más importante de Tenochtitlan, dedicado a Huitzilopochtli y Tláloc",
                "latitude": 19.4361,
                "longitude": -99.1356,
                "place_type": "ruin",
                "historical_significance": "Centro religioso y político del imperio azteca",
                "tenochtitlan_name": "Huei Teocalli",
                "estimated_visit_duration": 90,
                "is_locked": False,
                "opening_hours": "9:00 AM - 5:00 PM",
                "entry_fee": 85,
                "has_bathrooms": True,
                "has_cafes": True,
                "has_hotels": True,
                "archaeological": True,
                "era_description": "Construido en 1325, ampliado múltiples veces hasta 1521",
            },
            {
                "name": "Museo Nacional de Antropología",
                "description": "Museo con la colección más grande de artefactos prehispánicos de México",
                "latitude": 19.4269,
                "longitude": -99.1878,
                "place_type": "museum",
                "historical_significance": "Alberga la Piedra del Sol y otros tesoros aztecas",
                "estimated_visit_duration": 180,
                "is_locked": True,
                "required_subscription": "premium",
                "unlock_price": 15.0,
                "opening_hours": "9:00 AM - 7:00 PM (Closed Mondays)",
                "entry_fee": 80,
                "has_bathrooms": True,
                "has_cafes": True,
                "has_hotels": True,
                "archaeological": False,
            },
            {
                "name": "Palacio Nacional",
                "description": "Edificio que fue construido sobre el Palacio de Montezuma",
                "latitude": 19.4353,
                "longitude": -99.1344,
                "place_type": "cultural_center",
                "historical_significance": "Contiene murales de Diego Rivera que narran la historia de México",
                "tenochtitlan_name": "Tecpan",
                "estimated_visit_duration": 60,
                "is_locked": False,
                "opening_hours": "10:00 AM - 5:00 PM",
                "entry_fee": 0,  # Free
                "has_bathrooms": True,
                "has_cafes": False,
                "has_hotels": False,
                "archaeological": False,
            },
            {
                "name": "Zona Arqueológica de Malinalco",
                "description": "Antiguo centro ceremonial mexica con edificios tallados en la roca",
                "latitude": 18.9989,
                "longitude": -99.5034,
                "place_type": "ruin",
                "historical_significance": "Templo de las Guerras Floridas dedicado a Tezcatlipoca",
                "estimated_visit_duration": 120,
                "is_locked": True,
                "required_subscription": "premium",
                "unlock_price": 15.0,
                "opening_hours": "9:00 AM - 5:00 PM",
                "entry_fee": 75,
                "has_bathrooms": True,
                "has_cafes": False,
                "has_hotels": False,
                "archaeological": True,
            },
        ]
        
        places = []
        for data in places_data:
            place = Place(
                id=str(uuid.uuid4()),
                **data
            )
            db.session.add(place)
            places.append(place)
        
        db.session.commit()
        print(f"✓ Added {len(places)} places")
        return places


def seed_tours(places):
    """Cargar tours de prueba"""
    with app.app_context():
        tours_data = [
            {
                "title": "Introduction to Tenochtitlan",
                "description": "A beginner-friendly walk through downtown CDMX to discover the history of Tenochtitlan",
                "status": "published",
                "is_free": True,
                "price": 0,
                "is_locked": False,
                "estimated_duration": 120,
                "difficulty_level": "easy",
                "total_distance": 2.5,
                "content_description": "Learn about the three main Aztec temples and their significance",
                "includes_audio": True,
            },
            {
                "title": "Advanced: Empire Expansion Route",
                "description": "Explore sites related to the Aztec Empire's military conquests",
                "status": "published",
                "is_free": False,
                "price": 15.0,
                "is_locked": True,
                "estimated_duration": 180,
                "difficulty_level": "medium",
                "total_distance": 8.0,
                "content_description": "Detailed history of the Triple Alliance and conquered territories",
                "includes_audio": True,
            },
            {
                "title": "Hidden Gems: Lesser-Known Sites",
                "description": "Discover sites often missed by regular tourists",
                "status": "published",
                "is_free": True,
                "price": 0,
                "is_locked": False,
                "estimated_duration": 150,
                "difficulty_level": "medium",
                "total_distance": 5.0,
                "content_description": "Explore archaeological sites away from the main tourist routes",
                "includes_audio": True,
            },
        ]
        
        tours = []
        for i, data in enumerate(tours_data):
            tour = Tour(
                id=str(uuid.uuid4()),
                **data
            )
            # Associate with places (simple round-robin)
            if places:
                tour.places.append(places[i % len(places)])
                if i < len(places):
                    tour.places.append(places[(i + 1) % len(places)])
            
            db.session.add(tour)
            tours.append(tour)
        
        db.session.commit()
        print(f"✓ Added {len(tours)} tours")
        return tours


def seed_historical_content():
    """Cargar contenido histórico"""
    with app.app_context():
        content_data = [
            {
                "title": "The Aztec Capital: Tenochtitlan",
                "description": "Explore the history of the magnificent capital of the Aztec Empire",
                "content_type": "text",
                "text_content": """
Tenochtitlan was one of the largest cities in the world in the 15th century, with a population 
estimated at 200,000-400,000. The city was built on an island in Lake Texcoco, and was connected 
by canals and causeways. The city was divided into four districts, each representing one of the 
four Aztec nations that formed the Triple Alliance.
                """,
                "era": "Aztec Empire (1345-1521)",
                "author": "Dr. Miguel López",
                "verified": True,
            },
            {
                "title": "The Templo Mayor: Architectural Marvel",
                "description": "Understanding the design and construction of the main Aztec temple",
                "content_type": "text",
                "text_content": """
The Templo Mayor was built in multiple stages over approximately 200 years. Each ruler added 
their own layer to the temple, which explains its pyramidal structure. The temple was dedicated 
to two gods: Huitzilopochtli (god of war) and Tláloc (god of rain).
                """,
                "era": "Aztec Empire (1325-1521)",
                "author": "Dr. Maria García",
                "verified": True,
            },
            {
                "title": "The Three Cultures of Mexico City",
                "description": "How Aztec, Spanish colonial, and modern influences shaped CDMX",
                "content_type": "article",
                "text_content": """
Mexico City is a unique blend of Aztec, Spanish colonial, and modern influences. Walking through 
the historic center, you can see pre-Hispanic temples next to colonial churches and modern buildings. 
This layering of cultures tells the story of Mexico's complex history.
                """,
                "era": "Aztec to Modern",
                "author": "Dr. Carlos Mendez",
                "verified": True,
            },
        ]
        
        contents = []
        for data in content_data:
            content = HistoricalContent(
                id=str(uuid.uuid4()),
                **data
            )
            db.session.add(content)
            contents.append(content)
        
        db.session.commit()
        print(f"✓ Added {len(contents)} historical content pieces")
        return contents


def seed_timelines():
    """Cargar timelines"""
    with app.app_context():
        timelines_data = [
            {
                "title": "Aztec Empire Timeline",
                "description": "Major events and periods in Aztec history from 1345 to 1521",
            },
            {
                "title": "Spanish Conquest Timeline",
                "description": "Events leading to and during the Spanish conquest of Mexico (1519-1521)",
            },
            {
                "title": "Mexico City Evolution",
                "description": "How Mexico City developed from Tenochtitlan to the modern metropolis",
            },
        ]
        
        timelines = []
        for data in timelines_data:
            timeline = Timeline(
                id=str(uuid.uuid4()),
                **data
            )
            db.session.add(timeline)
            timelines.append(timeline)
        
        db.session.commit()
        print(f"✓ Added {len(timelines)} timelines")
        return timelines


def seed_lake_data():
    """Cargar datos del lago"""
    with app.app_context():
        lake_data = [
            {
                "latitude": 19.4361,
                "longitude": -99.1356,
                "was_water": True,
                "year_estimate": 1500,
                "description": "Templo Mayor was built on an island in Lake Texcoco",
                "tenochtitlan_name": "Huei Teocalli Island",
            },
            {
                "latitude": 19.4410,
                "longitude": -99.1250,
                "was_water": True,
                "year_estimate": 1450,
                "description": "This area was part of the canals of Tenochtitlan",
                "tenochtitlan_name": "Canal system",
            },
            {
                "latitude": 19.4300,
                "longitude": -99.1400,
                "was_water": False,
                "year_estimate": 1500,
                "description": "This area was one of the main residential districts",
                "tenochtitlan_name": "Tlatelolco Quarter",
            },
        ]
        
        views = []
        for data in lake_data:
            view = LakeView(
                id=str(uuid.uuid4()),
                **data
            )
            db.session.add(view)
            views.append(view)
        
        db.session.commit()
        print(f"✓ Added {len(views)} lake view data points")
        return views


def main():
    """Run all seed functions"""
    with app.app_context():
        print("Starting database seed...")
        
        # Create tables if they don't exist
        db.create_all()
        
        # Check if already seeded
        if Place.query.first():
            print("⚠ Database already has data. Skipping seed.")
            return
        
        try:
            places = seed_places()
            tours = seed_tours(places)
            content = seed_historical_content()
            timelines = seed_timelines()
            lake_data = seed_lake_data()
            
            print("\n✓ Database seeding completed successfully!")
            print(f"  - {len(places)} places")
            print(f"  - {len(tours)} tours")
            print(f"  - {len(content)} historical content")
            print(f"  - {len(timelines)} timelines")
            print(f"  - {len(lake_data)} lake data points")
            
        except Exception as e:
            print(f"\n✗ Error during seeding: {e}")
            db.session.rollback()


if __name__ == "__main__":
    main()
