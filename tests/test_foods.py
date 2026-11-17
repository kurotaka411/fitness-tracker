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
        conn.execute(
            "INSERT INTO foods (code, name, calories, protein, fat, carbs) VALUES (?, ?, ?, ?, ?, ?)",
            (code, name, calories, protein, fat, carbs),
        )
    conn.close()

def test_search_one_word():
    reset_db()
    add_food("00001", "にわとり　むね　生")
    add_food("00002", "にわとり　もも　生")
    add_food("00003", "ぶた　ロース　生")
    response = client.get("/foods", params={"keyword": "むね"})

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert "むね" in data[0]["name"]

def test_search_multiple_words():
    reset_db()
    add_food("00001", "にわとり　むね　生")
    add_food("00002", "にわとり　もも　生")
    add_food("00003", "うし　むね　生")
    response = client.get("/foods", params={"keyword": "にわとり むね"})

    data = response.json()
    assert response.status_code == 200
    assert len(data) == 1
    assert "にわとり　むね" in data[0]["name"]

def test_search_order():
    reset_db()
    add_food("00001", "にわとり　むね　皮なし　生")
    add_food("00002", "にわとり　むね　生")

    response = client.get("/foods", params={"keyword": "むね"})
    data =response.json()
    assert response.status_code == 200

    assert data[0]["name"] == "にわとり　むね　生"
    assert data[1]["name"] == "にわとり　むね　皮なし　生"

def test_search_limit():
    reset_db()

    for i in range(25):
        add_food(f"{i:05d}", f"テスト{i}")

    response = client.get("/foods", params={"keyword": "テスト"})

    data = response.json()
    assert response.status_code == 200
    assert len(data) == 20

def test_search_empty_keyword():
    reset_db()
    response = client.get("/foods", params={"keyword": "　"})

    assert response.status_code == 422

def test_search_percent():
    reset_db()
    add_food("00001", "100%ジュース")
    add_food("00002", "りんご")

    response = client.get("/foods", params={"keyword": "%"})
    data = response.json()
    assert response.status_code == 200
    assert data[0]["name"] == "100%ジュース"
    assert len(data) == 1