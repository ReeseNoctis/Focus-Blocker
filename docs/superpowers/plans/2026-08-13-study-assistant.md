# 沉浸式学习助手 MVP 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把现有 Focus Blocker 升级为可规划每日任务、一键启动专注、计时结束自动完成的沉浸式学习助手（Web 界面）。

**Architecture:** Vue 3 前端通过 REST + WebSocket 与 FastAPI 后端通信；后端权威计时并持有会话状态机；后端通过 `sudo -n` 调用现有 `focus_blocker.py` 作为屏蔽引擎；屏蔽引擎新增 `--acquire`/`--release` 共享锁命令，与 macOS Focus 勿扰守护进程（`focus_watcher.py`）协调，避免互相覆盖。

**Tech Stack:** Vue 3 + Vite（前端）、FastAPI + uvicorn（后端）、SQLite（标准库 `sqlite3`）、Python 3.12（Homebrew）。

## Global Constraints

- **Python 版本**：后端与屏蔽引擎一律用 `/opt/homebrew/bin/python3.12`（**不用** `/usr/bin/python3`，那是 Xcode 自带的 3.9.6，太老）。
- **依赖上限**：后端只用 `fastapi`、`uvicorn[standard]`、`pydantic`（FastAPI 自带）、`pytest`、`httpx`（TestClient 依赖）。**不用** SQLAlchemy/ORM —— 直接标准库 `sqlite3`。**不用** `rich`（后端与 `--acquire`/`--release` 路径不依赖它）。
- **前端依赖上限**：只用 Vue 3 + Vite 脚手架自带内容。**不引入** axios/pinia/vue-router —— 用原生 `fetch` 与原生 `WebSocket`。单页应用。
- **命名与文案**：界面语言中文；emoji 沿用现有项目风格（🧘 🎯 🔒 🌐）。任务状态字段值固定为 `pending` / `in_progress` / `done`（英文小写，与设计文档一致）。
- **平台**：仅需支持 macOS（本机）。屏蔽引擎的 `sudo -n` 依赖 passwordless sudo，配置项在 Task 10 统一给出。
- **屏蔽引擎 hosts 逻辑零改动**：`block_sites` / `restore_hosts` / `backup_hosts` / `flush_dns` 及 immutable flag 处理**不改**；只新增锁函数与命令。
- **锁文件路径**：`config/block_lock.json`，字段 `{"watcher": false, "assistant": false}`。
- **数据库路径**：`config/study_assistant.db`。

---

### Task 1: 屏蔽引擎 — 锁文件读写函数

**Files:**
- Modify: `focus_blocker.py`（在 `_STATE_FILE` 定义附近新增 `_LOCK_FILE`；在「Public API」区域新增 `_load_lock`/`_save_lock`）
- Test: `tests/test_block_lock.py`

**Interfaces:**
- Produces:
  - `focus_blocker._load_lock() -> dict[str, bool]` — 返回 `{"watcher": bool, "assistant": bool}`；文件缺失或损坏时返回 `{"watcher": False, "assistant": False}` 并重建。
  - `focus_blocker._save_lock(lock: dict[str, bool]) -> None` — 原子写入锁文件。

- [ ] **Step 1: 写失败测试**

创建 `tests/test_block_lock.py`：

```python
import json
import importlib
import focus_blocker as fb


def test_load_lock_returns_defaults_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(fb, "_LOCK_FILE", tmp_path / "block_lock.json")
    assert fb._load_lock() == {"watcher": False, "assistant": False}


def test_load_lock_repairs_corrupt_file(tmp_path, monkeypatch):
    lock_file = tmp_path / "block_lock.json"
    lock_file.write_text("{not valid json")
    monkeypatch.setattr(fb, "_LOCK_FILE", lock_file)
    assert fb._load_lock() == {"watcher": False, "assistant": False}


def test_save_then_load_roundtrip(tmp_path, monkeypatch):
    lock_file = tmp_path / "block_lock.json"
    monkeypatch.setattr(fb, "_LOCK_FILE", lock_file)
    fb._save_lock({"watcher": True, "assistant": False})
    assert json.loads(lock_file.read_text()) == {"watcher": True, "assistant": False}
    assert fb._load_lock() == {"watcher": True, "assistant": False}
```

- [ ] **Step 2: 运行测试确认失败**

Run: `/opt/homebrew/bin/python3.12 -m pytest tests/test_block_lock.py -v`
Expected: 全部 FAIL（`AttributeError: module 'focus_blocker' has no attribute '_LOCK_FILE'`）。

- [ ] **Step 3: 写最小实现**

在 `focus_blocker.py` 的 `_STATE_FILE` 定义（约第 93 行）之后新增：

```python
_LOCK_FILE = _CONFIG_DIR / "block_lock.json"
```

在 `# Public API — backup / block / restore` 区域之前新增（放在 `_get_sites` 之后）：

