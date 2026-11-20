import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "fitness.db"
#Path(__file__)これでこのファイルの場所を基準に決まった場所に作られる。.resolve()：C:\から始まる完全な場所にする。.parent:cd..と同義 

def connect(db_path: Path | str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
#databaseとつなげている db_path: Path | str = DB_PATH:これで接続先を引数にて変更できる

def init_db(db_path: Path | str = DB_PATH) -> None:
    conn = connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workouts (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                date     TEXT    NOT NULL,
                exercise TEXT    NOT NULL,
                weight   REAL    NOT NULL,
                reps     INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS foods (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                code     TEXT    UNIQUE,
                name     TEXT    NOT NULL,
                calories REAL,
                protein  REAL,
                fat      REAL,
                carbs    REAL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS meals (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                date      TEXT    NOT NULL,
                meal_type TEXT    NOT NULL,
                food_id   INTEGER NOT NULL REFERENCES foods(id),
                grams     REAL    NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()
#sqlにてdatabaseに表を作る関数。何もなければ作成する。autoincrement；重複を禁止するもの。finallyはどんなことがあっても必ず実行される部分

def get_db():
    """FastAPI の依存関係として使う。リクエストごとに接続を開いて閉じる。"""
    conn = connect()
    try:
        yield conn #connを渡して、一時停止。その後、list_workoutsが実行される。レスポンスを返して、get_db()を再開する
    finally:
        conn.close()
