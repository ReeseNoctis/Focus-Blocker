import app.ai_client as ac


def test_extract_json_plain(monkeypatch):
    assert ac._extract_json('[{"title": "a", "planned_minutes": 60}]') == [
        {"title": "a", "planned_minutes": 60}
    ]


def test_extract_json_strips_code_fence(monkeypatch):
    content = '```json\n[{"title": "b", "planned_minutes": 45}]\n```'
    assert ac._extract_json(content) == [{"title": "b", "planned_minutes": 45}]


def test_extract_json_raises_on_non_array(monkeypatch):
    import pytest
    with pytest.raises(ValueError):
        ac._extract_json('{"not": "an array"}')


def test_plan_tasks_normalizes_and_filters(monkeypatch):
    # Fake the HTTP layer so no real DeepSeek call happens.
    captured = {}

    class FakeResp:
        status_code = 200
        def json(self):
            return {"choices": [{"message": {"content":
                '[{"title":"学英语","planned_minutes":"90"},'
                '{"title":"","planned_minutes":30},'
                '{"title":"刷题","planned_minutes":9999}]'}}]}

    def fake_post(url, **kwargs):
        captured["json"] = kwargs["json"]
        captured["headers"] = kwargs["headers"]
        return FakeResp()

    monkeypatch.setattr(ac.httpx, "post", fake_post)
    monkeypatch.setattr(ac, "_load_config", lambda: {"deepseek_api_key": "sk-test"})

    tasks = ac.plan_tasks("学英语,刷题")
    assert tasks == [
        {"title": "学英语", "planned_minutes": 90},
        {"title": "刷题", "planned_minutes": 720},  # clamped to max
    ]
    assert captured["headers"]["Authorization"] == "Bearer sk-test"
    assert captured["json"]["model"] == "deepseek-chat"


def test_plan_tasks_raises_without_key(monkeypatch):
    import pytest
    monkeypatch.setattr(ac, "_load_config", lambda: {})
    with pytest.raises(RuntimeError):
        ac.plan_tasks("anything")
