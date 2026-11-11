import sqlite3
from datetime import date   #日付を扱う標準ライブラリ　dateは日付

from fastapi import APIRouter, Depends, HTTPException, Query    #APIRouterでAPIを各ファイルごとに分ける
from pydantic import BaseModel, Field   #Fieldで型以外の条件を足すことができるようになる

from app.database import get_db #app.databaseからデータベースを持ってくる

router = APIRouter(prefix="/workouts", tags=["workouts"])   #これは不明


class WorkoutItem(BaseModel):   #classでルールを定める
    exercise: str = Field(min_length=1) #エクササイズの種類　よって文字列で表記
    weight: float = Field(ge=0) #重さ　小数点を含む
    reps: int = Field(ge=1) #回数　整数
    sets: int = Field(ge=1) #セット数　整数


class WorkoutCreate(BaseModel):
    date: date  #日付
    items: list[WorkoutItem] = Field(min_length=1)  #行った筋トレについて、日ごとにリスト化


class WorkoutUpdate(BaseModel): #これは更新要因。PUTで一行だけを直す要因
    date: date
    exercise: str = Field(min_length=1)
    weight: float = Field(ge=0)
    reps: int = Field(ge=1)


class Workout(BaseModel):   #返すデータの形
    id: int #各項目にIDを付ける
    date: str #日付
    exercise: str #これも同様に筋トレの種類を入力してもらう
    weight: float   #以下同様
    reps: int


def _fetch_one(conn: sqlite3.Connection, workout_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT id, date, exercise, weight, reps FROM workouts WHERE id = ?",
        (workout_id,),
    ).fetchone()
#ここの定義で、workout_idに紐づいている各項目をsqlに落とし込む。実行までをreturnで返す

@router.post("", status_code=201, response_model=list[Workout])
def create_workouts(body: WorkoutCreate, conn: sqlite3.Connection = Depends(get_db)):   #Depends（）:この関数が呼ばれる前に、get_dbを実行して、その結果をconnに入れてという仕組み
    """sets の数だけ 1 セット 1 行に展開して保存する。"""
    day = body.date.isoformat() #isoformat()とは何だ
    ids: list[int] = []
    with conn:
        for item in body.items:
            for _ in range(item.sets):
                cur = conn.execute(
                    "INSERT INTO workouts (date, exercise, weight, reps) VALUES (?, ?, ?, ?)",
                    (day, item.exercise, item.weight, item.reps),
                )
                ids.append(cur.lastrowid)   #ここ何しているのかよくわからない。存在するセットのリストの数for文で回して、対応する筋トレをinsertしている？
    return [dict(_fetch_one(conn, i)) for i in ids] #ここはリストをfor文で回して、appendして返すやつを一行にしている


@router.get("", response_model=list[Workout])
def list_workouts(date: date = Query(...) , conn: sqlite3.Connection = Depends(get_db)):    #Query(...)：引数がクエリパラメーター(?date=...)であることを明示する。...は必須という意味。省略すると４２２
    rows = conn.execute(
        "SELECT id, date, exercise, weight, reps FROM workouts WHERE date = ? ORDER BY id",
        (date.isoformat(),),    #target_dateのように違う名前にすると取り違えを防げそう
    ).fetchall()
    return [dict(r) for r in rows]
    #日付ごとに、その日行った筋トレの履歴を返す

@router.get("/latest", response_model=list[Workout])
def latest_workouts(
    exercise: str = Query(..., min_length=1), conn: sqlite3.Connection = Depends(get_db)
):
    """その種目の、一番最近の日の記録（全セット）を返す。"""
    rows = conn.execute(
        """
        SELECT id, date, exercise, weight, reps FROM workouts
        WHERE exercise = ?
        AND date = (SELECT MAX(date) FROM workouts WHERE exercise = ?)
        ORDER BY id
        """,
        (exercise, exercise),
    ).fetchall()
    return [dict(r) for r in rows]


@router.put("/{workout_id}", response_model=Workout)
def update_workout(
    workout_id: int, body: WorkoutUpdate, conn: sqlite3.Connection = Depends(get_db)
):
    with conn:
        cur = conn.execute(
            "UPDATE workouts SET date = ?, exercise = ?, weight = ?, reps = ? WHERE id = ?",
            (body.date.isoformat(), body.exercise, body.weight, body.reps, workout_id),
        )
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="workout not found")
    return dict(_fetch_one(conn, workout_id))
#ある筋トレの種類を更新する動作


@router.delete("/{workout_id}")
def delete_workout(workout_id: int, conn: sqlite3.Connection = Depends(get_db)):
    with conn:
        cur = conn.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="workout not found")
    return {"id": workout_id}
#ある筋トレの種類を消す動作
