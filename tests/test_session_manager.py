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


def test_pause_freezes_remaining_and_resume_continues():
    sm = SessionManager()
    sm.start(task_id=3, minutes=10)
    time.sleep(0.3)
    before = sm.current()["remaining"]

    sm.pause()
    paused = sm.current()
    assert paused["paused"] is True
    assert paused["remaining"] <= before
    frozen = paused["remaining"]

    # Sleeping while paused must not change remaining.
    time.sleep(0.3)
    assert sm.current()["remaining"] == frozen

    sm.resume()
    resumed = sm.current()
    assert resumed["paused"] is False
    # Resume continues from the frozen remainder (not reset to full 600s).
    assert resumed["remaining"] <= frozen
    assert resumed["remaining"] < 600


def test_pause_and_resume_when_no_session_are_noops():
    sm = SessionManager()
    assert sm.pause() is None
    assert sm.resume() is None


def test_stop_after_pause_returns_elapsed_not_full_duration():
    sm = SessionManager()
    sm.start(task_id=4, minutes=10)
    time.sleep(0.3)
    sm.pause()
    time.sleep(0.2)  # paused time should not count toward duration
    result = sm.stop(completed=True)
    # duration reflects only active seconds, not the full 600s nor paused time
    assert result["duration_seconds"] < 600
    assert sm.current() is None
