from fastapi.testclient import TestClient
from backend.main import app
from backend import db
import pytest
import uuid

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    db.init_db()
    yield

client = TestClient(app)

def test_user_flow():
    # 1. Create a user via auth register
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    user_data = {
        "name": "Test Player",
        "email": unique_email,
        "password": "securepassword",
        "skill_level": "intermediate"
    }
    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 200, f"Failed to register user: {response.text}"
    
    user = response.json()
    user_id = user["user_id"]
    assert user["name"] == "Test Player"

    # 2. List users
    response = client.get("/users")
    assert response.status_code == 200
    users = response.json()
    assert any(u["id"] == user_id for u in users)

    # 3. Check history (should be empty initially)
    response = client.get(f"/users/{user_id}/history")
    assert response.status_code == 200
    assert response.json() == []
