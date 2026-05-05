import requests
import os

BASE_URL = "http://localhost:8000"

def test_user_flow():
    # 1. Create a user
    user_data = {"name": "Test Player", "skill_level": "intermediate"}
    response = requests.post(f"{BASE_URL}/users", json=user_data)
    if response.status_code != 200:
        print(f"Failed to create user: {response.text}")
        return
    
    user = response.json()
    user_id = user["id"]
    print(f"Created user with ID: {user_id}")

    # 2. List users
    response = requests.get(f"{BASE_URL}/users")
    print(f"Users list: {response.json()}")

    # 3. Check history (should be empty)
    response = requests.get(f"{BASE_URL}/users/{user_id}/history")
    print(f"Initial history: {response.json()}")

if __name__ == "__main__":
    # Note: This assumes the server is running. 
    # Since I cannot easily run a long-lived process and hit it with requests in one turn,
    # I will try to use the fastapi TestClient in a separate script if needed,
    # or just start the server in background.
    pass
