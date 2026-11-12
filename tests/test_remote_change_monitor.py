from src.core.remote_change_monitor import RemoteChangeMonitor
from src.core.update_coordinator import UpdateCoordinator


class _DummyWindow:
    def __init__(self):
        self._visible = True
        self._minimized = False
        self._active = True

    def isVisible(self):
        return self._visible

    def isMinimized(self):
        return self._minimized

    def isActiveWindow(self):
        return self._active


def test_update_coordinator_flushes_deferred_remote_event_after_edit_session():
    coordinator = UpdateCoordinator()
    remote_events = []
    coordinator.remote_change_emitted.connect(
        lambda domain, action, payload: remote_events.append((domain, action, payload))
    )

    coordinator.begin_edit_session("rental")
    applied = coordinator.emit_remote_change("rental", "changed", {"signature": "abc"})

    assert applied is False
    assert remote_events == []

    coordinator.end_edit_session("rental")

    assert remote_events == [("rental", "changed", {"signature": "abc"})]


def test_remote_change_monitor_suppresses_one_remote_echo_after_local_change():
    coordinator = UpdateCoordinator()
    remote_events = []
    coordinator.remote_change_emitted.connect(
        lambda domain, action, payload: remote_events.append((domain, action, payload))
    )
    monitor = RemoteChangeMonitor(_DummyWindow(), coordinator)

    monitor._on_snapshot_ready(
        {
            "main_calculation": "main-1",
            "room_calculation": "room-1",
            "rental": "rent-1",
        }
    )

    monitor.mark_local_change("rental")
    monitor._on_snapshot_ready(
        {
            "main_calculation": "main-1",
            "room_calculation": "room-1",
            "rental": "rent-2",
        }
    )

    assert remote_events == []

    monitor._on_snapshot_ready(
        {
            "main_calculation": "main-2",
            "room_calculation": "room-1",
            "rental": "rent-2",
        }
    )

    assert remote_events == [
        (
            "main_calculation",
            "changed",
            {"main_signature": "main-2", "room_signature": "room-1"},
        )
    ]
