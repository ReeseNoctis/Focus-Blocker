from __future__ import annotations

import sqlite3
from datetime import date, datetime

from fastapi import APIRouter, HTTPException, Query

from app.db import get_conn, TASK_DONE, TASK_PENDING
from app.models import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


def _row_to_task(row: sqlite3.Row) -> TaskOut:
    return TaskOut(
        id=row["id"],
        title=row["title"],
        planned_minutes=row["planned_minutes"],
        status=row["status"],
        sort_order=row["sort_order"],
        created_date=row["created_date"],
        focus_seconds=row["focus_seconds"],
        completed_at=row["completed_at"],
    )


@router.get("", response_model=list[TaskOut])
def list_tasks(date_: str = Query("", alias="date")):
    d = date_ or date.today().isoformat()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE created_date = ? ORDER BY sort_order, id",
            (d,),
        ).fetchall()
    return [_row_to_task(r) for r in rows]


@router.post("", response_model=TaskOut, status_code=201)
def create_task(body: TaskCreate):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title, planned_minutes, status, sort_order, created_date, focus_seconds) "
            "VALUES (?, ?, ?, ?, ?, 0)",
            (body.title, body.planned_minutes, TASK_PENDING, body.sort_order,
             date.today().isoformat()),
        )
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _row_to_task(row)


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, body: TaskUpdate):
    data = body.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in ("pending", "in_progress", "done"):
        raise HTTPException(400, "invalid status")
    if "status" in data and data["status"] == TASK_DONE:
        data["completed_at"] = datetime.now().isoformat(timespec="seconds")
    if "status" in data and data["status"] != TASK_DONE:
        data["completed_at"] = None

    # Whitelisted field names — no user-controlled column names reach SQL.
    allowed = {"title", "planned_minutes", "status", "sort_order", "completed_at"}
    data = {k: v for k, v in data.items() if k in allowed}
    if not data:
        raise HTTPException(400, "no valid fields to update")

    sets = ", ".join(f"{k} = ?" for k in data)
    values = list(data.values()) + [task_id]
    with get_conn() as conn:
        cur = conn.execute(f"UPDATE tasks SET {sets} WHERE id = ?", values)
        if cur.rowcount == 0:
            raise HTTPException(404, "task not found")
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _row_to_task(row)


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int):
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "task not found")
