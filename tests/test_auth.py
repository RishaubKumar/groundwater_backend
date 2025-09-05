"""
Tests for authentication endpoints.
"""

import pytest
from fastapi.testclient import TestClient


def test_register_user(client: TestClient):
    """Test user registration."""
    user_data = {
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "newpassword123",
        "full_name": "New User"
    }
    
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]
    assert "id" in data


def test_register_duplicate_user(client: TestClient, test_user):
    """Test registration with duplicate username."""
    user_data = {
        "username": "testuser",  # Same as test_user
        "email": "different@example.com",
        "password": "password123"
    }
    
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 400


def test_login_user(client: TestClient, test_user):
    """Test user login."""
    login_data = {
        "username": "testuser",
        "password": "testpassword"
    }
    
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client: TestClient):
    """Test login with invalid credentials."""
    login_data = {
        "username": "nonexistent",
        "password": "wrongpassword"
    }
    
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 401


def test_get_current_user(client: TestClient, auth_headers):
    """Test getting current user info."""
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["username"] == "testuser"


def test_get_current_user_unauthorized(client: TestClient):
    """Test getting current user without authentication."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_change_password(client: TestClient, auth_headers):
    """Test changing password."""
    password_data = {
        "current_password": "testpassword",
        "new_password": "newpassword123"
    }
    
    response = client.post("/api/v1/auth/change-password", json=password_data, headers=auth_headers)
    assert response.status_code == 200
    
    # Test login with new password
    login_data = {
        "username": "testuser",
        "password": "newpassword123"
    }
    
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200


def test_change_password_wrong_current(client: TestClient, auth_headers):
    """Test changing password with wrong current password."""
    password_data = {
        "current_password": "wrongpassword",
        "new_password": "newpassword123"
    }
    
    response = client.post("/api/v1/auth/change-password", json=password_data, headers=auth_headers)
    assert response.status_code == 400


def test_refresh_token(client: TestClient, auth_headers):
    """Test token refresh."""
    response = client.post("/api/v1/auth/refresh-token", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_logout(client: TestClient, auth_headers):
    """Test user logout."""
    response = client.post("/api/v1/auth/logout", headers=auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "message" in data
