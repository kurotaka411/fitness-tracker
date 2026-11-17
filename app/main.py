from contextlib import asynccontextmanager

from fastapi import FastAPI

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
