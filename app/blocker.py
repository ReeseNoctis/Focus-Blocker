"""Thin wrapper around focus_blocker.py's --acquire/--release, via sudo -n."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

BLOCKER_SCRIPT = Path(__file__).resolve().parent.parent / "focus_blocker.py"

# sudo matches sudoers entries by the literal path you pass it (it does NOT
# resolve symlinks), so resolve sys.executable to its real path to match the
# NOPASSWD entry for the Homebrew Cellar python.
_PYTHON_REAL = os.path.realpath(sys.executable)


def _run(*args: str) -> tuple[bool, str]:
    try:
        r = subprocess.run(
            ["sudo", "-n", _PYTHON_REAL, str(BLOCKER_SCRIPT), *args],
            capture_output=True, text=True, timeout=30,
        )
        return r.returncode == 0, r.stderr.strip()
    except Exception as exc:
        return False, str(exc)


def acquire(owner: str) -> tuple[bool, str]:
    return _run("--acquire", owner)


def release(owner: str) -> tuple[bool, str]:
    return _run("--release", owner)
