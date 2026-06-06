def test_basic_balance_calculation(client, sample_users, sample_group):
    mohit_id = sample_users[0]["id"]
    group_id = sample_group["id"]

    # Dinner 1200 paid by Mohit
    client.post("/expenses", json={
        "group_id": group_id,
        "paid_by": mohit_id,
        "amount": 1200.00,
        "description": "Dinner",
        "split_type": "equal"
    })

    # Get balances
    response = client.get(f"/balances?group_id={group_id}")
    assert response.status_code == 200
    data = response.json()

    balances = data["balances"]
    # Rahul owes Mohit 400.00
    assert balances["Rahul"]["owes"]["Mohit"] == 400.00
    # Ankit owes Mohit 400.00
    assert balances["Ankit"]["owes"]["Mohit"] == 400.00
    
    # Check Summary
    assert data["summary"]["total_expenses"] == 1200.00
    assert data["summary"]["total_pending_settlements"] == 800.00

def test_mutual_debt_netting(client, sample_users, sample_group):
    mohit_id = sample_users[0]["id"]
    rahul_id = sample_users[1]["id"]
    group_id = sample_group["id"]

    # Dinner 1200 paid by Mohit (Rahul owes Mohit 400, Ankit owes Mohit 400)
    client.post("/expenses", json={
        "group_id": group_id,
        "paid_by": mohit_id,
        "amount": 1200.00,
        "description": "Dinner",
        "split_type": "equal"
    })

    # Transport 600 paid by Rahul (Mohit owes Rahul 200, Ankit owes Rahul 200)
    client.post("/expenses", json={
        "group_id": group_id,
        "paid_by": rahul_id,
        "amount": 600.00,
        "description": "Transport",
        "split_type": "equal"
    })

    # Get balances
    response = client.get(f"/balances?group_id={group_id}")
    assert response.status_code == 200
    data = response.json()

    balances = data["balances"]

    # Netting:
    # Rahul owes Mohit 400 gross, Mohit owes Rahul 200 gross -> Rahul owes Mohit 200 net
    assert balances["Rahul"]["owes"]["Mohit"] == 200.00
    
    # Ankit owes Mohit 400, and Ankit owes Rahul 200
    assert balances["Ankit"]["owes"]["Mohit"] == 400.00
    assert balances["Ankit"]["owes"]["Rahul"] == 200.00

    # Mohit owes Rahul should be deleted/absent due to netting
    if "Mohit" in balances:
        assert "Rahul" not in balances["Mohit"].get("owes", {})

def test_balance_zero_after_settlement(client, sample_users, sample_group):
    mohit_id = sample_users[0]["id"]
    rahul_id = sample_users[1]["id"]
    group_id = sample_group["id"]

    # Dinner 1200 paid by Mohit (Rahul owes Mohit 400, Ankit owes Mohit 400)
    client.post("/expenses", json={
        "group_id": group_id,
        "paid_by": mohit_id,
        "amount": 1200.00,
        "description": "Dinner",
        "split_type": "equal"
    })

    # Post settlement: Rahul pays Mohit 400
    res_settle = client.post("/settlements", json={
        "group_id": group_id,
        "paid_by": rahul_id,
        "paid_to": mohit_id,
        "amount": 400.00,
        "note": "Paid via UPI"
    })
    assert res_settle.status_code == 201

    # Get balances
    response = client.get(f"/balances?group_id={group_id}")
    assert response.status_code == 200
    data = response.json()

    balances = data["balances"]
    # Rahul owes Mohit should be 0, which means either absent or does not owe Mohit anymore
    if "Rahul" in balances:
        assert "Mohit" not in balances["Rahul"].get("owes", {})

def test_multiple_expenses_accumulate(client, sample_users, sample_group):
    mohit_id = sample_users[0]["id"]
    group_id = sample_group["id"]

    # Dinner 1200 paid by Mohit (Rahul owes 400, Ankit owes 400)
    client.post("/expenses", json={
        "group_id": group_id,
        "paid_by": mohit_id,
        "amount": 1200.00,
        "description": "Dinner",
        "split_type": "equal"
    })

    # Snacks 600 paid by Mohit (Rahul owes 200, Ankit owes 200)
    client.post("/expenses", json={
        "group_id": group_id,
        "paid_by": mohit_id,
        "amount": 600.00,
        "description": "Snacks",
        "split_type": "equal"
    })

    # Get balances
    response = client.get(f"/balances?group_id={group_id}")
    assert response.status_code == 200
    data = response.json()

    balances = data["balances"]
    # Rahul owes Mohit should be 400 + 200 = 600
    assert balances["Rahul"]["owes"]["Mohit"] == 600.00
    # Ankit owes Mohit should be 400 + 200 = 600
    assert balances["Ankit"]["owes"]["Mohit"] == 600.00