```python
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `/opt/homebrew/bin/python3.12 -m pytest tests/test_block_lock.py -v`
Expected: 3 passed。

- [ ] **Step 5: 提交**

```bash
git add focus_blocker.py tests/test_block_lock.py
git commit -m "feat: add block lock file read/write helpers"
```

---

### Task 2: 屏蔽引擎 — acquire/release 协调逻辑

**Files:**
- Modify: `focus_blocker.py`（新增 `_strip_block_entries`、`acquire_lock`、`release_lock`、`_cmd_acquire`、`_cmd_release`；`main()` 新增命令分发；`_silent_unblock` 复用 `_strip_block_entries`）
- Test: `tests/test_block_lock.py`（追加测试）

**Interfaces:**
- Consumes: `_load_lock` / `_save_lock`（Task 1）、`_has_block_entries` / `block_sites` / `restore_hosts` / `flush_dns` / `backup_hosts` / `_get_sites`（现有）、`elevate`（现有）、`is_admin`（现有）。
- Produces:
  - `focus_blocker._strip_block_entries() -> None` — 从 hosts 文件移除 `# >>> FOCUS_BLOCKER_START` 到 `# <<< FOCUS_BLOCKER_END` 之间的条目（不依赖备份）。
  - `focus_blocker.acquire_lock(owner: str) -> None` — owner ∈ {"watcher","assistant"}。
  - `focus_blocker.release_lock(owner: str) -> None`。

- [ ] **Step 1: 写失败测试**

在 `tests/test_block_lock.py` 追加（用 monkeypatch 替换 hosts 相关函数为假实现，只验证锁决策逻辑，不真改 `/etc/hosts`）：

```python
import focus_blocker as fb


class _FakeHosts:
    def __init__(self, blocked=False, backup=True):
        self.blocked = blocked
        self.backup = backup


def _setup(monkeypatch, tmp_path, blocked=False):
    state = _FakeHosts(blocked=blocked)
    monkeypatch.setattr(fb, "_LOCK_FILE", tmp_path / "block_lock.json")
    monkeypatch.setattr(fb, "_has_block_entries", lambda: state.blocked)
    monkeypatch.setattr(fb, "_get_sites", lambda: ["example.com"])
    monkeypatch.setattr(fb, "backup_hosts", lambda: None)
    monkeypatch.setattr(fb, "flush_dns", lambda: None)
    calls = {"blocked": None}

    def fake_block(sites):
        state.blocked = True
        calls["blocked"] = len(sites)

    def fake_restore():
        state.blocked = False
        calls["blocked"] = 0

    monkeypatch.setattr(fb, "block_sites", fake_block)
    monkeypatch.setattr(fb, "restore_hosts", fake_restore)
    return state


def test_acquire_blocks_when_nothing_blocked(tmp_path, monkeypatch):
    state = _setup(monkeypatch, tmp_path, blocked=False)
    fb.acquire_lock("assistant")
    assert state.blocked is True
    assert fb._load_lock() == {"watcher": False, "assistant": True}


def test_second_acquire_keeps_blocked(tmp_path, monkeypatch):
    state = _setup(monkeypatch, tmp_path, blocked=True)
    fb.acquire_lock("watcher")
    assert state.blocked is True  # already blocked, no double block
    assert fb._load_lock()["watcher"] is True


def test_release_one_owner_keeps_blocked(tmp_path, monkeypatch):
    state = _setup(monkeypatch, tmp_path, blocked=True)
    fb._save_lock({"watcher": True, "assistant": True})
    fb.release_lock("assistant")
    assert state.blocked is True  # watcher still holds
    assert fb._load_lock() == {"watcher": True, "assistant": False}


def test_release_last_owner_restores(tmp_path, monkeypatch):
    state = _setup(monkeypatch, tmp_path, blocked=True)
    fb._save_lock({"watcher": True, "assistant": False})
    fb.release_lock("watcher")
    assert state.blocked is False
    assert fb._load_lock() == {"watcher": False, "assistant": False}
```

- [ ] **Step 2: 运行测试确认失败**

Run: `/opt/homebrew/bin/python3.12 -m pytest tests/test_block_lock.py -v`
Expected: 新增 4 条 FAIL（`AttributeError: module 'focus_blocker' has no attribute 'acquire_lock'`）。

- [ ] **Step 3: 写实现**

在 `focus_blocker.py` 新增 `_strip_block_entries`（放在 `_has_block_entries` 之后）：

```python
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
```

在锁函数之后新增 `acquire_lock` / `release_lock`：

```python
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
```

新增命令入口（放在 `_silent_unblock` 之后）：

```python
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
```

修改 `main()`，在 `elif cmd == "--unblock-only":` 分支之前插入：

```python
    elif cmd in ("--acquire", "--release"):
        if len(sys.argv) < 3 or sys.argv[2] not in ("watcher", "assistant"):
            print("Usage: focus_blocker.py --acquire|--release <watcher|assistant>")
            sys.exit(1)
        owner = sys.argv[2]
        if cmd == "--acquire":
            _cmd_acquire(owner)
        else:
            _cmd_release(owner)
```

同时更新 `_print_usage()`，在 `--unblock-only` 行后加两行：

```python
    print("  python focus_blocker.py --acquire <watcher|assistant>   占住屏蔽锁")
    print("  python focus_blocker.py --release <watcher|assistant>   释放屏蔽锁")
```

