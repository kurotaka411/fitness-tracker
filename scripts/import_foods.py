"""日本食品標準成分表（Excel）を読み込み、foods テーブルに保存するスクリプト。

使い方（プロジェクトのルートで実行）:
    python scripts/import_foods.py

取り込み方は design.md の「成分表からの取り込み方」に従う。
食品番号（code）が同じ行は上書きするので、何度実行しても重複しない。
"""

import re #正規表現に当てはまるかどうかの確認
import sys #Python自体の設定を扱う標準ライブラリ
from pathlib import Path    #知らないけどなんとなくわかる。

import openpyxl #Excelを用いるための外部ライブラリ

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.database import DB_PATH, connect, init_db  # noqa: E402

DATA_DIR = ROOT / "data"
SHEET_NAME = "表全体"
FIRST_ROW = 13  #開始する行

# 項目名 → Excel の列
COLUMNS = {
    "code": "B",
    "name": "D",
    "calories": "G",
    "protein": "J",
    "fat": "M",
    "carbs": "U",
}
NUMBER_FIELDS = ["calories", "protein", "fat", "carbs"]

NUMBER_RE = re.compile(r"-?\d+(\.\d+)?")    #何やっているかわからん
PAREN_RE = re.compile(r"\((.+)\)")  #何やっているかわからん


def find_excel() -> Path:
    files = sorted(DATA_DIR.glob("*.xlsx"))
    if len(files) != 1:
        raise SystemExit(f"data フォルダに .xlsx が1つだけある状態にしてください（見つかった数: {len(files)}）")
    return files[0]     #ファイルの数を確認する関数ここでいうfile[0]はなに？最初のファイル？


def parse_value(raw, counts: dict[str, int]) -> float | None:
    """セルの値を数値（または None）にする。記号があれば counts に数える。

    - (数値) → 括弧を外して数値（(0) も含む）
    - Tr → 0
    - - → None
    """
    if isinstance(raw, (int, float)):
        return float(raw)
    if raw is None:
        raise ValueError("空のセル")

    text = str(raw).strip()
    if text == "-":
        counts["-"] += 1
        return None
    if text == "Tr":
        counts["Tr"] += 1
        return 0.0  #ここの二つで、Trと-の扱いを定めている

    m = PAREN_RE.fullmatch(text)
    if m:
        counts["括弧付き"] += 1 #そのままの数値を用いている
        inner = m.group(1).strip()
        # 成分表には (Tr) もある。括弧付きとして数え、Tr と同じく 0 にする
        if inner == "Tr":
            return 0.0
        if NUMBER_RE.fullmatch(inner):
            return float(inner)
        raise ValueError(f"想定していない値: {raw!r}")

    if NUMBER_RE.fullmatch(text):
        return float(text) #数字が文字列として入っていたときに数値に変換
    raise ValueError(f"想定していない値: {raw!r}")


def read_foods(path: Path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[SHEET_NAME]
        idx = {key: openpyxl.utils.column_index_from_string(col) - 1 for key, col in COLUMNS.items()}
        counts = {field: {"括弧付き": 0, "Tr": 0, "-": 0} for field in NUMBER_FIELDS}
        foods = []
        for row_no, row in enumerate(ws.iter_rows(min_row=FIRST_ROW, values_only=True), start=FIRST_ROW):
            code = row[idx["code"]]
            if code is None or str(code).strip() == "":
                continue  # 末尾の空行
            food = {"code": str(code).strip(), "name": str(row[idx["name"]]).strip()}
            for field in NUMBER_FIELDS:
                try:
                    food[field] = parse_value(row[idx[field]], counts[field])
                except ValueError as e:
                    raise SystemExit(f"{row_no}行目 {COLUMNS[field]}列（{field}）: {e}")
            foods.append(food)
        return foods, counts
    finally:
        wb.close()
    #Excelの行を１行づつ読んで、食品の辞書のリストを作成。そのついでに(),Tr,-の数と項目をカウントしている？

def save_foods(foods: list[dict]) -> tuple[int, int]:
    """foods を保存する。戻り値は (保存前の件数, 保存後の件数)。"""
    init_db()
    conn = connect()
    try:
        before = conn.execute("SELECT COUNT(*) FROM foods").fetchone()[0]
        with conn:
            conn.executemany(
                """
                INSERT INTO foods (code, name, calories, protein, fat, carbs)
                VALUES (:code, :name, :calories, :protein, :fat, :carbs)
                ON CONFLICT(code) DO UPDATE SET
                    name = excluded.name,
                    calories = excluded.calories,
                    protein = excluded.protein,
                    fat = excluded.fat,
                    carbs = excluded.carbs
                """,
                foods,
            )
        after = conn.execute("SELECT COUNT(*) FROM foods").fetchone()[0]
        return before, after
    finally:
        conn.close()


def main() -> None:
    path = find_excel()
    print(f"読み込み: {path.name}")
    foods, counts = read_foods(path)
    before, after = save_foods(foods)

    print(f"保存先: {DB_PATH}")
    print(f"取り込んだ件数: {len(foods)} 件（新規 {after - before} 件、更新 {len(foods) - (after - before)} 件）")
    print("列ごとの記号の件数:")
    print(f"  {'列':<10}{'括弧付き':>8}{'Tr':>6}{'-':>6}")
    for field in NUMBER_FIELDS:
        c = counts[field]
        print(f"  {field:<10}{c['括弧付き']:>8}{c['Tr']:>6}{c['-']:>6}")


if __name__ == "__main__":
    main()
