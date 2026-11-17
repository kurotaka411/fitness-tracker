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