最后，把 `_silent_unblock` 里「无备份但有条目」的手动 strip 逻辑替换为复用 `_strip_block_entries`（约第 952-973 行的 `block_sites` + 手动 strip 段），改为：

```python
        if _has_block_entries():
            _remove_immutable_flag()
            _strip_block_entries()
            _restore_immutable_flag()
            flush_dns()
            msg = "🌐 Sites unblocked (recovered without backup)."
```

- [ ] **Step 4: 运行测试确认通过**

Run: `/opt/homebrew/bin/python3.12 -m pytest tests/test_block_lock.py -v`
Expected: 7 passed。

- [ ] **Step 5: 提交**

```bash
git add focus_blocker.py tests/test_block_lock.py
git commit -m "feat: add --acquire/--release block lock coordination"
```

---

### Task 3: focus_watcher 改用共享锁命令

**Files:**
- Modify: `focus_watcher.py`（`_run_blocker` 调用点改为 `--acquire watcher` / `--release watcher`）

**Interfaces:**
- Consumes: `--acquire watcher` / `--release watcher`（Task 2）。
- Produces: 无新接口；`_run_blocker(arg)` 的 `arg` 取值从 `--block-only`/`--unblock-only` 变为 `--acquire watcher`/`--release watcher`。

- [ ] **Step 1: 改启动对齐逻辑**

在 `run_forever()` 中，把启动时的两处调用（约第 223、227 行）改为：

```python
    if active and not should_be_blocked:
        _log("  → focus active but not blocked — blocking now")
        _run_blocker("--acquire", "watcher")
        _notify("🧘 Focus Mode: ON", f"Sites blocked for {name}" if name else "Sites blocked")
    elif not active and should_be_blocked:
        _log("  → focus inactive but still blocked — restoring now")
        _run_blocker("--release", "watcher")
        _notify("🌐 Focus Mode: OFF", "Sites unblocked")
```

- [ ] **Step 2: 改状态转换逻辑**

在 `run_forever()` 主循环里，两处（约第 258、267 行）改为：

```python
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
```

- [ ] **Step 3: 改 `_run_blocker` 签名以支持两个参数**

把 `_run_blocker(arg: str)` 改为 `_run_blocker(*args: str)`，内部命令拼接：

```python
def _run_blocker(*args: str) -> bool:
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
```

- [ ] **Step 4: 语法校验**

Run: `/opt/homebrew/bin/python3.12 -m py_compile focus_watcher.py`
Expected: 无输出，退出码 0。

- [ ] **Step 5: 提交**

```bash
git add focus_watcher.py
git commit -m "feat: watcher uses shared block lock (acquire/release)"
```

---

### Task 4: 后端脚手架 — venv、依赖、SQLite

**Files:**
- Create: `app/__init__.py`
- Create: `app/db.py`
- Create: `requirements.txt`
- Create: `tests/conftest.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Produces:
  - `app.db.get_conn() -> sqlite3.Connection` — 打开到 `config/study_assistant.db` 的连接，`row_factory=sqlite3.Row`，`PRAGMA foreign_keys=ON`。
  - `app.db.init_db() -> None` — 建表（幂等）。
  - `app.db.DB_PATH: Path` — 数据库路径（测试通过 monkeypatch 覆盖）。
  - 常量 `TASK_PENDING="pending"` / `TASK_IN_PROGRESS="in_progress"` / `TASK_DONE="done"`（放在 `app/db.py`）。

- [ ] **Step 1: 写失败测试**

创建 `tests/conftest.py`：

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
```

创建 `tests/test_db.py`：

