"""Test historical module"""
import pytest


def test_get_all_timelines(client):
    """Test getting all timelines"""
    response = client.get("/api/historical/timelines")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True


def test_get_lake_data(client):
    """Test getting lake view data"""
    response = client.get("/api/historical/lake-view?latitude=19.43&longitude=-99.13")
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
