def test_equal_split_three_people(client, sample_users, sample_group):
    mohit_id = sample_users[0]["id"]
    rahul_id = sample_users[1]["id"]
    ankit_id = sample_users[2]["id"]
    group_id = sample_group["id"]

    expense_payload = {
        "group_id": group_id,
        "paid_by": mohit_id,
        "amount": 1200.00,
        "description": "Dinner",
        "category": "Food",
        "split_type": "equal"
    }

    response = client.post("/expenses", json=expense_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == "1200.00"
    assert data["paid_by"] == "Mohit"
    assert len(data["splits"]) == 2  # Mohit (payer) excluded from splits
    
    # Check individual split values
    splits_map = {s["user_id"]: s["amount_owed"] for s in data["splits"]}
    assert splits_map[rahul_id] == "400.00"
    assert splits_map[ankit_id] == "400.00"

def test_equal_split_rounding(client, sample_users, sample_group):
    mohit_id = sample_users[0]["id"]
    rahul_id = sample_users[1]["id"]
    ankit_id = sample_users[2]["id"]
    group_id = sample_group["id"]

    # ₹100 split amongst 3 people (Mohit, Rahul, Ankit)
    expense_payload = {
        "group_id": group_id,
        "paid_by": mohit_id,
        "amount": 100.00,
        "description": "Round Test",
        "category": "Others",
        "split_type": "equal"
    }

    response = client.post("/expenses", json=expense_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == "100.00"

    # Ensure payer is excluded from DB splits.
    # Rahul and Ankit owe. The split array contains exactly 2 splits.
    # The split utility distributes base cents (33.33) and remainder cents.
    # Since member IDs are sorted: [mohit_id, rahul_id, ankit_id]
    # Index 0 gets 33.34, Index 1 gets 33.33, Index 2 gets 33.33.
    # Since Mohit is Index 0 (payer), his share (33.34) is excluded.
    # Rahul and Ankit owe 33.33 each.
    splits_map = {s["user_id"]: s["amount_owed"] for s in data["splits"]}
    assert splits_map[rahul_id] == "33.33"
    assert splits_map[ankit_id] == "33.33"

def test_payer_not_in_splits(client, sample_users, sample_group):
    mohit_id = sample_users[0]["id"]
    group_id = sample_group["id"]

    expense_payload = {
        "group_id": group_id,
        "paid_by": mohit_id,
        "amount": 300.00,
        "description": "Exclusion Test",
        "split_type": "equal"
    }

    response = client.post("/expenses", json=expense_payload)
    assert response.status_code == 201
    data = response.json()
    
    # Verify payer (Mohit) is not present in the splits array
    for split in data["splits"]:
        assert split["user_id"] != mohit_id

def test_custom_split_amounts_must_sum_to_total(client, sample_users, sample_group):
    mohit_id = sample_users[0]["id"]
    rahul_id = sample_users[1]["id"]
    ankit_id = sample_users[2]["id"]
    group_id = sample_group["id"]

    # Sum is 500 + 300 + 100 = 900 != 1000.00
    expense_payload = {
        "group_id": group_id,
        "paid_by": mohit_id,
        "amount": 1000.00,
        "description": "Hotel",
        "split_type": "custom",
        "custom_splits": [
            {"user_id": mohit_id, "amount": 500.00},
            {"user_id": rahul_id, "amount": 300.00},
            {"user_id": ankit_id, "amount": 100.00}
        ]
    }

    response = client.post("/expenses", json=expense_payload)
    assert response.status_code == 422
    assert response.json()["error"] is True

def test_expense_amount_must_be_positive(client, sample_users, sample_group):
    mohit_id = sample_users[0]["id"]
    group_id = sample_group["id"]

    expense_payload = {
        "group_id": group_id,
        "paid_by": mohit_id,
        "amount": -50.00,
        "description": "Negative expense",
        "split_type": "equal"
    }

    response = client.post("/expenses", json=expense_payload)
    assert response.status_code == 422
    assert response.json()["error"] is True

def test_payer_must_be_group_member(client, sample_users, sample_group):
    # Create a new user who is not in sample_group
    res_user = client.post("/users", json={"name": "Stranger", "email": "stranger@example.com"})
    stranger_id = res_user.json()["id"]
    group_id = sample_group["id"]

    expense_payload = {
        "group_id": group_id,
        "paid_by": stranger_id,
        "amount": 300.00,
        "description": "Intruder payment",
        "split_type": "equal"
    }

    response = client.post("/expenses", json=expense_payload)
    assert response.status_code == 400
    assert response.json()["error"] is True

def test_group_must_have_members_before_expense(client, sample_users):
    mohit_id = sample_users[0]["id"]
    
    # Create group but add NO members (so count = 0)
    res_group = client.post("/groups", json={"name": "Empty Goa Trip", "created_by": mohit_id})
    group_id = res_group.json()["id"]

    expense_payload = {
        "group_id": group_id,
        "paid_by": mohit_id,
        "amount": 1200.00,
        "description": "Dinner",
        "split_type": "equal"
    }

    response = client.post("/expenses", json=expense_payload)
    assert response.status_code == 400
    assert response.json()["error"] is True
