#!/usr/bin/env python3
"""
🧘 Focus Blocker — 专注学习时从物理层面屏蔽娱乐网站
======================================================
A cross-platform Python tool that modifies the system hosts file
to block distracting websites during timed focus sessions.

Usage:
  python focus_blocker.py              Start a focus session
  python focus_blocker.py manage       Interactive TUI site manager
  python focus_blocker.py list         Show blocked sites

Requirements: Python 3.7+  •  pip install rich
"""

from __future__ import annotations

import json
import os
import stat as stat_module
import sys
import shlex
import shutil
import time
import signal
import platform
import ctypes
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

# ============================================================
# Default blocklist — used when creating a fresh config file
# ============================================================

DEFAULT_SITES: list[str] = [
    # --- Video & Streaming ---
    "www.bilibili.com",
    "bilibili.com",
    "www.douyin.com",
    "douyin.com",
    "v.qq.com",
    "www.iqiyi.com",
    "iqiyi.com",
    "www.youku.com",
    "youku.com",
    "www.youtube.com",
    "youtube.com",
    "www.twitch.tv",
    "twitch.tv",
    # --- Social Media ---
    "www.weibo.com",
    "weibo.com",
    "www.zhihu.com",
    "zhihu.com",
    "www.douban.com",
    "douban.com",
    "www.xiaohongshu.com",
    "xiaohongshu.com",
    # --- Short Video ---
    "www.kuaishou.com",
    "kuaishou.com",
]

REDIRECT_IP = "127.0.0.1"

# Marker lines that bracket our entries — do not edit manually
_MARKER_START = "# >>> FOCUS_BLOCKER_START (auto-generated, do not edit) >>>"
_MARKER_END = "# <<< FOCUS_BLOCKER_END <<<"

# ============================================================
# Platform detection
# ============================================================

_SYSTEM = platform.system()
IS_WINDOWS = _SYSTEM == "Windows"
IS_MACOS = _SYSTEM == "Darwin"
IS_LINUX = _SYSTEM == "Linux"

HOSTS_PATH = Path(
    r"C:\Windows\System32\drivers\etc\hosts" if IS_WINDOWS else "/etc/hosts"
)
_BACKUP_PATH = Path(str(HOSTS_PATH) + ".focus_blocker_backup")

# ============================================================
# Config file — <script_dir>/config/sites.json
# ============================================================

_CONFIG_DIR = Path(__file__).resolve().parent / "config"
_CONFIG_FILE = _CONFIG_DIR / "sites.json"
_STATE_FILE = _CONFIG_DIR / "session_state.json"
_LOCK_FILE = _CONFIG_DIR / "block_lock.json"

# Encouraging quotes for session completion
_QUOTES = [
    "The only way to do great work is to love what you do. — Steve Jobs",
    "Focus is the key that unlocks extraordinary results.",
    "Small daily improvements lead to stunning long-term results.",
    "Your future is created by what you do today, not tomorrow.",
    "Discipline is choosing between what you want now and what you want most.",
    "The successful warrior is the average man, with laser-like focus.",
    "It's not about having time, it's about making time.",
    "Deep work is the superpower of the 21st century.",
    "You don't have to be great to start, but you have to start to be great.",
    "Stay focused, stay humble, stay hungry.",
    "What you focus on grows. Focus on what matters.",
    "The best investment you can make is in yourself.",
    "Every hour of focused work is a brick in your cathedral.",
    "Motivation gets you started. Discipline keeps you going.",
    "The difference between ordinary and extraordinary is that little extra.",
]


