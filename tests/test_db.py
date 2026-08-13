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
