from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import get_conn, TASK_DONE, TASK_IN_PROGRESS
from app.session_manager import session_manager
from app import blocker

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class StartBody(BaseModel):
    task_id: Optional[int] = None
    minutes: int = 25


class StopBody(BaseModel):
    completed: bool = False


@router.post("/start")
def start_session(body: StartBody):
    try:
        session_manager.start(body.task_id, body.minutes)
    except RuntimeError:
        raise HTTPException(409, "a session is already running")

    ok, err = blocker.acquire("assistant")
    if not ok:
        session_manager._current = None  # rollback
        raise HTTPException(502, f"block failed: {err}")

    if body.task_id is not None:
        with get_conn() as conn:
            conn.execute(
                "UPDATE tasks SET status = ? WHERE id = ?",
                (TASK_IN_PROGRESS, body.task_id),
            )
    return session_manager.state()


@router.post("/stop")
def stop_session(body: StopBody = StopBody()):
    result = session_manager.stop(completed=body.completed)
    if result is None:
        raise HTTPException(409, "no active session")

    blocker.release("assistant")

    with get_conn() as conn:
        start_iso = datetime.fromtimestamp(result["started_at"]).isoformat(timespec="seconds")
        now = datetime.now().isoformat(timespec="seconds")
        conn.execute(
            "INSERT INTO focus_sessions (task_id, start_time, end_time, duration_seconds, completed) "
            "VALUES (?, ?, ?, ?, ?)",
            (result["task_id"], start_iso, now, result["duration_seconds"],
             1 if result["completed"] else 0),
        )
        if result["task_id"] is not None:
            conn.execute(
                "UPDATE tasks SET focus_seconds = focus_seconds + ?, status = ? WHERE id = ?",
                (result["duration_seconds"],
                 TASK_DONE if result["completed"] else TASK_IN_PROGRESS,
                 result["task_id"]),
            )
    return {"session": result, "state": session_manager.state()}


@router.get("/current")
def current_session():
    return session_manager.state()
