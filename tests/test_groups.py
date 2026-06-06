def test_create_group_success(client, sample_users):
    mohit_id = sample_users[0]["id"]
    response = client.post("/groups", json={"name": "Goa Trip", "created_by": mohit_id})
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Goa Trip"
    assert data["created_by"] == mohit_id

def test_create_group_creator_not_found(client):
    response = client.post("/groups", json={"name": "Ghost Group", "created_by": 9999})
    assert response.status_code == 400
    assert response.json()["error"] is True

def test_add_member_success(client, sample_users):
    mohit_id = sample_users[0]["id"]
    rahul_id = sample_users[1]["id"]
    
    # Create group
    res_group = client.post("/groups", json={"name": "Trip", "created_by": mohit_id})
    group_id = res_group.json()["id"]

    # Add member
    response = client.post(f"/groups/{group_id}/members", json={"user_id": rahul_id})
    assert response.status_code == 200
    data = response.json()
    assert data["group_id"] == group_id
    assert data["user_id"] == rahul_id
    assert "added successfully" in data["message"].lower()

def test_add_member_duplicate_fails(client, sample_users):
    mohit_id = sample_users[0]["id"]
    rahul_id = sample_users[1]["id"]
    
    # Create group
    res_group = client.post("/groups", json={"name": "Trip", "created_by": mohit_id})
    group_id = res_group.json()["id"]

    # Add member first time
    client.post(f"/groups/{group_id}/members", json={"user_id": rahul_id})
    
    # Duplicate add
    response = client.post(f"/groups/{group_id}/members", json={"user_id": rahul_id})
    assert response.status_code == 409
    assert response.json()["error"] is True
