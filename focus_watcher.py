#!/usr/bin/env python3
"""
🔄 Focus Watcher — auto-trigger Focus Blocker when macOS Focus Mode changes
=============================================================================
A lightweight background daemon that monitors macOS system Focus Mode status
and automatically blocks / unblocks distracting websites when focus changes.

Runs as a LaunchAgent (see install instructions below).

Detection methods (tried in order, first successful result wins):
  1. Compiled Swift helper            (macOS 26+ Tahoe — most reliable)
  2. Shortcuts Events via osascript  (macOS 12–15)
  3. ncprefs.plist polling           (fallback)
  4. notifyutil state keys           (last resort)

Usage:
  python focus_watcher.py           Run in foreground (for testing)
  python focus_watcher.py --install  Install as LaunchAgent
  python focus_watcher.py --uninstall  Remove LaunchAgent
"""

from __future__ import annotations

import os
import sys
import time
import json
import subprocess
import plistlib
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
BLOCKER_SCRIPT = SCRIPT_DIR / "focus_blocker.py"
CONFIG_DIR = SCRIPT_DIR / "config"
STATE_FILE = CONFIG_DIR / "watcher_state.json"
LOG_FILE = CONFIG_DIR / "watcher.log"
PLIST_NAME = "com.focusblocker.watcher.plist"
PLIST_DEST = Path.home() / "Library/LaunchAgents" / PLIST_NAME

POLL_INTERVAL = 3  # seconds between checks
DEBOUNCE = 2        # consecutive reads required before acting

# ── Logging ────────────────────────────────────────────────

def _log(msg: str) -> None:
    """Append a timestamped line to the log file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass
    print(line)  # also echo to stdout when running in foreground


# ── Focus detection ────────────────────────────────────────

def _get_focus_via_shortcuts_events() -> tuple[bool, str]:
    """Query current focus mode via Shortcuts Events (macOS 12–15).

    Returns (is_active, focus_name).  This API was removed in
    macOS 26 Tahoe.
    """
    scripts = [
        # macOS 13+ syntax
        'tell application "Shortcuts Events" to name of current focus',
        # Alternative
        'tell application "Shortcuts Events" to get current focus',
    ]
    for script in scripts:
        try:
            r = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=4,
            )
            name = r.stdout.strip()
            if r.returncode == 0 and name:
                return True, name
        except Exception:
            continue
    return False, ""


def _get_focus_via_ncprefs() -> tuple[bool, str]:
    """Check ``com.apple.ncprefs.plist`` for DnD/Focus enabled flag.

    This is less reliable — the plist structure varies across macOS
    versions and may not reflect instantaneous state.
    """
    pref = Path.home() / "Library/Preferences/com.apple.ncprefs.plist"
    if not pref.exists():
        return False, ""
    try:
        with open(pref, "rb") as f:
            data = plistlib.load(f)
    except Exception:
        return False, ""

    dnd = data.get("dnd_prefs")
    if isinstance(dnd, bytes):
        try:
            dnd = plistlib.loads(dnd)
        except Exception:
            return False, ""
    if isinstance(dnd, dict):
        # macOS 12–15: userPref.enabled indicates active DnD/Focus
        if dnd.get("userPref", {}).get("enabled"):
            return True, "Focus"
        # NOTE: dndMirrored means "Share Across Devices" is ENABLED,
        # not that a focus mode is currently active.  Do NOT check it.
    return False, ""


def is_focus_active() -> tuple[bool, str]:
    """Return ``(is_active, focus_mode_name)``.

    Tries available detection strategies in order of reliability.
    *focus_mode_name* is an empty string when no focus mode is active.

    Note: on macOS 26+ Tahoe, programmatic Focus detection is limited.
    Use Shortcuts Automation for reliable Focus-based triggering instead.
    """
    # Method 1: Shortcuts Events (macOS 12–15)
    active, name = _get_focus_via_shortcuts_events()
    if name:
        return active, name

    # Method 2: ncprefs plist (fallback)
    active, name = _get_focus_via_ncprefs()
    if name:
        return active, name

    return False, ""


# ── Actions ────────────────────────────────────────────────

def _notify(title: str, message: str) -> None:
    """Post a macOS user notification."""
    try:
        subprocess.run(
            [
                "osascript", "-e",
                f'display notification "{message}" '
                f'with title "{title}" '
                f'sound name "Glass"',
            ],
            capture_output=True, timeout=3,
        )
    except Exception:
        pass


def _run_blocker(*args: str) -> bool:
    """Run ``focus_blocker.py`` with elevated privileges via sudo.

    Uses ``sudo -n`` (non-interactive) — requires passwordless sudo
    to be configured for the blocker script.  Returns True on success.
    """
    try:
        r = subprocess.run(
            ["sudo", "-n", sys.executable, str(BLOCKER_SCRIPT), *args],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            stderr = r.stderr.strip()
            if "password is required" in stderr.lower() or "a terminal is required" in stderr.lower():
                _log(
                    "  ❌ Passwordless sudo is NOT configured.\n"
                    "     Run:  sudo visudo\n"
                    f'     Add:   {os.environ.get("USER", "YOUR_USERNAME")} ALL=(ALL) NOPASSWD: {sys.executable} {BLOCKER_SCRIPT} *'
                )
            elif stderr:
                _log(f"  blocker {' '.join(args)} stderr: {stderr[:300]}")
            return False
        return True
    except Exception as exc:
        _log(f"  blocker {' '.join(args)} exception: {exc}")
        return False


# ── State machine ──────────────────────────────────────────

def _load_state() -> bool:
    """Return the last known focus-active state (persisted to disk)."""
    try:
        return json.loads(STATE_FILE.read_text())["was_active"]
    except Exception:
        return False


def _save_state(active: bool) -> None:
    """Persist the current focus-active state."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"was_active": active}))


