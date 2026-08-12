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
