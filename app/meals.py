import sqlite3
from datetime import date
from typing import Literal  #これなになんのライブラリ？

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.database import get_db

router = APIRouter(prefix="/meals", tags=["meals"]) #ルーターを今回は/mealsで作成

MealType = Literal["朝食", "昼食", "夕食", "間食"]  #存在する食事類をこの四種で限定


class MealItem(BaseModel): #各食材に対し、グラム数での管理
    food_id: int
    grams: float = Field(gt=0)


class MealCreate(BaseModel):    #日付とどの食事か、その中に先ほどclassで書いたmealitemをリストとして入れる。（作ったリストの中には最低一つの食事は入る。）
    date: date
    meal_type: MealType
    items: list[MealItem] = Field(min_length=1)


class MealUpdate(BaseModel):    #先ほどの更新用のもの
    date: date
    meal_type: MealType
    food_id: int
    grams: float = Field(gt=0)


class Meal(BaseModel):  #各定義をつくっている
    id: int
    date: str
    meal_type: str
    food_id: int
    food_name: str
    grams: float
    calories: float | None
    protein: float | None
    fat: float | None
    carbs: float | None


# foods と JOIN して、食品名とその量での栄養を返す SELECT。
# 「100gあたりの値 × grams ÷ 100」。foods の値が NULL なら、計算結果も NULL になる。
SELECT_MEALS = """
    SELECT
        m.id, m.date, m.meal_type, m.food_id, f.name AS food_name, m.grams,
        f.calories * m.grams / 100 AS calories,
        f.protein  * m.grams / 100 AS protein,
        f.fat      * m.grams / 100 AS fat,
        f.carbs    * m.grams / 100 AS carbs
    FROM meals AS m
    JOIN foods AS f ON f.id = m.food_id
"""


def _check_food_ids(conn: sqlite3.Connection, food_ids: list[int]) -> None:
    """存在しない food_id があれば 422 にする。"""
    unique_ids = sorted(set(food_ids))
    placeholders = ", ".join(["?"] * len(unique_ids))
    rows = conn.execute(
        f"SELECT id FROM foods WHERE id IN ({placeholders})", unique_ids
    ).fetchall()
    missing = set(unique_ids) - {r["id"] for r in rows}
    if missing:
        raise HTTPException(
            status_code=422, detail=f"food_id not found: {sorted(missing)}"
        )


def _fetch_one(conn: sqlite3.Connection, meal_id: int) -> sqlite3.Row | None:
    return conn.execute(SELECT_MEALS + " WHERE m.id = ?", (meal_id,)).fetchone()


@router.post("", status_code=201, response_model=list[Meal])
def create_meals(body: MealCreate, conn: sqlite3.Connection = Depends(get_db)):
    """1回の食事を、複数の食品をまとめて記録する。1品でもおかしければ何も保存しない。"""
    _check_food_ids(conn, [item.food_id for item in body.items])
    day = body.date.isoformat()
    ids: list[int] = []
    with conn:
        for item in body.items:
            cur = conn.execute(
                "INSERT INTO meals (date, meal_type, food_id, grams) VALUES (?, ?, ?, ?)",
                (day, body.meal_type, item.food_id, item.grams),
            )
            ids.append(cur.lastrowid)
    return [dict(_fetch_one(conn, i)) for i in ids]


@router.get("", response_model=list[Meal])
def list_meals(date: date = Query(...), conn: sqlite3.Connection = Depends(get_db)):
    rows = conn.execute(
        SELECT_MEALS + " WHERE m.date = ? ORDER BY m.id", (date.isoformat(),)
    ).fetchall()
    return [dict(r) for r in rows]


@router.put("/{meal_id}", response_model=Meal)
def update_meal(meal_id: int, body: MealUpdate, conn: sqlite3.Connection = Depends(get_db)):
    """date・meal_type・food_id・grams をすべて置き換える。"""
    exists = conn.execute("SELECT 1 FROM meals WHERE id = ?", (meal_id,)).fetchone()
    if exists is None:
        raise HTTPException(status_code=404, detail="meal not found")
    _check_food_ids(conn, [body.food_id])
    with conn:
        conn.execute(
            "UPDATE meals SET date = ?, meal_type = ?, food_id = ?, grams = ? WHERE id = ?",
            (body.date.isoformat(), body.meal_type, body.food_id, body.grams, meal_id),
        )
    return dict(_fetch_one(conn, meal_id))


@router.delete("/{meal_id}")
def delete_meal(meal_id: int, conn: sqlite3.Connection = Depends(get_db)):
    with conn:
        cur = conn.execute("DELETE FROM meals WHERE id = ?", (meal_id,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="meal not found")
    return {"id": meal_id}