class _Config:
    """Read / write the persistent blocklist config file."""

    def __init__(self) -> None:
        self._ensure_exists()

    # ---- helpers ----

    def _ensure_exists(self) -> None:
        if not _CONFIG_DIR.exists():
            _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if not _CONFIG_FILE.exists():
            self._write_default()

    def _write_default(self) -> None:
        """Write the built-in default list on first run."""
        with open(_CONFIG_FILE, "w", encoding="utf-8") as fh:
            json.dump({"sites": DEFAULT_SITES}, fh, indent=2, ensure_ascii=False)

    # ---- public API ----

    def load(self) -> list[str]:
        """Return the current blocklist (deduplicated, sorted)."""
        try:
            with open(_CONFIG_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            self._write_default()
            return list(DEFAULT_SITES)

        sites: list[str] = data.get("sites", [])
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for s in sites:
            s = s.strip().lower()
            if s and s not in seen:
                seen.add(s)
                unique.append(s)
        return unique

    def save(self, sites: list[str]) -> None:
        """Persist a site list."""
        with open(_CONFIG_FILE, "w", encoding="utf-8") as fh:
            json.dump({"sites": sites}, fh, indent=2, ensure_ascii=False)

    def add(self, domain: str) -> bool:
        """Add a domain.  Returns True if it was actually added."""
        sites = self.load()
        domain = domain.strip().lower()
        if not domain:
            return False
        if domain in sites:
            return False
        sites.append(domain)
        self.save(sites)
        return True

    def remove(self, index: int) -> str | None:
        """Remove a domain by its 0-based index.  Returns the removed domain."""
        sites = self.load()
        if 0 <= index < len(sites):
            removed = sites.pop(index)
            self.save(sites)
            return removed
        return None

    def remove_by_name(self, domain: str) -> bool:
        """Remove a domain by name (case-insensitive)."""
        sites = self.load()
        domain = domain.strip().lower()
        try:
            sites.remove(domain)
            self.save(sites)
            return True
        except ValueError:
            return False


# Singleton — cheap to re-read since the file is tiny
def _get_sites() -> list[str]:
    return _Config().load()


# ============================================================
# Block lock — shared coordination with focus_watcher.py
# ============================================================

def _load_lock() -> dict[str, bool]:
    """Return the shared block lock.  Repair/rebuild on corrupt or missing."""
    default = {"watcher": False, "assistant": False}
    try:
        data = json.loads(_LOCK_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default
    if not isinstance(data, dict):
        return default
    return {
        "watcher": bool(data.get("watcher", False)),
        "assistant": bool(data.get("assistant", False)),
    }


def _save_lock(lock: dict[str, bool]) -> None:
    """Atomically write the lock file (temp file + os.replace)."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _LOCK_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(lock), encoding="utf-8")
    os.replace(tmp, _LOCK_FILE)


def acquire_lock(owner: str) -> None:
    """Mark *owner* as holding the block; block sites if not already blocked."""
    lock = _load_lock()
    if lock.get(owner):
        return
    lock[owner] = True
    _save_lock(lock)

    if _has_block_entries():
        print(f"ℹ️  Sites already blocked ({owner} acquired).")
        return

    sites = _get_sites()
    if not sites:
        print("❌ Blocklist is empty.")
        sys.exit(1)

    backup_hosts()
    block_sites(sites)
    flush_dns()
    print(f"🔒 Sites blocked (acquired by {owner}).")


def release_lock(owner: str) -> None:
    """Release *owner*'s hold; restore only when no owner remains."""
    lock = _load_lock()
    lock[owner] = False
    _save_lock(lock)

    if any(lock.values()):
        remaining = [k for k, v in lock.items() if v]
        print(f"ℹ️  Still held by {remaining} — keeping blocked.")
        return

    if not _has_block_entries():
        return

    if restore_hosts():
        flush_dns()
        print("🌐 All sites unblocked.")
    else:
        _remove_immutable_flag()
        _strip_block_entries()
        _restore_immutable_flag()
        flush_dns()
        print("🌐 Sites unblocked (recovered without backup).")


# ============================================================
# Privilege helpers
# ============================================================

def is_admin() -> bool:
    """Return True if the current process has root / administrator rights."""
    if IS_WINDOWS:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        return os.geteuid() == 0


def _has_passwordless_sudo() -> bool:
    """Check whether ``sudo -n`` works (passwordless sudo configured)."""
    import subprocess
    try:
        r = subprocess.run(
            ["sudo", "-n", "true"],
            capture_output=True, timeout=5,
        )
        return r.returncode == 0
    except Exception:
        return False


def _is_interactive() -> bool:
    """Return True if we appear to be running in an interactive terminal."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def elevate(extra_args: list[str] | None = None) -> None:
    """Re-execute this script with elevated privileges, then exit.

    On Windows this triggers the UAC consent dialog.
    On macOS / Linux this runs ``sudo``.

    If *extra_args* is not None, those args replace ``sys.argv[1:]``
    (useful when crossing from ``manage`` → focus mode).
    """
    if extra_args is not None:
        args = [sys.executable] + extra_args
    else:
        args = [sys.executable] + sys.argv[1:]

    if IS_WINDOWS:
        params = " ".join(f'"{a}"' if " " in a else a for a in args)
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, None, 1,
        )
        if ret <= 32:
            print(f"❌ Failed to request administrator privileges (code {ret}).")
            sys.exit(1)
        sys.exit(0)
    else:
        # Check if passwordless sudo is available (needed for background use)
        if not _is_interactive() and not _has_passwordless_sudo():
            print(
                "❌ Cannot prompt for sudo password in a non-interactive context.\n"
                "\n"
                "   This script was called from a background process (Shortcuts,\n"
                "   LaunchAgent, cron, etc.) where it can't ask for your password.\n"
                "\n"
                "   To fix this, configure passwordless sudo for this script:\n"
                "\n"
                "     sudo visudo\n"
                "\n"
                "   And add this line (adjust the path):\n"
                "\n"
                f'     {os.environ.get("USER", "YOUR_USERNAME")} ALL=(ALL) NOPASSWD: {sys.executable} {Path(__file__).resolve()} *\n'
                "\n"
                "   Then try again.",
                file=sys.stderr,
            )
            sys.exit(1)

        print("🔐 Root privileges are needed to modify /etc/hosts.")
        print("    Requesting sudo …\n")
        try:
            os.execvp("sudo", ["sudo"] + args)
        except Exception as exc:
            print(f"❌ sudo failed: {exc}")
            sys.exit(1)


# ============================================================
# Hosts file helpers
# ============================================================

def _read_hosts() -> str:
    with open(HOSTS_PATH, "r", encoding="utf-8") as fh:
        return fh.read()


def _write_hosts(content: str) -> None:
    with open(HOSTS_PATH, "w", encoding="utf-8") as fh:
        fh.write(content)


def _has_block_entries() -> bool:
    try:
        return _MARKER_START in _read_hosts()
    except FileNotFoundError:
        return False


def _strip_block_entries() -> None:
    """Remove our marker-bracketed block section from the hosts file."""
    content = _read_hosts()
    if _MARKER_START not in content:
        return
    lines: list[str] = []
    skip = False
    for line in content.splitlines(keepends=True):
        if _MARKER_START in line:
            skip = True
            continue
        if _MARKER_END in line:
            skip = False
            continue
        if not skip:
            lines.append(line)
    _write_hosts("".join(lines))


def _path_flags(path: Path) -> int:
    """Return the BSD file flags for *path* (0 if not available)."""
    try:
        return path.stat().st_flags
    except Exception:
        return 0


def _remove_immutable_flag_path(path: Path) -> bool:
    """Remove the system/user immutable flag from *path* so it can be modified."""
    flags = _path_flags(path)
    if not (flags & (stat_module.UF_IMMUTABLE | stat_module.SF_IMMUTABLE)):
        return True

    ret = os.system(f"chflags noschg {shlex.quote(str(path))} 2>/dev/null")
    if ret != 0:
        ret = os.system(f"chflags nouchg {shlex.quote(str(path))} 2>/dev/null")

    new_flags = _path_flags(path)
    return not bool(new_flags & (stat_module.UF_IMMUTABLE | stat_module.SF_IMMUTABLE))


def _restore_immutable_flag_path(path: Path) -> None:
    """Put the system immutable flag back on a path."""
    os.system(f"chflags schg {shlex.quote(str(path))} 2>/dev/null")


def _hosts_has_immutable_flag() -> bool:
    """Check whether the hosts file has the schg / uchg immutable flag set."""
    flags = _path_flags(HOSTS_PATH)
    return bool(flags & (stat_module.UF_IMMUTABLE | stat_module.SF_IMMUTABLE))


def _remove_immutable_flag() -> bool:
    """Remove the immutable flag from the hosts file so we can write to it."""
    return _remove_immutable_flag_path(HOSTS_PATH)


def _restore_immutable_flag() -> None:
    """Put the system immutable flag back on the hosts file (security)."""
    _restore_immutable_flag_path(HOSTS_PATH)


# ============================================================
# Public API — backup / block / restore
# ============================================================

def _delete_backup() -> None:
    """Delete the backup file, removing any immutable flag first."""
    if not _BACKUP_PATH.exists():
        return
    _remove_immutable_flag_path(_BACKUP_PATH)
    _BACKUP_PATH.unlink()


def backup_hosts() -> None:
    """Copy hosts → backup file.  Handles stale backups interactively
    when a TTY is available, or auto-overwrites in headless mode."""
    if _BACKUP_PATH.exists():
        if _is_interactive():
            print("⚠️  Found an existing backup file:")
            print(f"     {_BACKUP_PATH}")
            print("   This usually means a previous session crashed or was killed.\n")
            print("   [R] Restore that backup now  (undo old block)")
            print("   [O] Overwrite with a fresh backup")
            print("   [Q] Quit and do nothing")
            choice = input("   → ").strip().lower()

            if choice == "r":
                _remove_immutable_flag()
                _remove_immutable_flag_path(_BACKUP_PATH)
                shutil.copy2(_BACKUP_PATH, HOSTS_PATH)
                _restore_immutable_flag()
                _delete_backup()
                print("✅ Hosts restored. Creating a fresh backup …")
                backup_hosts()
                return
            if choice == "o":
                _delete_backup()
                print("   Old backup discarded.")
            else:
                print("👋 Exiting.")
                sys.exit(0)
        else:
            # Headless mode — auto-overwrite stale backup
            _delete_backup()
            print("   Old backup auto-discarded (headless mode).")

    shutil.copy2(HOSTS_PATH, _BACKUP_PATH)
    print(f"✅ Backup saved → {_BACKUP_PATH}")


def block_sites(sites: list[str]) -> int:
    """Insert *sites* into the hosts file.  Idempotent — strips any
    previous block section first."""
    # Remove immutable flag so we can write (macOS 26+ sets schg on /etc/hosts)
    _remove_immutable_flag()

    content = _read_hosts()

    # Remove any pre-existing block section
    if _MARKER_START in content:
        lines: list[str] = []
        skip = False
        for line in content.splitlines(keepends=True):
            if _MARKER_START in line:
                skip = True
                continue
            if _MARKER_END in line:
                skip = False
                continue
            if not skip:
                lines.append(line)
        content = "".join(lines)

    content = content.rstrip("\n") + "\n\n"

    block = [_MARKER_START + "\n"]
    for domain in sites:
        block.append(f"{REDIRECT_IP}  {domain}\n")
        block.append(f"::1  {domain}\n")  # IPv6 loopback
    block.append(_MARKER_END + "\n")

    content += "".join(block)
    _write_hosts(content)
    return len(sites)


def restore_hosts() -> bool:
    """Restore hosts from the backup file.  Returns True on success."""
    if not _BACKUP_PATH.exists():
        print("ℹ️  No backup found — nothing to restore.")
        return False

    _remove_immutable_flag()
    _remove_immutable_flag_path(_BACKUP_PATH)
    shutil.copy2(_BACKUP_PATH, HOSTS_PATH)
    _restore_immutable_flag()
    _delete_backup()
    print("✅ Hosts file restored from backup.")
    return True


def flush_dns() -> None:
    """Best-effort DNS cache flush."""
    try:
        if IS_MACOS:
            os.system("dscacheutil -flushcache 2>/dev/null")
            os.system("killall -HUP mDNSResponder 2>/dev/null")
        elif IS_LINUX:
            os.system("systemctl restart systemd-resolved 2>/dev/null || true")
        elif IS_WINDOWS:
            os.system("ipconfig /flushdns >nul 2>&1")
    except Exception:
        pass


# ============================================================
# Signal handling
# ============================================================

_interrupted = False


def _on_signal(_signum: int, _frame: object) -> None:
    global _interrupted
    _interrupted = True


def _install_signal_handlers() -> None:
    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)


# ============================================================
# Rich helpers
# ============================================================

def _ensure_rich() -> None:
    try:
        import rich  # noqa: F401
    except ImportError:
        print("╔══════════════════════════════════════════════╗")
        print("║  ⚠️  This script needs the 'rich' library.    ║")
        print("║                                              ║")
        print("║     pip install rich                         ║")
        print("║                                              ║")
        print("║  Install it and try again!                   ║")
        print("╚══════════════════════════════════════════════╝")
        sys.exit(1)


def _fmt_time(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


# ============================================================
# Subcommand: list
# ============================================================

def cmd_list() -> None:
    """Print the current blocklist to the terminal."""
    _ensure_rich()
    from rich.console import Console
    from rich.table import Table
    from rich import box

    console = Console()
    sites = _get_sites()

    table = Table(
        title="🚫  Focus Blocker — Blocked Sites",
        title_style="bold cyan",
        box=box.ROUNDED,
        border_style="cyan",
        show_header=True,
        header_style="bold",
    )
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Domain")

    for i, site in enumerate(sites, 1):
        table.add_row(str(i), site)

    console.print()
    console.print(table)
    console.print(f"\n  [dim]{len(sites)} site(s) in blocklist[/]\n")


# ============================================================
# Subcommand: manage  (interactive TUI)
# ============================================================

def cmd_manage() -> None:
    """Open the interactive TUI for managing the blocklist."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.prompt import Prompt
    from rich.text import Text
    from rich.align import Align
    from rich import box

    console = Console()
    cfg = _Config()

    def _render_table(sites: list[str]) -> Table:
        blocked_now = _has_block_entries() if is_admin() else None

        table = Table(
            box=box.ROUNDED,
            border_style="cyan",
            show_header=True,
            header_style="bold cyan",
            expand=True,
        )
        table.add_column("#", style="dim", width=4, justify="right")
        table.add_column("Domain", style="white")
        if blocked_now is not None:
            table.add_column("Status", width=10)

        for i, site in enumerate(sites, 1):
            row = [str(i), site]
            if blocked_now is not None:
                row.append(
                    "[red]● blocked[/]" if blocked_now else "[green]○ inactive[/]"
                )
            table.add_row(*row)

        total = len(sites)
        caption = Text(f"{total} site(s) total", style="dim")
        table.caption = caption
        return table

    def _action_bar() -> None:
        console.print()
        bar = Text.assemble(
            (" [A]", "bold green"), ("dd site   ", "dim"),
            (" [D]", "bold yellow"), ("elete site   ", "dim"),
            (" [S]", "bold cyan"), ("tart focus   ", "dim"),
            (" [Q]", "bold red"), ("uit", "dim"),
        )
        console.print(Align.center(bar))
        console.print()

    while True:
        sites = cfg.load()

        console.clear()
        console.print()
        console.print(
            Panel(
                _render_table(sites),
                title="🧘  Focus Blocker — Site Manager",
                title_align="left",
                border_style="cyan",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
        _action_bar()

        try:
            action = Prompt.ask(
                "  [bold]Action[/]",
                choices=["a", "d", "s", "q"],
                default="s",
                show_choices=False,
            )
        except (KeyboardInterrupt, EOFError):
            console.print("\n👋 Bye!\n")
            sys.exit(0)

        if action == "a":
            # ---- add ----
            console.print()
            domain = Prompt.ask(
                "  [bold green]Domain to block[/]",
                default="",
            ).strip().lower()
            if domain:
                if cfg.add(domain):
                    console.print(f"  ✅ [green]{domain}[/] added.\n")
                else:
                    console.print(f"  ⚠️  [yellow]{domain}[/] is already in the list.\n")
                time.sleep(0.6)
            else:
                console.print("  ⏭️  Skipped.\n")
                time.sleep(0.4)

        elif action == "d":
            # ---- delete ----
            if not sites:
                console.print("  📭 List is empty — nothing to delete.\n")
                time.sleep(0.8)
                continue

            console.print()
            target = Prompt.ask(
                "  [bold yellow]Number or domain to remove[/]",
                default="",
            ).strip()
            if not target:
                console.print("  ⏭️  Skipped.\n")
                time.sleep(0.4)
                continue

            # Try as index first, then as domain name
            try:
                idx = int(target) - 1
                removed = cfg.remove(idx)
                if removed:
                    console.print(f"  🗑️  [red]{removed}[/] removed.\n")
                else:
                    console.print(f"  ❌ Invalid number: {target}\n")
            except ValueError:
                if cfg.remove_by_name(target):
                    console.print(f"  🗑️  [red]{target}[/] removed.\n")
                else:
                    console.print(f"  ❌ [yellow]{target}[/] not found in list.\n")
            time.sleep(0.6)

        elif action == "s":
            # ---- start focus ----
            console.print()
            console.print("  🚀 Starting focus mode …\n")
            time.sleep(0.3)
            break  # exit the manage loop → fall through to focus

        elif action == "q":
            console.print("\n👋 Bye!\n")
            sys.exit(0)

    # If we broke out via "s", launch the focus flow
    _start_focus_flow()


# ============================================================
# Focus timer UI
# ============================================================

def _prompt_duration() -> int:
    """Ask how many minutes, return the number."""
    from rich.console import Console
    from rich.prompt import IntPrompt

    console = Console()
    console.print()
    console.print(
        "  🧘 How many minutes would you like to focus?",
        style="bold cyan",
    )
    console.print("     (e.g. 25 for a Pomodoro, 90 for deep work)", style="dim")
    console.print()
    minutes = IntPrompt.ask("  [bold yellow]Minutes[/]", default=25)
    return max(1, min(minutes, 1440))


def _run_countdown(total_minutes: int, sites: list[str]) -> bool:
    """Rich countdown timer.  Returns True if completed, False if interrupted."""
    from rich.console import Console, Group
    from rich.live import Live
    from rich.panel import Panel
    from rich.progress import Progress, BarColumn, TextColumn
    from rich.text import Text
    from rich.align import Align
    from rich import box

    console = Console()
    total_seconds = total_minutes * 60

    _install_signal_handlers()

    start = time.monotonic()
    completed = False

    def _build(elapsed: float) -> Panel:
        remaining = max(0, int(total_seconds - elapsed))
        pct = min(100.0, (elapsed / total_seconds) * 100) if total_seconds else 100.0

        ratio = remaining / total_seconds if total_seconds else 0
        if ratio > 0.5:
            accent, emoji, label = "green", "🧘", "Deep Focus"
        elif ratio > 0.15:
            accent, emoji, label = "yellow", "🔥", "Keep Going"
        else:
            accent, emoji, label = "red", "🏁", "Almost There"

        progress = Progress(
            TextColumn(""),
            BarColumn(
                bar_width=42,
                style=f"dim {accent}",
                complete_style=accent,
                finished_style="bright_green",
            ),
            TextColumn("[bold]{task.percentage:>4.0f}%"),
            console=console,
            expand=False,
        )
        progress.add_task("", total=100, completed=pct)

        preview = ", ".join(sites[:4])
        if len(sites) > 4:
            preview += f" … +{len(sites) - 4} more"

        inner = Group(
            Align.center(Text(f"{emoji}  {label}", style=f"bold {accent}")),
            Text(""),
            Align.center(Text(_fmt_time(remaining), style=f"bold {accent}")),
            Align.center(Text("remaining", style=f"dim {accent}")),
            Text(""),
            progress,
            Text(""),
            Align.center(Text(f"🚫  {preview}", style="dim")),
            Text(""),
            Align.center(
                Text("Press Ctrl+C to end focus mode early", style="dim italic")
            ),
        )

        return Panel(
            inner,
            title="🧘  Focus Mode",
            title_align="left",
            border_style=accent,
            box=box.ROUNDED,
            padding=(1, 2),
        )

    try:
        with Live(
            _build(0), console=console, refresh_per_second=8, transient=False,
        ) as live:
            while True:
                elapsed = time.monotonic() - start

                if _interrupted:
                    break
                if elapsed >= total_seconds:
                    completed = True
                    break

                live.update(_build(elapsed))
                time.sleep(0.125)
    except KeyboardInterrupt:
        pass

    if completed:
        import random
        duration_str = _fmt_time(total_seconds)
        quote = random.choice(_QUOTES)
        console.clear()
        console.print()
        console.print(
            Panel(
                Align.center(
                    Text(
                        f"🎉  Focus session complete!  🎉\n\n"
                        f"You were focused for {duration_str}.\n\n"
                        f"💬 {quote}",
                        style="bold green",
                        justify="center",
                    ),
                ),
                border_style="bright_green",
                box=box.ROUNDED,
                padding=(1, 2),
            )
        )
        console.print()

    return not _interrupted


# ============================================================
# Core focus flow (elevate → block → timer → restore)
# ============================================================

def _start_focus_flow() -> None:
    """The main focus-session pipeline.  Called by both ``cmd_manage``
    (after exiting the TUI) and directly from ``main``."""
    _ensure_rich()

    # 1. Ensure admin
    if not is_admin():
        # Pass no subcommand so the elevated process lands in focus mode
        elevate(extra_args=[])
        return  # unreachable

    # 2. Validate hosts file
    if not HOSTS_PATH.exists():
        print(f"❌ Hosts file not found at {HOSTS_PATH}")
        sys.exit(1)

    # 3. Clean up stale entries
    if _has_block_entries():
        from rich.console import Console
        c = Console()
        c.print()
        c.print(
            "⚠️  [bold yellow]Block entries already exist in the hosts file.[/]",
        )
        c.print("    This may be left over from a previous crashed session.")
        c.print()
        c.print("    [R] Restore hosts & start fresh")
        c.print("    [C] Continue (keep current block, just start timer)")
        c.print("    [Q] Quit")
        choice = input("    → ").strip().lower()
        if choice == "r":
            restore_hosts()
        elif choice == "c":
            pass
        else:
            print("👋 Exiting.")
            sys.exit(0)

    # 4. Load sites & block
    sites = _get_sites()
    if not sites:
        print("❌ Blocklist is empty.  Add sites first with: python focus_blocker.py manage")
        sys.exit(1)

    print()
    backup_hosts()
    count = block_sites(sites)
    flush_dns()
    _record_session_start()
    print(f"🔒 {count} websites blocked. DNS cache flushed.\n")

    # 5. Timer (wrapped in finally for guaranteed restore)
    try:
        minutes = _prompt_duration()
        _start_status_server(sites, minutes * 60)
        _run_countdown(minutes, sites)
    finally:
        _stop_status_server()
        print()
        restore_hosts()
        flush_dns()
        print("🌐 All sites unblocked. Happy browsing!\n")


# ============================================================
# CLI dispatch
# ============================================================

def _print_usage() -> None:
    print("Usage:")
    print("  python focus_blocker.py              Start a focus session")
    print("  python focus_blocker.py manage       Interactive TUI site manager")
    print("  python focus_blocker.py list         Show blocked sites")
    print("  python focus_blocker.py --block-only   Silent block (no timer)")
    print("  python focus_blocker.py --unblock-only Silent restore (no timer)")
    print("  python focus_blocker.py --acquire <watcher|assistant>   占住屏蔽锁")
    print("  python focus_blocker.py --release <watcher|assistant>   释放屏蔽锁")
    print("  python focus_blocker.py --help       Show this message")


def _silent_block() -> None:
    """Headless block — elevate, backup, block, notify, exit.  No timer."""
    if not is_admin():
        elevate(extra_args=["--block-only"])
        return

    if not HOSTS_PATH.exists():
        print(f"❌ Hosts file not found at {HOSTS_PATH}")
        sys.exit(1)

    sites = _get_sites()
    if not sites:
        print("❌ Blocklist is empty.")
        sys.exit(1)

    # Don't double-block
    if _has_block_entries():
        print("ℹ️  Sites already blocked.")
        _start_status_server(sites)  # ensure server is running
        sys.exit(0)

    backup_hosts()
    count = block_sites(sites)
    flush_dns()

    # Record session start for completion summary
    _record_session_start()

    # Start local status server
    _start_status_server(sites)

    msg = f"🔒 {count} sites blocked — stay focused!"
    print(f"  {msg}")
    _notify("Focus Blocker", msg)


def _silent_unblock() -> None:
    """Headless restore — restore hosts, flush DNS, notify, exit."""
    if not is_admin():
        elevate(extra_args=["--unblock-only"])
        return

    _stop_status_server()

    if not _BACKUP_PATH.exists():
        if _has_block_entries():
            _remove_immutable_flag()
            _strip_block_entries()
            _restore_immutable_flag()
            flush_dns()
            msg = "🌐 Sites unblocked (recovered without backup)."
            summary = _session_summary()
            print(f"  {msg}")
            if summary:
                print(f"\n  {summary}\n")
                _notify("Focus Blocker 🎉", summary)
            else:
                _notify("Focus Blocker", msg)
            sys.exit(0)
        else:
            print("  ℹ️  Sites are not currently blocked.")
            sys.exit(0)

    if restore_hosts():
        flush_dns()
        summary = _session_summary()
        if summary:
            print(f"\n  {summary}\n")
            _notify("Focus Blocker 🎉", summary)
        else:
            print("  🌐 All sites unblocked — happy browsing!")
            _notify("Focus Blocker", "All sites unblocked — happy browsing!")


def _cmd_acquire(owner: str) -> None:
    if not is_admin():
        elevate(extra_args=["--acquire", owner])
        return
    acquire_lock(owner)


def _cmd_release(owner: str) -> None:
    if not is_admin():
        elevate(extra_args=["--release", owner])
        return
    release_lock(owner)


def _notify(title: str, message: str) -> None:
    """Show a macOS notification via osascript (best-effort)."""
    if not IS_MACOS:
        return
    try:
        import subprocess
        subprocess.run([
            "osascript", "-e",
            f'display notification "{message}" with title "{title}" sound name "Glass"',
        ], capture_output=True, timeout=3)
    except Exception:
        pass  # notifications are non-critical


def _record_session_start() -> None:
    """Record the focus session start time to a state file."""
    import json
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps({"start": time.time()}))


def _session_summary() -> str | None:
    """Return a completion summary string (duration + quote), or None if no session found."""
    import json, random
    try:
        data = json.loads(_STATE_FILE.read_text())
        start = data.get("start")
    except Exception:
        return None

    if not start:
        return None

    elapsed = int(time.time() - start)
    _STATE_FILE.unlink(missing_ok=True)

    # Format duration
    if elapsed < 60:
        duration = f"{elapsed}s"
    elif elapsed < 3600:
        m, s = divmod(elapsed, 60)
        duration = f"{m}min {s}s"
    else:
        h, remainder = divmod(elapsed, 3600)
        m = remainder // 60
        duration = f"{h}h {m}min"

    quote = random.choice(_QUOTES)
    return f"🎉 Focus session complete! You were focused for {duration}.\n💬 {quote}"


def _open_config() -> None:
    """Open the config file in the user's default editor."""
    print(f"📝 Opening {_CONFIG_FILE} …")
    import subprocess
    subprocess.run(["open", str(_CONFIG_FILE)])


# ============================================================
# Local status server
# ============================================================

_SERVER_SCRIPT = Path(__file__).resolve().parent / "focus_server.py"


def _start_status_server(sites: list[str], total_seconds: int = 0) -> None:
    """Start the local HTTP status server (non-blocking, forked)."""
    if not _SERVER_SCRIPT.exists():
        return
    import subprocess
    try:
        subprocess.run(
            [sys.executable, str(_SERVER_SCRIPT), "start", str(total_seconds)],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        pass  # server is non-critical


def _stop_status_server() -> None:
    """Stop the local HTTP status server (delegates to focus_server.py stop)."""
    import subprocess
    try:
        subprocess.run(
            [sys.executable, str(_SERVER_SCRIPT), "stop"],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        pass  # server is non-critical


def main() -> None:
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
    else:
        cmd = "start"

    if cmd in ("--help", "-h", "help"):
        _print_usage()
    elif cmd == "manage":
        cmd_manage()
    elif cmd == "list":
        cmd_list()
    elif cmd in ("config", "--config", "--open-config"):
        _open_config()
    elif cmd == "start":
        _start_focus_flow()
    elif cmd == "--block-only":
        _silent_block()
    elif cmd in ("--acquire", "--release"):
        if len(sys.argv) < 3 or sys.argv[2] not in ("watcher", "assistant"):
            print("Usage: focus_blocker.py --acquire|--release <watcher|assistant>")
            sys.exit(1)
        owner = sys.argv[2]
        if cmd == "--acquire":
            _cmd_acquire(owner)
        else:
            _cmd_release(owner)
    elif cmd == "--unblock-only":
        _silent_unblock()
    else:
        print(f"Unknown command: {cmd}\n")
        _print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
