from fastapi import FastAPI

from app.db import init_db
from app.routers import tasks

app = FastAPI(title="Study Assistant")


@app.on_event("startup")
def _startup():
    init_db()


app.include_router(tasks.router)
