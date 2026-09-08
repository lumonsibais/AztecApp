"""Test places module"""
import pytest
from app.extensions import db
from app.places.services import PlaceService
from app.places.models import Place
import uuid


def test_get_nearby_places(client, app):
    """Test getting nearby places"""
    with app.app_context():
        # Create test place
        place = Place(
            id=str(uuid.uuid4()),
            name="Test Place",
            description="Test description",
            latitude=19.4361,
            longitude=-99.1356,
            place_type="ruin",
            historical_significance="Test significance",
            estimated_visit_duration=60,
            is_locked=False,
        )
        # Flask-SQLAlchemy 3.x registra la extensión bajo la clave "sqlalchemy",
        # no "db". Usar el objeto db directamente evita depender de esa clave.
        db.session.add(place)
        db.session.commit()
    
    # Test endpoint
    response = client.get("/api/places/nearby?latitude=19.43&longitude=-99.13&radius=5")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "data" in data


def test_get_all_places(client):
    """Test getting all places"""
    response = client.get("/api/places/?page=1&limit=10")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