# ── Main loop ──────────────────────────────────────────────

def run_forever() -> None:
    """Blocking main loop — poll focus status, act on transitions."""
    _log("Focus Watcher started")
    _log(f"  blocker script : {BLOCKER_SCRIPT}")
    _log(f"  poll interval  : {POLL_INTERVAL}s")
    _log(f"  state file     : {STATE_FILE}")

    # On startup, check and align
    active, name = is_focus_active()
    was_active = _load_state()
    _log(f"  initial state: focus={'ON' if active else 'OFF'} "
         f"({name or 'unknown'}), "
         f"remembered={'ON' if was_active else 'OFF'}")

    # If focus is ON but we didn't remember it (e.g. watcher was restarted),
    # or vice versa, align the system
    should_be_blocked = _has_block_entries()

    if active and not should_be_blocked:
        _log("  → focus active but not blocked — blocking now")
        _run_blocker("--acquire", "watcher")
        _notify("🧘 Focus Mode: ON", f"Sites blocked for {name}" if name else "Sites blocked")
    elif not active and should_be_blocked:
        _log("  → focus inactive but still blocked — restoring now")
        _run_blocker("--release", "watcher")
        _notify("🌐 Focus Mode: OFF", "Sites unblocked")

    _save_state(active)

    consecutive = 0

    while True:
        time.sleep(POLL_INTERVAL)

        try:
            active, name = is_focus_active()
        except Exception as exc:
            _log(f"  detection error: {exc}")
            continue

        was_active = _load_state()

        if active == was_active:
            consecutive = 0
            continue

        # State change candidate — debounce
        consecutive += 1
        if consecutive < DEBOUNCE:
            continue

        consecutive = 0

        # Act on the transition
        if active and not was_active:
            _log(f"  🔒 Focus ON  ({name or 'unknown'}) → blocking")
            ok = _run_blocker("--acquire", "watcher")
            if ok:
                _notify("🧘 Focus Mode: ON",
                        f"Sites blocked for '{name}'" if name else "Sites blocked")
            _save_state(True)

        elif not active and was_active:
            _log(f"  🌐 Focus OFF → restoring")
            ok = _run_blocker("--release", "watcher")
            if ok:
                _notify("🌐 Focus Mode: OFF", "Sites unblocked — happy browsing!")
            _save_state(False)


def _has_block_entries() -> bool:
    """Check if hosts file currently has our block entries.  Tries multiple
    strategies to read the hosts file (may fail without sudo on some systems)."""
    import platform
    hosts = Path(
        r"C:\Windows\System32\drivers\etc\hosts"
        if platform.system() == "Windows"
        else "/etc/hosts"
    )
    try:
        return "# >>> FOCUS_BLOCKER_START" in hosts.read_text()
    except Exception:
        return False


# ── Install / uninstall ────────────────────────────────────

_LAUNCH_AGENT_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.focusblocker.watcher</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python}</string>
        <string>{script}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log}</string>
    <key>StandardErrorPath</key>
    <string>{log}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:{home}/Library/Python/{pyver}/bin</string>
    </dict>
</dict>
</plist>"""


def install() -> None:
    """Write the LaunchAgent plist and load it."""
    pyver = f"{sys.version_info.major}.{sys.version_info.minor}"
    plist_content = _LAUNCH_AGENT_PLIST.format(
        python=sys.executable,
        script=str(Path(__file__).resolve()),
        log=str(LOG_FILE),
        home=str(Path.home()),
        pyver=pyver,
    )

    PLIST_DEST.parent.mkdir(parents=True, exist_ok=True)
    PLIST_DEST.write_text(plist_content)
    print(f"✅ LaunchAgent written → {PLIST_DEST}")

    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{PLIST_NAME}"],
                   capture_output=True)  # ignore errors (not loaded yet)
    subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(PLIST_DEST)],
                   check=True)
    print(f"✅ LaunchAgent loaded — watcher will start on next login (or now)")


def uninstall() -> None:
    """Unload and remove the LaunchAgent."""
    subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}/{PLIST_NAME}"],
                   capture_output=True)
    if PLIST_DEST.exists():
        PLIST_DEST.unlink()
        print(f"🗑️  LaunchAgent removed → {PLIST_DEST}")
    else:
        print("ℹ️  LaunchAgent was not installed.")


# ── Entry point ────────────────────────────────────────────

def main() -> None:
    if "--install" in sys.argv:
        install()
    elif "--uninstall" in sys.argv:
        uninstall()
    else:
        # Foreground run (for testing / debugging)
        print("🔄 Focus Watcher running in foreground (Ctrl+C to stop)")
        print(f"   Log: {LOG_FILE}")
        print()
        run_forever()


if __name__ == "__main__":
    main()
