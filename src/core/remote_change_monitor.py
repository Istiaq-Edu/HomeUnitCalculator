from PyQt5.QtCore import QObject, QTimer


class RemoteChangeMonitor(QObject):
    def __init__(self, main_window, coordinator, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.coordinator = coordinator
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll_once)
        self._worker = None
        self._last_signatures = {}
        self._suppress_next_domains = set()

    def start(self):
        self._update_interval()
        if not self._timer.isActive():
            self._timer.start()
        self._poll_once()

    def stop(self):
        if self._timer.isActive():
            self._timer.stop()

    def mark_local_change(self, domain: str):
        if domain:
            self._suppress_next_domains.add(str(domain))

    def _update_interval(self):
        if not self.main_window.isVisible() or self.main_window.isMinimized():
            interval_ms = 30000
        elif self.main_window.isActiveWindow():
            interval_ms = 10000
        else:
            interval_ms = 10000
        self._timer.setInterval(interval_ms)

    def _poll_once(self):
        self._update_interval()

        supabase_manager = getattr(self.main_window, "supabase_manager", None)
        if not supabase_manager or not supabase_manager.is_client_initialized():
            self.coordinator.set_connection_mode("local")
            return

        if self._worker is not None and self._worker.isRunning():
            return

        from src.ui.background_workers import FetchRemoteChangeSnapshotWorker

        self._worker = FetchRemoteChangeSnapshotWorker(supabase_manager, parent=self)
        self._worker.snapshot_ready.connect(self._on_snapshot_ready)
        self._worker.error_occurred.connect(self._on_snapshot_error)
        self._worker.finished.connect(self._on_snapshot_finished)
        self._worker.start()

    def _on_snapshot_ready(self, snapshot: dict):
        self.coordinator.set_connection_mode("polling")

        if not self._last_signatures:
            self._last_signatures = dict(snapshot or {})
            return

        changed_domains = []
        if snapshot.get("rental") != self._last_signatures.get("rental"):
            changed_domains.append(("rental", {"signature": snapshot.get("rental")}))

        main_changed = snapshot.get("main_calculation") != self._last_signatures.get(
            "main_calculation"
        )
        room_changed = snapshot.get("room_calculation") != self._last_signatures.get(
            "room_calculation"
        )
        if main_changed or room_changed:
            changed_domains.append(
                (
                    "main_calculation",
                    {
                        "main_signature": snapshot.get("main_calculation"),
                        "room_signature": snapshot.get("room_calculation"),
                    },
                )
            )

        self._last_signatures = dict(snapshot or {})

        for domain, payload in changed_domains:
            if domain in self._suppress_next_domains:
                self._suppress_next_domains.discard(domain)
                continue
            self.coordinator.emit_remote_change(domain, "changed", payload)

    def _on_snapshot_error(self, _message: str):
        self.coordinator.set_connection_mode("offline")

    def _on_snapshot_finished(self):
        self._worker = None
