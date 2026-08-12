from __future__ import annotations

from pydantic import BaseModel
from typing import Optional


class TaskCreate(BaseModel):
    title: str
    planned_minutes: int = 25
    sort_order: int = 0


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    planned_minutes: Optional[int] = None
    status: Optional[str] = None
    sort_order: Optional[int] = None


class TaskOut(BaseModel):
    id: int
    title: str
    planned_minutes: int
    status: str
    sort_order: int
    created_date: str
    focus_seconds: int
    completed_at: Optional[str] = None
