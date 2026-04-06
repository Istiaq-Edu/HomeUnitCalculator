from PyQt5.QtCore import QObject, pyqtSignal


class UpdateCoordinator(QObject):
    """Centralized, minimal app-wide update state coordinator."""

    status_changed = pyqtSignal(str, str)
    local_change_emitted = pyqtSignal(str, str, object)
    remote_change_emitted = pyqtSignal(str, str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._connection_mode = "starting"
        self._active_activities = {}
        self._editing_domains = set()
        self._pending_remote_domains = set()
        self._pending_remote_events = {}
        self._last_status = (None, None)

    def set_connection_mode(self, mode: str):
        self._connection_mode = str(mode or "starting")
        self._emit_status()

    def begin_activity(self, key: str, message: str | None = None):
        if not key:
            return
        self._active_activities[str(key)] = message or ""
        self._emit_status()

    def end_activity(self, key: str):
        if not key:
            return
        self._active_activities.pop(str(key), None)
        self._emit_status()

    def begin_edit_session(self, domain: str):
        if not domain:
            return
        self._editing_domains.add(str(domain))
        self._emit_status()

    def end_edit_session(self, domain: str):
        if not domain:
            return
        domain_key = str(domain)
        self._editing_domains.discard(domain_key)
        self._emit_status()
        pending = self._pending_remote_events.pop(domain_key, None)
        self._pending_remote_domains.discard(domain_key)
        if pending is not None:
            action, payload = pending
            self.remote_change_emitted.emit(domain_key, action, payload)

    def clear_pending_remote_updates(self, domain: str | None = None):
        if domain is None:
            self._pending_remote_domains.clear()
            self._pending_remote_events.clear()
        else:
            domain_key = str(domain)
            self._pending_remote_domains.discard(domain_key)
            self._pending_remote_events.pop(domain_key, None)
        self._emit_status()

    def emit_local_change(self, domain: str, action: str, payload=None):
        self.local_change_emitted.emit(str(domain), str(action), payload)

    def emit_remote_change(self, domain: str, action: str, payload=None) -> bool:
        domain_key = str(domain)
        if domain_key in self._editing_domains:
            self._pending_remote_domains.add(domain_key)
            self._pending_remote_events[domain_key] = (str(action), payload)
            self._emit_status()
            return False

        self.remote_change_emitted.emit(domain_key, str(action), payload)
        return True

    def _build_status(self) -> tuple[str, str]:
        if self._pending_remote_domains and self._editing_domains:
            return ("Updates: deferred while editing", "warning")

        if self._active_activities:
            latest_message = next(reversed(self._active_activities.values()), "")
            return (latest_message or "Updates: syncing", "info")

        mode_to_status = {
            "starting": ("Updates: starting", "info"),
            "live": ("Updates: live", "success"),
            "polling": ("Updates: polling fallback", "info"),
            "local": ("Updates: local only", "muted"),
            "offline": ("Updates: offline", "warning"),
        }
        return mode_to_status.get(self._connection_mode, ("Updates: ready", "muted"))

    def _emit_status(self):
        status = self._build_status()
        if status == self._last_status:
            return
        self._last_status = status
        self.status_changed.emit(*status)
