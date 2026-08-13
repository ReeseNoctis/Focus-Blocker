from __future__ import annotations

import asyncio
import json
import sys

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.db import init_db
from app.routers import tasks, sessions
from app.routers.sessions import finalize_session
from app.session_manager import session_manager
from app import blocker

app = FastAPI(title="Study Assistant")


async def _expiry_watchdog():
    """Background enforcement of session expiry — auto-complete is normally
    client-driven, but if the browser is closed a session would otherwise run
    forever.  Polls every second and completes elapsed sessions server-side."""
    while True:
        try:
            await asyncio.sleep(1)
            result = session_manager.expire_if_done()
            if result is not None:
                # release runs a blocking sudo subprocess — keep it off the
                # event loop so WS streaming / REST stay responsive.
                await asyncio.to_thread(blocker.release, "assistant")
                finalize_session(result)
        except Exception as exc:
            # A transient error (e.g. SQLite locked) must not kill the watchdog
            # forever — log and keep polling.
            print(f"expiry watchdog error: {exc}", file=sys.stderr)


@app.on_event("startup")
async def _startup():
    init_db()
    # Clean up any stale assistant lock left by a previous backend crash
    blocker.release("assistant")
    asyncio.create_task(_expiry_watchdog())


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
