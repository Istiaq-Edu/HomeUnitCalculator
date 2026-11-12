from src.core.update_coordinator import UpdateCoordinator


def test_update_coordinator_tracks_connection_and_activity_states():
    coordinator = UpdateCoordinator()
    seen = []
    coordinator.status_changed.connect(lambda text, level: seen.append((text, level)))

    coordinator.set_connection_mode("polling")
    coordinator.begin_activity("dashboard-years", "Updates: syncing dashboard")
    coordinator.end_activity("dashboard-years")

    assert seen[0] == ("Updates: polling fallback", "info")
    assert seen[1] == ("Updates: syncing dashboard", "info")
    assert seen[2] == ("Updates: polling fallback", "info")


def test_update_coordinator_defers_remote_changes_while_editing():
    coordinator = UpdateCoordinator()
    seen = []
    remote_events = []
    coordinator.status_changed.connect(lambda text, level: seen.append((text, level)))
    coordinator.remote_change_emitted.connect(
        lambda domain, action, payload: remote_events.append((domain, action, payload))
    )

    coordinator.set_connection_mode("polling")
    coordinator.begin_edit_session("rental")
    applied = coordinator.emit_remote_change("rental", "updated", {"id": "abc"})

    assert applied is False
    assert remote_events == []
    assert seen[-1] == ("Updates: deferred while editing", "warning")

    coordinator.clear_pending_remote_updates("rental")
    coordinator.end_edit_session("rental")

    assert seen[-1] == ("Updates: polling fallback", "info")


def test_update_coordinator_emits_remote_change_when_not_editing():
    coordinator = UpdateCoordinator()
    remote_events = []
    coordinator.remote_change_emitted.connect(
        lambda domain, action, payload: remote_events.append((domain, action, payload))
    )

    applied = coordinator.emit_remote_change("history", "deleted", {"id": 5})

    assert applied is True
    assert remote_events == [("history", "deleted", {"id": 5})]
