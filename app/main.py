from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.db import init_db
from app.routers import tasks, sessions
from app.session_manager import session_manager
from app import blocker

app = FastAPI(title="Study Assistant")


@app.on_event("startup")
def _startup():
    init_db()
    # Clean up any stale assistant lock left by a previous backend crash
    blocker.release("assistant")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            # Backend is the authoritative timer: stream state every second.
            await ws.send_text(
                json.dumps({"type": "state", "state": session_manager.state()})
            )
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass


app.include_router(tasks.router)
app.include_router(sessions.router)
