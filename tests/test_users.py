"""Test users module"""
import pytest
from app.users.services import UserService


def test_user_registration(client):
    """Test user registration"""
    response = client.post("/api/users/register", json={
        "email": "test@example.com",
        "password": "testpassword123",
        "firstName": "Test",
        "lastName": "User",
    })
    
    assert response.status_code == 201
    data = response.get_json()
    assert data["success"] is True
    assert "accessToken" in data["data"]


def test_user_login(client):
    """Test user login"""
    # Register first
    client.post("/api/users/register", json={
        "email": "test2@example.com",
        "password": "testpassword123",
    })
    
    # Login
    response = client.post("/api/users/login", json={
        "email": "test2@example.com",
        "password": "testpassword123",
    })
    
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "accessToken" in data["data"]


def test_invalid_email_registration(client):
    """Test registration with invalid email"""
    response = client.post("/api/users/register", json={
        "email": "invalid-email",
        "password": "testpassword123",
    })
    
    assert response.status_code == 400
    data = response.get_json()
    assert data["success"] is False
