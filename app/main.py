from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import workouts
from app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="fitness-tracker", lifespan=lifespan)
app.include_router(workouts.router)
