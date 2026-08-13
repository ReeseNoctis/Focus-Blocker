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
