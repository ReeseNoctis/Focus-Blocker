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