```python
import sqlite3
import app.db as db


def test_init_db_creates_tables(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    conn = sqlite3.connect(tmp_path / "test.db")
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"tasks", "focus_sessions"} <= tables


def test_get_conn_has_row_factory():
    conn = db.get_conn()
    assert conn.row_factory is sqlite3.Row
    conn.close()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `/opt/homebrew/bin/python3.12 -m pytest tests/test_db.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'app'`）。

- [ ] **Step 3: 建 venv 并安装依赖**

```bash
cd /Users/liuzishan/Focus-Blocker
/opt/homebrew/bin/python3.12 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install fastapi "uvicorn[standard]" pytest httpx
```

创建 `requirements.txt`：

```text
fastapi
uvicorn[standard]
pytest
httpx
```

- [ ] **Step 4: 写实现**

创建 `app/__init__.py`（空文件）。

创建 `app/db.py`：

```python
"""SQLite connection + schema for the study assistant."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "config" / "study_assistant.db"

TASK_PENDING = "pending"
TASK_IN_PROGRESS = "in_progress"
TASK_DONE = "done"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    planned_minutes INTEGER NOT NULL DEFAULT 25,
    status          TEXT NOT NULL DEFAULT 'pending',
    sort_order      INTEGER NOT NULL DEFAULT 0,
    created_date    TEXT NOT NULL,
    focus_seconds   INTEGER NOT NULL DEFAULT 0,
    completed_at    TEXT
);

CREATE TABLE IF NOT EXISTS focus_sessions (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id          INTEGER REFERENCES tasks(id) ON DELETE SET NULL,
    start_time       TEXT NOT NULL,
    end_time         TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL,
    completed        INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_tasks_date ON tasks(created_date);
CREATE INDEX IF NOT EXISTS idx_sessions_task ON focus_sessions(task_id);
"""


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript(_SCHEMA)
```

- [ ] **Step 5: 运行测试确认通过**

Run: `./.venv/bin/python3.12 -m pytest tests/test_db.py -v`
Expected: 2 passed。

- [ ] **Step 6: 提交**

```bash
git add app/__init__.py app/db.py requirements.txt tests/conftest.py tests/test_db.py
git commit -m "feat: backend scaffold with SQLite schema"
```

---

### Task 5: 后端 — 任务 CRUD 路由

**Files:**
- Create: `app/models.py`
- Create: `app/routers/__init__.py`
- Create: `app/routers/tasks.py`
- Test: `tests/test_tasks.py`

**Interfaces:**
- Consumes: `get_conn` / `init_db` / `TASK_PENDING` 等常量（Task 4）。
- Produces（后续前端依赖的 REST 契约）:
  - `GET /api/tasks?date=YYYY-MM-DD` → `200 [TaskOut]`
  - `POST /api/tasks` body `{title, planned_minutes?, sort_order?}` → `201 TaskOut`
  - `PATCH /api/tasks/{id}` body 可选 `{title?, planned_minutes?, status?, sort_order?}` → `200 TaskOut`；不存在 → `404`
  - `DELETE /api/tasks/{id}` → `204`；不存在 → `404`
  - `TaskOut` 字段：`id:int, title:str, planned_minutes:int, status:str, sort_order:int, created_date:str, focus_seconds:int, completed_at:str|None`

- [ ] **Step 1: 写失败测试**

创建 `tests/test_tasks.py`：

```python
from fastapi.testclient import TestClient
from datetime import date
import app.db as db


def _client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    from app.main import app
    return TestClient(app)


