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
