def test_create_user_success(client):
    response = client.post("/users", json={"name": "Alice", "email": "alice@example.com"})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Alice"
    assert data["email"] == "alice@example.com"
    assert "id" in data
    assert "created_at" in data

def test_create_user_duplicate_email_fails(client):
    # Register Alice once
    client.post("/users", json={"name": "Alice", "email": "alice@example.com"})
    
    # Try duplicate
    response = client.post("/users", json={"name": "Alice Duplicate", "email": "alice@example.com"})
    assert response.status_code == 409
    data = response.json()
    assert data["error"] is True
    assert "conflict" in data["message"].lower()

def test_create_user_empty_name_fails(client):
    # Empty string name
    response = client.post("/users", json={"name": "", "email": "empty@example.com"})
    assert response.status_code == 422
    assert response.json()["error"] is True

    # Whitespace only name
    response = client.post("/users", json={"name": "   ", "email": "empty@example.com"})
    assert response.status_code == 422
    assert response.json()["error"] is True

def test_get_user_not_found_returns_404(client):
    response = client.get("/users/9999")
    assert response.status_code == 404
    data = response.json()
    assert data["error"] is True
    assert "not found" in data["message"].lower()
