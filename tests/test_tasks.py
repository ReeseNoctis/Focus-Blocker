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