def test_create_and_list_tasks(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    r = c.post("/api/tasks", json={"title": "复习数学第三章", "planned_minutes": 45})
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "复习数学第三章"
    assert body["status"] == "pending"
    assert body["created_date"] == date.today().isoformat()

    r = c.get("/api/tasks", params={"date": date.today().isoformat()})
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_patch_task_status(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    tid = c.post("/api/tasks", json={"title": "刷 LeetCode"}).json()["id"]
    r = c.patch(f"/api/tasks/{tid}", json={"status": "done"})
    assert r.status_code == 200
    assert r.json()["status"] == "done"
    assert r.json()["completed_at"] is not None


def test_delete_task_404_when_missing(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    assert c.delete("/api/tasks/9999").status_code == 404
```

- [ ] **Step 2: 运行测试确认失败**

Run: `./.venv/bin/python3.12 -m pytest tests/test_tasks.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'app.main'`）。

- [ ] **Step 3: 写模型与路由**

创建 `app/models.py`：

```python
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
```

创建 `app/routers/__init__.py`（空）。

创建 `app/routers/tasks.py`：

```python
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
```

- [ ] **Step 4: 写最小 `app/main.py` 让测试可导入**

创建 `app/main.py`（完整版在 Task 7 完善，这里先挂 tasks 路由）：

```python
from fastapi import FastAPI

from app.db import init_db
from app.routers import tasks

app = FastAPI(title="Study Assistant")


@app.on_event("startup")
def _startup():
    init_db()


app.include_router(tasks.router)
```

- [ ] **Step 5: 运行测试确认通过**

Run: `./.venv/bin/python3.12 -m pytest tests/test_tasks.py -v`
Expected: 3 passed。

- [ ] **Step 6: 提交**

```bash
git add app/models.py app/routers/ app/main.py tests/test_tasks.py
git commit -m "feat: task CRUD REST API"
```

---

### Task 6: 后端 — 会话状态机（权威计时）

**Files:**
- Create: `app/session_manager.py`
- Test: `tests/test_session_manager.py`

**Interfaces:**
- Produces:
  - `SessionManager.start(task_id: int | None, minutes: int) -> dict` — 返回 `{"task_id", "total_seconds", "started_at"}`；已有活动会话时抛 `RuntimeError`。
  - `SessionManager.stop(completed: bool = False) -> dict | None` — 返回 `{"task_id", "duration_seconds", "completed"}`；无活动会话返回 `None`。
  - `SessionManager.current() -> dict | None` — 返回 `{"active": True, "task_id", "total_seconds", "elapsed", "remaining"}`；无会话返回 `None`。
  - `SessionManager.state() -> dict` — 总状态，含 `{"active": bool, "task_id", "total_seconds", "elapsed", "remaining"}`（供 `GET /api/sessions/current` 与 WS 复用）。
  - 模块级单例 `session_manager = SessionManager()`。

- [ ] **Step 1: 写失败测试**

创建 `tests/test_session_manager.py`：

```python
import time
from app.session_manager import SessionManager


def test_start_and_current():
    sm = SessionManager()
    s = sm.start(task_id=1, minutes=25)
    assert s["task_id"] == 1
    assert s["total_seconds"] == 1500

    cur = sm.current()
    assert cur["active"] is True
    assert cur["task_id"] == 1
    assert 0 <= cur["elapsed"] < 2
    assert 1498 <= cur["remaining"] <= 1500


def test_start_while_running_raises():
    sm = SessionManager()
    sm.start(task_id=None, minutes=10)
    try:
        sm.start(task_id=None, minutes=10)
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass


def test_stop_returns_duration_and_completed():
    sm = SessionManager()
    sm.start(task_id=2, minutes=1)
    time.sleep(1.1)
    result = sm.stop(completed=False)
    assert result["task_id"] == 2
    assert result["duration_seconds"] >= 1
    assert result["completed"] is False
    assert sm.current() is None


def test_state_idle_when_no_session():
    sm = SessionManager()
    st = sm.state()
    assert st["active"] is False
```

- [ ] **Step 2: 运行测试确认失败**

Run: `./.venv/bin/python3.12 -m pytest tests/test_session_manager.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'app.session_manager'`）。

- [ ] **Step 3: 写实现**

创建 `app/session_manager.py`：

```python
"""In-memory authoritative timer for focus sessions."""

from __future__ import annotations

import time


class SessionManager:
    def __init__(self) -> None:
        self._current: dict | None = None

    def start(self, task_id: int | None, minutes: int) -> dict:
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

    def state(self) -> dict:
        cur = self.current()
        if cur is None:
            return {"active": False, "task_id": None,
                    "total_seconds": 0, "elapsed": 0, "remaining": 0}
        return cur


session_manager = SessionManager()
```

- [ ] **Step 4: 运行测试确认通过**

Run: `./.venv/bin/python3.12 -m pytest tests/test_session_manager.py -v`
Expected: 4 passed。

- [ ] **Step 5: 提交**

```bash
git add app/session_manager.py tests/test_session_manager.py
git commit -m "feat: authoritative session timer (state machine)"
```

---

### Task 7: 后端 — 会话路由 + WebSocket + blocker 封装

**Files:**
- Create: `app/blocker.py`
- Create: `app/routers/sessions.py`
- Modify: `app/main.py`（挂 sessions 路由 + WS 端点 + 启动时清理残留锁）
- Test: `tests/test_sessions.py`

**Interfaces:**
- Consumes: `session_manager`（Task 6）、`get_conn`（Task 4）、`TASK_IN_PROGRESS`/`TASK_DONE`（Task 4）。
- Produces:
  - `app.blocker.acquire(owner: str) -> tuple[bool, str]` — 返回 `(success, stderr)`。
  - `app.blocker.release(owner: str) -> tuple[bool, str]`。
  - `POST /api/sessions/start` body `{task_id?: int|null, minutes: int}` → `200 {state}`；已运行 → `409`；屏蔽失败 → `502`。
  - `POST /api/sessions/stop` body `{completed?: bool}` → `200 {session, state}`；无会话 → `409`。
  - `GET /api/sessions/current` → `200 state`。
  - `WS /ws` → 连接即推送当前 state，会话状态变化时广播。

- [ ] **Step 1: 写失败测试**

创建 `tests/test_sessions.py`：

```python
from fastapi.testclient import TestClient
import app.db as db
import app.session_manager as sm
import app.blocker as blocker


def _client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    sm.session_manager._current = None
    # fake blocker so tests don't need sudo
    monkeypatch.setattr(blocker, "acquire", lambda owner: (True, ""))
    monkeypatch.setattr(blocker, "release", lambda owner: (True, ""))
    from app.main import app
    return TestClient(app)


def test_start_stop_session_lifecycle(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    tid = c.post("/api/tasks", json={"title": "背单词"}).json()["id"]

    r = c.post("/api/sessions/start", json={"task_id": tid, "minutes": 25})
    assert r.status_code == 200
    assert r.json()["active"] is True

    r = c.get("/api/sessions/current")
    assert r.json()["active"] is True

    r = c.post("/api/sessions/stop", json={"completed": True})
    assert r.status_code == 200
    assert r.json()["session"]["completed"] is True
    assert r.json()["state"]["active"] is False


def test_start_while_running_returns_409(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    c.post("/api/sessions/start", json={"task_id": None, "minutes": 10})
    r = c.post("/api/sessions/start", json={"task_id": None, "minutes": 10})
    assert r.status_code == 409


def test_stop_without_session_returns_409(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch)
    assert c.post("/api/sessions/stop").status_code == 409
```

- [ ] **Step 2: 运行测试确认失败**

Run: `./.venv/bin/python3.12 -m pytest tests/test_sessions.py -v`
Expected: FAIL（`ModuleNotFoundError: No module named 'app.blocker'`）。

- [ ] **Step 3: 写 blocker 封装**

创建 `app/blocker.py`：

```python
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
```

- [ ] **Step 4: 写会话路由**

创建 `app/routers/sessions.py`：

```python
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
```

- [ ] **Step 5: 完善 `app/main.py` 挂路由与 WS**

把 `app/main.py` 替换为：

```python
from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from app.db import init_db
from app.routers import tasks, sessions
from app.session_manager import session_manager
from app import blocker

app = FastAPI(title="Study Assistant")


@app.on_event("startup")
def _startup():
    init_db()
    # Clean up any stale assistant lock left by a previous backend crash
    blocker.release("assistant")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            # Backend is the authoritative timer: stream state every second.
            await ws.send_text(
                json.dumps({"type": "state", "state": session_manager.state()})
            )
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass


app.include_router(tasks.router)
app.include_router(sessions.router)
```

说明：WS 端点自己每秒推送一次状态，因此 `sessions.py` 无需广播——省去客户端列表与循环导入，`start_session`/`stop_session` 保持同步 `def`（阻塞的 `sudo` 调用不会卡住事件循环）。前端每秒收到 state，倒计时自然推进。

- [ ] **Step 6: 运行测试确认通过**

Run: `./.venv/bin/python3.12 -m pytest tests/test_sessions.py -v`
Expected: 3 passed。

- [ ] **Step 7: 提交**

```bash
git add app/blocker.py app/routers/sessions.py app/main.py tests/test_sessions.py
git commit -m "feat: session start/stop routes + WebSocket broadcast"
```

---

### Task 8: 前端脚手架 + API 客户端

**Files:**
- Create: `web/`（Vite + Vue 3 脚手架）
- Create: `web/src/api/client.js`

**Interfaces:**
- Produces（后续组件依赖）:
  - `web/src/api/client.js` 导出 `fetchTasks(date)`, `createTask(title, plannedMinutes)`, `updateTask(id, patch)`, `deleteTask(id)`, `startSession(taskId, minutes)`, `stopSession(completed)`, `currentSession()`, `connectWs(onState)`（返回关闭函数）。

- [ ] **Step 1: 脚手架**

```bash
cd /Users/liuzishan/Focus-Blocker
npm create vite@latest web -- --template vue
cd web
npm install
```

- [ ] **Step 2: 配置 dev 代理**

编辑 `web/vite.config.js`，加入代理（前端 5173 → 后端 8000）：

```js
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/ws': { target: 'ws://127.0.0.1:8000', ws: true },
    },
  },
})
```

- [ ] **Step 3: 写 API 客户端**

创建 `web/src/api/client.js`：

```js
const BASE = ''

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (res.status === 204) return null
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export function fetchTasks(date) {
  return request(`/api/tasks?date=${encodeURIComponent(date)}`)
}
export function createTask(title, plannedMinutes = 25) {
  return request('/api/tasks', { method: 'POST', body: JSON.stringify({ title, planned_minutes: plannedMinutes }) })
}
export function updateTask(id, patch) {
  return request(`/api/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(patch) })
}
export function deleteTask(id) {
  return request(`/api/tasks/${id}`, { method: 'DELETE' })
}
export function startSession(taskId, minutes) {
  return request('/api/sessions/start', { method: 'POST', body: JSON.stringify({ task_id: taskId, minutes }) })
}
export function stopSession(completed) {
  return request('/api/sessions/stop', { method: 'POST', body: JSON.stringify({ completed }) })
}
export function currentSession() {
  return request('/api/sessions/current')
}
export function connectWs(onState) {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  const ws = new WebSocket(`${proto}://${location.host}/ws`)
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data)
    if (msg.type === 'state') onState(msg.state)
  }
  ws.onclose = () => setTimeout(() => connectWs(onState), 2000)
  return () => ws.close()
}
```

- [ ] **Step 4: 冒烟验证脚手架可启动**

Run: `cd web && npm run dev`
Expected: Vite 输出 `Local: http://localhost:5173/`，无报错。

