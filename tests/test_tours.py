"""Test tours module"""
import pytest


def test_get_free_tours(client):
    """Test getting free tours"""
    response = client.get("/api/tours/free")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "tours" in data["data"]


def test_get_all_tours(client):
    """Test getting all tours"""
    response = client.get("/api/tours/?page=1&limit=10")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "tours" in data["data"]
