from tests.helpers import client, reset_db, add_food, add_meal, add_workout

def test_create_meals():
    reset_db()
    chicken_id = add_food("00001", "にわとり　むね　生", calories=200, protein=20)
    rice_id = add_food("00002", "こめ　ごはん")

    response =client.post("/meals", json={
        "date": "2026-11-17",
        "meal_type": "夕食",
        "items": [
            {"food_id": chicken_id, "grams":150},
            {"food_id": rice_id, "grams":100} 
        ],
    })

    assert response.status_code == 201
    data = response.json()
    assert len(data)==2
    assert data[0]["food_name"] == "にわとり　むね　生"
    assert data[0]["calories"] == 300
    assert data[0]["protein"] == 30 

def test_create_invalid_meal_type():
    reset_db()
    food_id = add_food("00002", "にわとり　むね　生")

    response = client.post("/meals", json={
        "date": "2026-11-17",
        "meal_type": "夕飯",
        "items": [
            {"food_id": food_id, "grams": 150},
        ],
    })

    assert response.status_code == 422

def test_create_zero_grams():
    reset_db()
    food_id = add_food("00002", "にわとり　むね　生")
    response = client.post("/meals", json={
        "date": "2026-11-17",
        "meal_type": "夕食",
        "items": [
            {"food_id": food_id, "grams": 0},
        ],
    })

    assert response.status_code == 422

def test_create_unknown_food_saves_nothing():
    reset_db()
    food_id = add_food("00001", "にわとり　むね　生")

    response = client.post("/meals", json={
        "date": "2026-11-17",
        "meal_type": "夕食",
        "items": [
            {"food_id": food_id, "grams": 150},
            {"food_id": 99999, "grams": 100},
        ],
    })

    assert response.status_code == 422

    response = client.get("/meals", params={"date": "2026-11-17"})

    assert response.status_code == 200
    assert len(response.json()) == 0

def test_list_by_date():
    reset_db()
    food_id = add_food("00001", "にわとり　むね　生")

    response = client.post("/meals", json={
        "date": "2026-11-17",
        "meal_type": "夕食",
        "items": [
            {"food_id": food_id, "grams": 150},
        ],
    })

    response = client.post("/meals", json={
        "date": "2026-11-16",
        "meal_type": "夕食",
        "items": [
            {"food_id": food_id, "grams": 150},
        ],
    })

    response =client.get("/meals", params={"date": "2026-11-17"})
    data = response.json()

    assert response.status_code == 200
    assert data[0]["date"] == "2026-11-17"
    assert len(data) == 1

def test_null_nutrition():
    reset_db()
    food_id = add_food("00001", "テスト食品", protein=None)
    response = client.post("/meals", json={
        "date": "2026-11-17",
        "meal_type": "夕食",
        "items": [{"food_id": food_id, "grams": 100}],
    })
    data =response.json()
    assert response.status_code == 201
    assert data[0]["protein"] is None

def test_delete_meal():
    reset_db()
    food_id = add_food("00001", "にわとり　むね　生")
    response = client.post("/meals", json={
        "date": "2026-11-17",
        "meal_type": "夕食",
        "items" : [
            {"food_id": food_id, "grams": 100}
        ],
    })

    meal_id =response.json()[0]["id"]

    response = client.delete(f"/meals/{meal_id}")

    assert response.status_code == 200
    response = client.get("/meals", params={"date": "2026-11-17"})
    data = response.json()
    assert len(data) == 0