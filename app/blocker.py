"""Thin wrapper around focus_blocker.py's --acquire/--release, via sudo -n."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BLOCKER_SCRIPT = Path(__file__).resolve().parent.parent / "focus_blocker.py"


def _run(*args: str) -> tuple[bool, str]:
    try:
        r = subprocess.run(
            ["sudo", "-n", sys.executable, str(BLOCKER_SCRIPT), *args],
            capture_output=True, text=True, timeout=30,
        )
        return r.returncode == 0, r.stderr.strip()
    except Exception as exc:
        return False, str(exc)


def acquire(owner: str) -> tuple[bool, str]:
    return _run("--acquire", owner)


def release(owner: str) -> tuple[bool, str]:
    return _run("--release", owner)
