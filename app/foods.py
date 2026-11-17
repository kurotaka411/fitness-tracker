import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.database import get_db

router = APIRouter(prefix="/foods", tags=["foods"]) #ここでAPIごとにファイルを仕分け

MAX_RESULTS = 20    #最大表示を20で定義


class Food(BaseModel):  #設計書に記載の通りの定義
    id: int
    code: str | None
    name: str
    calories: float | None
    protein: float | None
    fat: float | None
    carbs: float | None


def _escape_like(word: str) -> str:
    """LIKE で特別な意味を持つ文字（\\ % _）を、ただの文字として扱えるようにする。"""
    return word.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")   #wildcardでの入力を避ける


@router.get("", response_model=list[Food])
def search_foods(keyword: str = Query(...), conn: sqlite3.Connection = Depends(get_db)):
    """keyword をスペース（半角・全角）で分け、すべての言葉を名前に含む食品を返す。"""
    words = keyword.split()  # 引数なしの split() は半角・全角どちらのスペースでも分ける
    if not words:
        raise HTTPException(status_code=422, detail="keyword is empty")

    conditions = " AND ".join(["name LIKE ? ESCAPE '\\'"] * len(words))
    params = [f"%{_escape_like(w)}%" for w in words]
    rows = conn.execute(
        f"""
        SELECT id, code, name, calories, protein, fat, carbs FROM foods
        WHERE {conditions}
        ORDER BY LENGTH(name), code IS NULL, code, id
        LIMIT ?
        """,
        (*params, MAX_RESULTS),
    ).fetchall()
    return [dict(r) for r in rows]  #ここが検索部分
