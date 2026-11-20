from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import foods, meals, summary, workouts
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="fitness-tracker", lifespan=lifespan)
app.include_router(workouts.router)
app.include_router(foods.router)
app.include_router(meals.router)
app.include_router(summary.router)

# 画面（static フォルダの HTML・CSS・JavaScript）
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")
