"""Test historical module"""
import pytest


def test_get_all_timelines(client):
    """Test getting all timelines"""
    response = client.get("/api/historical/timelines")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True


def test_get_lake_overlay(client):
    """El overlay del lago sale como GeoJSON, con o sin encuadre."""
    response = client.get("/api/historical/lake-view")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["data"]["type"] == "FeatureCollection"
