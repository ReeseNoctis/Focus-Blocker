from __future__ import annotations

import sys
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


def finalize_session(result: dict) -> dict:
    """Persist a finished session and update its task, then return the
    response payload.  Shared by the manual ``/stop`` handler and the
    backend expiry watchdog."""
    with get_conn() as conn:
        # The task may have been deleted mid-session — record as free focus
        # instead of tripping the FK constraint on INSERT.
        if result["task_id"] is not None:
            exists = conn.execute(
                "SELECT 1 FROM tasks WHERE id = ?", (result["task_id"],)
            ).fetchone()
            if not exists:
                result["task_id"] = None

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
                "UPDATE tasks SET focus_seconds = focus_seconds + ?, status = ?, completed_at = ? WHERE id = ?",
                (result["duration_seconds"],
                 TASK_DONE if result["completed"] else TASK_IN_PROGRESS,
                 now if result["completed"] else None,
                 result["task_id"]),
            )
    return {"session": result, "state": session_manager.state()}


@router.post("/stop")
def stop_session(body: StopBody = StopBody()):
    result = session_manager.stop(completed=body.completed)
    if result is None:
        raise HTTPException(409, "no active session")

    ok, err = blocker.release("assistant")

    resp = finalize_session(result)
    if not ok:
        warning = f"failed to unblock sites: {err}"
        print(warning, file=sys.stderr)
        resp["warning"] = warning
    else:
        resp["warning"] = None
    return resp


@router.post("/pause")
def pause_session():
    if session_manager.pause() is None:
        raise HTTPException(409, "no active session or already paused")
    # Pausing is a break from focusing — unblock sites per user preference.
    ok, err = blocker.release("assistant")
    state = session_manager.state()
    if not ok:
        print(f"failed to unblock sites on pause: {err}", file=sys.stderr)
        state["warning"] = f"failed to unblock sites: {err}"
    return state


@router.post("/resume")
def resume_session():
    if session_manager.resume() is None:
        raise HTTPException(409, "no active session or not paused")
    ok, err = blocker.acquire("assistant")
    if not ok:
        # Re-blocking failed — roll back to paused so the clock stays frozen.
        session_manager.pause()
        raise HTTPException(502, f"block failed: {err}")
    return session_manager.state()


@router.get("/current")
def current_session():
    return session_manager.state()
