from tests.helpers import client, reset_db, add_food, add_meal, add_workout

def test_create_expands_set():
    reset_db()

    response = client.post("/workouts", json={
        "date": "2026-11-11",
        "items": [
            {"exercise": "ベンチプレス", "weight": 55, "reps": 10, "sets": 3},
            {"exercise": "ベンチプレス", "weight": 60, "reps": 1, "sets": 1},
        ],
    })

    assert response.status_code ==201
    assert len(response.json()) == 4

def test_delete_not_found():
    reset_db()

    response = client.delete("/workouts/99")
    assert response.status_code == 404

def test_create_invalid_weight():
    reset_db()

    response = client.post("/workouts",json={
        "date": "2026-11-11",
        "items": [
            {"exercise": "ベンチプレス", "weight": -5, "reps": 10, "sets": 3},
        ],
    })

    assert response.status_code == 422

def test_list_by_date():
    reset_db()

    response = client.post("/workouts",json={
        "date": "2026-11-10",
        "items": [
            {"exercise": "ベンチプレス", "weight": 55, "reps": 10, "sets": 1},
        ],
    })

    response = client.post("/workouts",json={
        "date": "2026-11-11",
        "items": [
            {"exercise": "ベンチプレス", "weight": 55, "reps": 10, "sets": 2},
        ],
    })

    response =client.get("/workouts", params={"date": "2026-11-11"})

    assert response.status_code == 200
    assert len(response.json()) == 2

def test_latest():
    reset_db()

    response = client.post("/workouts",json={
        "date": "2026-11-10",
        "items": [
            {"exercise": "ベンチプレス", "weight": 55, "reps": 10, "sets": 3},
        ],
    })

    response = client.post("/workouts",json={
        "date": "2026-11-11",
        "items": [
            {"exercise": "ベンチプレス", "weight": 55, "reps": 10, "sets": 1},
        ],
    })

    response = client.get("/workouts/latest?exercise=ベンチプレス")

    assert response.status_code == 200
    assert len(response.json()) == 1