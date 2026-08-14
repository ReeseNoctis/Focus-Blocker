from fastapi.testclient import TestClient
import app.ai_client as ac


def _client(monkeypatch, plan_tasks):
    monkeypatch.setattr(ac, "plan_tasks", plan_tasks)
    from app.main import app
    return TestClient(app)


def test_plan_returns_tasks(monkeypatch):
    def fake(text):
        return [{"title": "学英语", "planned_minutes": 60}]
    c = _client(monkeypatch, fake)
    r = c.post("/api/ai/plan", json={"text": "学英语"})
    assert r.status_code == 200
    assert r.json() == {"tasks": [{"title": "学英语", "planned_minutes": 60}]}


def test_plan_missing_key_returns_500(monkeypatch):
    def fake(text):
        raise RuntimeError("missing DeepSeek API key")
    c = _client(monkeypatch, fake)
    r = c.post("/api/ai/plan", json={"text": "x"})
    assert r.status_code == 500


def test_plan_api_error_returns_502(monkeypatch):
    def fake(text):
        raise RuntimeError("DeepSeek API error 401")
    c = _client(monkeypatch, fake)
    r = c.post("/api/ai/plan", json={"text": "x"})
    assert r.status_code == 502


def test_plan_bad_json_returns_400(monkeypatch):
    def fake(text):
        raise ValueError("bad json")
    c = _client(monkeypatch, fake)
    r = c.post("/api/ai/plan", json={"text": "x"})
    assert r.status_code == 400
