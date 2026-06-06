def test_settlement_reduces_balance(client, sample_users, sample_group):
    mohit_id = sample_users[0]["id"]
    rahul_id = sample_users[1]["id"]
    group_id = sample_group["id"]

    # Dinner 1200 paid by Mohit (Rahul owes 400)
    client.post("/expenses", json={
        "group_id": group_id,
        "paid_by": mohit_id,
        "amount": 1200.00,
        "description": "Dinner",
        "split_type": "equal"
    })

    # Rahul pays Mohit 150 (partial settlement)
    response = client.post("/settlements", json={
        "group_id": group_id,
        "paid_by": rahul_id,
        "paid_to": mohit_id,
        "amount": 150.00,
        "note": "First installment"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == "150.00"
    assert data["remaining_debt"] == "250.00"  # 400 - 150 = 250

    # Verify via balance check
    bal_res = client.get(f"/balances?group_id={group_id}")
    assert bal_res.json()["balances"]["Rahul"]["owes"]["Mohit"] == 250.00

def test_cannot_settle_more_than_owed(client, sample_users, sample_group):
    mohit_id = sample_users[0]["id"]
    rahul_id = sample_users[1]["id"]
    group_id = sample_group["id"]

    # Dinner 1200 paid by Mohit (Rahul owes 400)
    client.post("/expenses", json={
        "group_id": group_id,
        "paid_by": mohit_id,
        "amount": 1200.00,
        "description": "Dinner",
        "split_type": "equal"
    })

    # Rahul tries to pay 401 (exceeds 400)
    response = client.post("/settlements", json={
        "group_id": group_id,
        "paid_by": rahul_id,
        "paid_to": mohit_id,
        "amount": 401.00,
        "note": "Paying too much"
    })
    assert response.status_code == 400
    assert response.json()["error"] is True

def test_cannot_settle_with_yourself(client, sample_users, sample_group):
    mohit_id = sample_users[0]["id"]
    group_id = sample_group["id"]

    response = client.post("/settlements", json={
        "group_id": group_id,
        "paid_by": mohit_id,
        "paid_to": mohit_id,
        "amount": 100.00
    })
    assert response.status_code == 422
    assert response.json()["error"] is True
