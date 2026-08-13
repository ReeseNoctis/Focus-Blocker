"""In-memory authoritative timer for focus sessions."""

from __future__ import annotations

import threading
import time


class SessionManager:
    def __init__(self) -> None:
        self._current: dict | None = None
        self._lock = threading.Lock()

    def start(self, task_id: int | None, minutes: int) -> dict:
        with self._lock:
            if self._current is not None:
                raise RuntimeError("a focus session is already running")
            total = max(1, minutes) * 60
            self._current = {
                "task_id": task_id,
                "total_seconds": total,
                "started_at": time.time(),
            }
            return dict(self._current)

    def stop(self, completed: bool = False) -> dict | None:
        with self._lock:
            if self._current is None:
                return None
            s = self._current
            elapsed = int(time.time() - s["started_at"])
            self._current = None
            return {
                "task_id": s["task_id"],
                "duration_seconds": elapsed,
                "completed": completed,
                "started_at": s["started_at"],
            }

    def current(self) -> dict | None:
        if self._current is None:
            return None
        s = self._current
        elapsed = time.time() - s["started_at"]
        remaining = max(0, s["total_seconds"] - elapsed)
        return {
            "active": True,
            "task_id": s["task_id"],
            "total_seconds": s["total_seconds"],
            "elapsed": int(elapsed),
            "remaining": int(remaining),
        }

    def expire_if_done(self):
        """If a session has elapsed past its total, stop it as completed and
        return the result dict; otherwise return None."""
        if self._current is None:
            return None
        s = self._current
        if int(time.time() - s["started_at"]) >= s["total_seconds"]:
            return self.stop(completed=True)
        return None

    def state(self) -> dict:
        cur = self.current()
        if cur is None:
            return {"active": False, "task_id": None,
                    "total_seconds": 0, "elapsed": 0, "remaining": 0}
        return cur


session_manager = SessionManager()
