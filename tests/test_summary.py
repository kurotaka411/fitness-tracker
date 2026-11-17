import os

from fastapi.testclient import TestClient

from app import database
from app.main import app

TEST_DB = "test_fitness.db"


def override_get_db():
    conn = database.connect(TEST_DB)
    try:
        yield conn
    finally:
        conn.close()


app.dependency_overrides[database.get_db] = override_get_db
client = TestClient(app)


def reset_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    database.init_db(TEST_DB)


def add_food(code, name, calories=100, protein=10, fat=5, carbs=10):
    conn = database.connect(TEST_DB)
    with conn:
        cur = conn.execute(
            "INSERT INTO foods (code, name, calories, protein, fat, carbs) VALUES (?, ?, ?, ?, ?, ?)",
            (code, name, calories, protein, fat, carbs),
        )
    conn.close()
    return cur.lastrowid

def add_meal(date, meal_type, food_id, grams):
    client.post("/meals", json={
        "date": date,
        "meal_type": meal_type,
        "items": [{"food_id": food_id, "grams": grams}],
    })


def add_workout(date, exercise, weight, reps, sets):
    client.post("/workouts", json={
        "date": date,
        "items": [{"exercise": exercise, "weight": weight, "reps": reps, "sets": sets}],
    })


def test_summary_empty():
    reset_db()
    response = client.get("/summary", params={"date": "2026-11-17"})
    data = response.json()
    assert response.status_code == 200

    assert data["nutrition"]["total"]["calories"] == 0
    assert len(data["nutrition"]["by_meal_type"]) == 4
    assert data["nutrition"]["by_meal_type"]["朝食"]["calories"] == 0

    assert data["nutrition"]["missing"]["protein"] == 0

    assert data["training"] == []

def test_summary_nutrition():
    reset_db()
    food_id = add_food("00001", "にわとり　むね　生", calories=200, protein=20)

    add_meal("2026-11-17", "朝食", food_id, 100)
    add_meal("2026-11-17", "夕食", food_id, 150)
    response = client.get("/summary", params={"date":"2026-11-17"})

    assert response.status_code == 200
    data = response.json()
    assert data["nutrition"]["total"]["calories"] == 500
    assert data["nutrition"]["by_meal_type"]["朝食"]["calories"] == 200
    assert data["nutrition"]["by_meal_type"]["夕食"]["calories"] == 300
    assert data["nutrition"]["by_meal_type"]["昼食"]["calories"] == 0
        
def test_summary_missing():
    reset_db()
    food_id1 = add_food("00001", "にわとり　むね　生", protein=20)
    food_id2 = add_food("00002", "にわとり　むね　生", protein=None)
    add_meal("2026-11-17", "夕食", food_id1, 100)
    add_meal("2026-11-17", "夕食", food_id2, 100)

    response = client.get("/summary", params={"date": "2026-11-17"})

    assert response.status_code == 200
    data = response.json()
    assert data["nutrition"]["missing"]["protein"] == 1
    assert data["nutrition"]["total"]["protein"] == 20

def test_summary_training():
    reset_db()
    add_workout("2026-11-17", "ベンチプレス", 60, 10, 3)
    add_workout("2026-11-17", "スクワット", 80, 5, 2)

    response=client.get("/summary", params={"date": "2026-11-17"})

    assert response.status_code == 200
    data = response.json()
    assert len(data["training"]) == 2
    assert data["training"][0]["exercise"] == "ベンチプレス"
    assert data["training"][0]["sets"] ==   3
    assert data["training"][0]["volume"] == 1800
    assert data["training"][0]["top_weight"] == 60

def test_summary_other_date():
    reset_db()
    food_id = add_food("00001", "にわとり　むね　生", calories=100)
    add_meal("2026-11-16","夕食", food_id, 100)
    add_meal("2026-11-17", "夕食", food_id, 100)
    add_workout("2026-11-16", "ベンチプレス", 60, 5, 3)
    add_workout("2026-11-17", "ベンチプレス", 60, 5, 3)

    response = client.get("/summary", params={"date": "2026-11-17"})
    assert response.status_code == 200
    data = response.json()
    assert data["nutrition"]["total"]["calories"] == 100
    assert len(data["training"]) == 1
    assert data["training"][0]["sets"] == 3