- [ ] **Step 5: 提交**

```bash
git add web/vite.config.js web/src/api/client.js web/package.json web/package-lock.json web/index.html web/src/main.js web/src/App.vue
git commit -m "feat: Vue 3 scaffold + API client with WS"
```

---

### Task 9: 前端 — 任务清单组件

**Files:**
- Create: `web/src/components/TaskList.vue`
- Modify: `web/src/App.vue`

**Interfaces:**
- Consumes: `fetchTasks` / `createTask` / `updateTask` / `deleteTask`（Task 8）。
- Produces: `TaskList` 组件，`props: { date: String }`，`emits: ['start']`（携带选中任务对象）。

- [ ] **Step 1: 写 TaskList 组件**

创建 `web/src/components/TaskList.vue`：

```vue
<script setup>
import { ref, onMounted, watch } from 'vue'
import { fetchTasks, createTask, updateTask, deleteTask } from '../api/client'

const props = defineProps({ date: String })
const emit = defineEmits(['start'])

const tasks = ref([])
const newTitle = ref('')
const newMinutes = ref(25)

async function load() {
  tasks.value = await fetchTasks(props.date)
}
async function add() {
  if (!newTitle.value.trim()) return
  await createTask(newTitle.value.trim(), newMinutes.value)
  newTitle.value = ''
  newMinutes.value = 25
  await load()
}
async function toggle(id, status) {
  await updateTask(id, { status })
  await load()
}
async function remove(id) {
  await deleteTask(id)
  await load()
}
onMounted(load)
watch(() => props.date, load)
</script>

<template>
  <section class="task-list">
    <h2>📋 今日任务</h2>
    <form @submit.prevent="add" class="add-form">
      <input v-model="newTitle" placeholder="输入任务，如：复习数学第三章" />
      <input v-model.number="newMinutes" type="number" min="1" class="mins" />
      <button type="submit">添加</button>
    </form>
    <ul>
      <li v-for="t in tasks" :key="t.id" :class="t.status">
        <span class="title">{{ t.title }}</span>
        <span class="meta">{{ Math.round(t.focus_seconds / 60) }}min / 计划 {{ t.planned_minutes }}min</span>
        <button v-if="t.status !== 'done'" @click="emit('start', t)">▶ 专注</button>
        <button v-if="t.status === 'pending'" @click="toggle(t.id, 'done')">✓</button>
        <button v-else-if="t.status === 'done'" @click="toggle(t.id, 'pending')">↩</button>
        <button class="del" @click="remove(t.id)">✕</button>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.task-list { max-width: 640px; margin: 0 auto; padding: 24px; }
.add-form { display: flex; gap: 8px; margin-bottom: 16px; }
.add-form input[type=text] { flex: 1; }
.add-form .mins { width: 64px; }
ul { list-style: none; padding: 0; }
li { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border: 1px solid #333; border-radius: 8px; margin-bottom: 8px; }
li.done .title { text-decoration: line-through; color: #666; }
.title { flex: 1; }
.meta { color: #888; font-size: 13px; }
button { cursor: pointer; }
.del { color: #c66; border: none; background: none; }
</style>
```

