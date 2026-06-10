"""Development and testing utilities"""
import os
import sys
from app import create_app, db
from app.places.models import Place
from app.tours.models import Tour
from app.users.models import User
from app.historical.models import HistoricalContent
from datetime import datetime
import uuid

app = create_app()


@app.shell_context_processor
def make_shell_context():
    """Create shell context for Flask CLI"""
    return {
        "db": db,
        "Place": Place,
        "Tour": Tour,
        "User": User,
        "HistoricalContent": HistoricalContent,
    }


def init_db():
    """Initialize database with sample data"""
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database initialized!")
        
        # Add sample places
        sample_places = [
            Place(
                id=str(uuid.uuid4()),
                name="Templo Mayor",
                description="Remains of the main Aztec temple in Mexico City",
                latitude=19.4361,
                longitude=-99.1356,
                place_type="ruin",
                historical_significance="Main temple of Tenochtitlan",
                tenochtitlan_name="Huei Teocalli",
                estimated_visit_duration=90,
                is_locked=False,
                has_bathrooms=True,
                has_cafes=True,
                archaeological=True,
            ),
            Place(
                id=str(uuid.uuid4()),
                name="Museo Nacional de Antropología",
                description="National museum with extensive Aztec artifacts",
                latitude=19.4269,
                longitude=-99.1878,
                place_type="museum",
                historical_significance="Houses the largest collection of pre-Hispanic artifacts",
                estimated_visit_duration=180,
                is_locked=True,
                required_subscription="premium",
                unlock_price=15.0,
                has_bathrooms=True,
                has_cafes=True,
            ),
        ]
        
        for place in sample_places:
            db.session.add(place)
        
        db.session.commit()
        print(f"Added {len(sample_places)} sample places")


def drop_db():
    """Drop all tables"""
    with app.app_context():
        db.drop_all()
        print("Database dropped!")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "init":
            init_db()
        elif command == "drop":
            drop_db()
        elif command == "shell":
            app.shell()
    else:
        print("Usage: python manage.py [init|drop|shell]")
