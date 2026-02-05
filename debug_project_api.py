import requests
import json
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1"

def debug_api():
    # 1. Register/Login
    username = "debug_user_001"
    password = "password123"

    print(f"1. Attempting to login with {username}...")
    login_resp = requests.post(f"{BASE_URL}/auth/login", data={
        "username": username,
        "password": password
    })

    if login_resp.status_code == 401:
        print("User does not exist, registering...")
        reg_resp = requests.post(f"{BASE_URL}/auth/register", json={
            "email": "debug001@example.com",
            "username": username,
            "password": password,
            "full_name": "Debug User"
        })
        if reg_resp.status_code not in [200, 201]:
            print(f"Registration failed: {reg_resp.text}")
            return

        # Login again
        login_resp = requests.post(f"{BASE_URL}/auth/login", data={
            "username": username,
            "password": password
        })

    if login_resp.status_code != 200:
        print(f"Login failed: {login_resp.text}")
        return

    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login successful.")

    # 2. Create Project
    print("\n2. Creating project...")
    payload = {
        "name": "Test Project 001",
        "novel_type": "Sci-Fi",
        "description": "Debug description",
        "batch_size": 5,
        "chapter_split_rule": "auto"
    }

    resp = requests.post(f"{BASE_URL}/projects", json=payload, headers=headers)
    print(f"Status Code: {resp.status_code}")
    print(f"Response Body: {resp.text}")

if __name__ == "__main__":
    try:
        debug_api()
    except Exception as e:
        print(f"Error: {e}")