- [ ] **Step 2: 写 App.vue 挂载**

替换 `web/src/App.vue`：

```vue
<script setup>
import { ref } from 'vue'
import TaskList from './components/TaskList.vue'

const today = new Date().toISOString().slice(0, 10)
const activeTask = ref(null)
</script>

<template>
  <main>
    <h1>🧘 沉浸式学习助手</h1>
    <TaskList :date="today" @start="(t) => (activeTask = t)" />
  </main>
</template>

<style>
body { margin: 0; background: #0d0d0d; color: #eee; font-family: -apple-system, sans-serif; }
main { max-width: 720px; margin: 0 auto; padding: 24px; }
h1 { text-align: center; }
</style>
```

- [ ] **Step 3: 冒烟验证**

Run: 后端 `./.venv/bin/python3.12 -m uvicorn app.main:app --port 8000`（另一终端）；前端 `cd web && npm run dev`。
Expected: 打开 `http://localhost:5173`，能添加任务并显示列表，点「✓」能标记完成。

- [ ] **Step 4: 提交**

```bash
git add web/src/components/TaskList.vue web/src/App.vue
git commit -m "feat: task list UI (add/toggle/delete/start)"
```

---

### Task 10: 前端 — 专注计时组件 + 自动完成

**Files:**
- Create: `web/src/components/FocusTimer.vue`
- Modify: `web/src/App.vue`（接入 timer + WS 状态）

**Interfaces:**
- Consumes: `startSession` / `stopSession` / `currentSession` / `connectWs`（Task 8）。
- Produces: `FocusTimer` 组件，`props: { task: Object|null }`，`emits: ['finished']`。

- [ ] **Step 1: 写 FocusTimer 组件**

创建 `web/src/components/FocusTimer.vue`：

```vue
<script setup>
import { ref, watch, onUnmounted } from 'vue'
import { startSession, stopSession, currentSession, connectWs } from '../api/client'

const props = defineProps({ task: { type: Object, default: null } })
const emit = defineEmits(['finished'])

const state = ref({ active: false, remaining: 0, total_seconds: 0 })
const planned = ref(25)
let closeWs = null

function fmt(s) {
  const m = Math.floor(s / 60), sec = s % 60
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`
}

async function begin() {
  await startSession(props.task?.id ?? null, planned.value)
  emit('finished')  // prompt parent to refresh task list
}
async function stop() {
  await stopSession(false)
  emit('finished')
}

onUnmounted(() => closeWs && closeWs())
closeWs = connectWs((s) => { state.value = s })
currentSession().then((s) => { state.value = s })

// auto-complete: when remaining hits 0, stop as completed
let lastRemaining = null
watch(() => state.value.remaining, async (r) => {
  if (state.value.active && r === 0 && lastRemaining !== 0) {
    lastRemaining = 0
    await stopSession(true)
    emit('finished')
  } else if (r !== 0) {
    lastRemaining = r
  }
})
</script>

<template>
  <section class="timer">
    <div v-if="state.active" class="counting">
      <div class="clock">{{ fmt(state.remaining) }}</div>
      <button class="stop" @click="stop">🛑 停止（不计完成）</button>
    </div>
    <div v-else class="idle">
      <div class="task-name">{{ props.task ? props.task.title : '自由专注' }}</div>
      <input v-model.number="planned" type="number" min="1" />
      <button @click="begin">▶ 开始专注</button>
    </div>
  </section>
</template>

