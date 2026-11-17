import sqlite3
from datetime import date
from typing import get_args

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.database import get_db
from app.meals import MealType

router = APIRouter(prefix="/summary", tags=["summary"])

MEAL_TYPES: tuple[str, ...] = get_args(MealType)  # ("朝食", "昼食", "夕食", "間食")


class Nutrients(BaseModel):
    calories: float
    protein: float
    fat: float
    carbs: float


class MissingCounts(BaseModel):
    calories: int
    protein: int
    fat: int
    carbs: int


class Nutrition(BaseModel):
    total: Nutrients
    by_meal_type: dict[str, Nutrients]
    missing: MissingCounts


class TrainingItem(BaseModel):
    exercise: str
    sets: int
    volume: float
    top_weight: float


class Summary(BaseModel):
    date: str
    nutrition: Nutrition
    training: list[TrainingItem]


# 「100gあたりの値 × grams ÷ 100」の合計。SUM は NULL の品を飛ばす。
# 記録が1件もないと SUM は NULL になるので、COALESCE で 0 にする。
NUTRIENT_SUMS = """
    COALESCE(SUM(f.calories * m.grams / 100), 0) AS calories,
    COALESCE(SUM(f.protein  * m.grams / 100), 0) AS protein,
    COALESCE(SUM(f.fat      * m.grams / 100), 0) AS fat,
    COALESCE(SUM(f.carbs    * m.grams / 100), 0) AS carbs
"""


def _nutrition(conn: sqlite3.Connection, day: str) -> Nutrition:
    # 合計と、NULL（未測定）だった品の数。COUNT(列) は NULL を数えないので、COUNT(*) との差が NULL の数になる。
    row = conn.execute(
        f"""
        SELECT
            {NUTRIENT_SUMS},
            COUNT(*) - COUNT(f.calories) AS missing_calories,
            COUNT(*) - COUNT(f.protein)  AS missing_protein,
            COUNT(*) - COUNT(f.fat)      AS missing_fat,
            COUNT(*) - COUNT(f.carbs)    AS missing_carbs
        FROM meals AS m
        JOIN foods AS f ON f.id = m.food_id
        WHERE m.date = ?
        """,
        (day,),
    ).fetchone()

    # meal_type ごとの合計。記録がない区分は 0 で埋めて、4つすべて返す。
    rows = conn.execute(
        f"""
        SELECT m.meal_type, {NUTRIENT_SUMS}
        FROM meals AS m
        JOIN foods AS f ON f.id = m.food_id
        WHERE m.date = ?
        GROUP BY m.meal_type
        """,
        (day,),
    ).fetchall()
    found = {r["meal_type"]: r for r in rows}
    zero = {"calories": 0, "protein": 0, "fat": 0, "carbs": 0}
    by_meal_type = {
        t: Nutrients(**({k: found[t][k] for k in zero} if t in found else zero))
        for t in MEAL_TYPES
    }

    return Nutrition(
        total=Nutrients(calories=row["calories"], protein=row["protein"], fat=row["fat"], carbs=row["carbs"]),
        by_meal_type=by_meal_type,
        missing=MissingCounts(
            calories=row["missing_calories"],
            protein=row["missing_protein"],
            fat=row["missing_fat"],
            carbs=row["missing_carbs"],
        ),
    )


def _training(conn: sqlite3.Connection, day: str) -> list[TrainingItem]:
    # 種目ごとに集計し、その種目を最初に記録した順（id が一番小さい順）に並べる。
    rows = conn.execute(
        """
        SELECT
            exercise,
            COUNT(*)            AS sets,
            SUM(weight * reps)  AS volume,
            MAX(weight)         AS top_weight
        FROM workouts
        WHERE date = ?
        GROUP BY exercise
        ORDER BY MIN(id)
        """,
        (day,),
    ).fetchall()
    return [TrainingItem(**dict(r)) for r in rows]


@router.get("", response_model=Summary)
def get_summary(date: date = Query(...), conn: sqlite3.Connection = Depends(get_db)):
    """その日の食事と筋トレのまとめを、記録からその場で計算して返す（保存はしない）。"""
    day = date.isoformat()
    return Summary(date=day, nutrition=_nutrition(conn, day), training=_training(conn, day))
