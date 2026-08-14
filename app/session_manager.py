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
                "accumulated": 0.0,   # active seconds before the current run
                "paused_at": None,    # time.time() when paused, else None
            }
            return dict(self._current)

    def _elapsed(self, s: dict) -> float:
        """Active (non-paused) seconds elapsed for session *s*."""
        if s["paused_at"] is not None:
            return s["accumulated"]
        return s["accumulated"] + (time.time() - s["started_at"])

    def pause(self) -> dict | None:
        with self._lock:
            s = self._current
            if s is None or s["paused_at"] is not None:
                return None
            # Freeze the active segment into accumulated, then mark paused.
            s["accumulated"] += time.time() - s["started_at"]
            s["paused_at"] = time.time()
            return dict(s)

    def resume(self) -> dict | None:
        with self._lock:
            s = self._current
            if s is None or s["paused_at"] is None:
                return None
            # Restart the active clock from the frozen remainder.
            s["started_at"] = time.time()
            s["paused_at"] = None
            return dict(s)

    def stop(self, completed: bool = False) -> dict | None:
        with self._lock:
            if self._current is None:
                return None
            s = self._current
            elapsed = int(self._elapsed(s))
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
        elapsed = self._elapsed(s)
        remaining = max(0, s["total_seconds"] - elapsed)
        return {
            "active": True,
            "paused": s["paused_at"] is not None,
            "task_id": s["task_id"],
            "total_seconds": s["total_seconds"],
            "elapsed": int(elapsed),
            "remaining": int(remaining),
        }

    def expire_if_done(self):
        """If a session has elapsed past its total, stop it as completed and
        return the result dict; otherwise return None.  A paused session is
        never auto-completed."""
        if self._current is None:
            return None
        if self._current["paused_at"] is not None:
            return None
        s = self._current
        if int(self._elapsed(s)) >= s["total_seconds"]:
            return self.stop(completed=True)
        return None

    def state(self) -> dict:
        cur = self.current()
        if cur is None:
            return {"active": False, "paused": False, "task_id": None,
                    "total_seconds": 0, "elapsed": 0, "remaining": 0}
        return cur


session_manager = SessionManager()