<style scoped>
.timer { max-width: 640px; margin: 24px auto; padding: 24px; border: 1px solid #333; border-radius: 12px; text-align: center; }
.clock { font-size: 56px; font-variant-numeric: tabular-nums; margin: 12px 0; }
button { margin: 0 8px; padding: 8px 16px; }
</style>
```

- [ ] **Step 2: 接入 App.vue**

把 `web/src/App.vue` 的 script 与 template 改为：

```vue
<script setup>
import { ref } from 'vue'
import TaskList from './components/TaskList.vue'
import FocusTimer from './components/FocusTimer.vue'

const today = new Date().toISOString().slice(0, 10)
const activeTask = ref(null)
</script>

<template>
  <main>
    <h1>🧘 沉浸式学习助手</h1>
    <FocusTimer :task="activeTask" @finished="activeTask = null" />
    <TaskList :date="today" @start="(t) => (activeTask = t)" />
  </main>
</template>
```

- [ ] **Step 3: 冒烟验证完整链路**

Run: 后端 `./.venv/bin/python3.12 -m uvicorn app.main:app --port 8000`；前端 `cd web && npm run dev`。
Expected:
1. 添加任务 → 列表显示。
2. 点「▶ 专注」→ timer 开始倒计时，网站被屏蔽（可 `sudo cat /etc/hosts` 验证 `FOCUS_BLOCKER_START` 标记出现）。
3. 等计时到 0 或点「停止」→ 网站解除，任务状态更新，专注秒数累计。

- [ ] **Step 4: 提交**

```bash
git add web/src/components/FocusTimer.vue web/src/App.vue
git commit -m "feat: focus timer UI with auto-complete"
```

---

### Task 11: passwordless sudo 配置 + README 更新 + 端到端验收

**Files:**
- Modify: `README.md`（新增「学习助手」章节）
- Create: `web/README.md` 无需；在根 README 补启动说明

**Interfaces:**
- Consumes: 全部已有组件。

- [ ] **Step 1: 配置 passwordless sudo**

本计划用 `.venv` 的 Python 3.12 与绝对路径调用 `focus_blocker.py`，需给该 Python 配 passwordless sudo。执行（需你手动输密码，建议用 `!` 前缀在会话里跑，或你自己在终端跑）：

```bash
sudo visudo
```

追加一行（把 `liuzishan` 换成你的用户名，路径按实际 `.venv` 绝对路径）：

```
liuzishan ALL=(ALL) NOPASSWD: /Users/liuzishan/Focus-Blocker/.venv/bin/python3.12 /Users/liuzishan/Focus-Blocker/focus_blocker.py *
```

验证：

```bash
sudo -n /Users/liuzishan/Focus-Blocker/.venv/bin/python3.12 /Users/liuzishan/Focus-Blocker/focus_blocker.py list
```

Expected: 无密码提示，输出站点列表。

- [ ] **Step 2: 更新 README**

在 README 的「Quick Start」之前新增一节：

```markdown
## 🧘 学习助手（Web 界面）

Web 版学习助手：规划每日任务、一键启动专注、计时结束自动完成。

### 启动后端

```bash
cd Focus-Blocker
/opt/homebrew/bin/python3.12 -m venv .venv   # 首次
./.venv/bin/pip install -r requirements.txt  # 首次
./.venv/bin/python3.12 -m uvicorn app.main:app --port 8000
```

### 启动前端

```bash
cd web
npm install   # 首次
npm run dev
```

打开 http://localhost:5173 使用。

### 与系统 Focus 勿扰的配合

学习助手与系统 Focus 勿扰通过 `config/block_lock.json` 共享锁协调：
- 两者任一开启，网站即被屏蔽；两者都关闭才解除。
- 屏蔽引擎新增 `--acquire <watcher|assistant>` / `--release <watcher|assistant>` 命令，学习助手用 `assistant`，Focus 守护进程用 `watcher`。
```

- [ ] **Step 3: 端到端验收（真实 sudo + 真实 hosts）**

依次执行并确认：

```bash
# 1. 起后端
./.venv/bin/python3.12 -m uvicorn app.main:app --port 8000

# 2. 起前端
cd web && npm run dev

# 3. 浏览器走完整链路：添加任务 → 开始专注 → 验证 /etc/hosts 被屏蔽 →
#    停止 → 验证 hosts 恢复 → 任务秒数累计
sudo grep FOCUS_BLOCKER /etc/hosts   # 专注中应有输出
```

Expected: 全部符合 Task 10 冒烟预期，且退出后 hosts 无残留标记、锁文件两键均为 false。

- [ ] **Step 4: 提交**

```bash
git add README.md
git commit -m "docs: study assistant web app usage + sudo setup"
```

---

## 任务依赖图

```
Task 1 ─→ Task 2 ─→ Task 3
              └──────→ Task 7（blocker 依赖 Task 2 的命令）
Task 4 ─→ Task 5 ─→ Task 7
Task 6 ─→ Task 7
Task 8 ─→ Task 9 ─→ Task 10
Task 4,5,6,7,8,9,10 ─→ Task 11（验收）
```

建议顺序：1→2→3（引擎层），4→5→6→7（后端层），8→9→10（前端层），11（验收收尾）。
