"""Cloud Connection tab — replaces the old SupabaseConfigTab.

Provides a clean, one-click OAuth2 flow for connecting to Supabase.
Users click "Connect to Supabase", their browser opens, they authorize,
and the app auto-provisions their project.
"""

import logging
import threading
import webbrowser
import secrets as pysecrets
from datetime import datetime, timedelta

from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from qfluentwidgets import (
    CardWidget, PrimaryPushButton, PushButton, TitleLabel,
    BodyLabel, InfoBar, InfoBarPosition, FluentIcon,
)

from src.core.supabase_oauth import (
    generate_pkce_pair, build_authorize_url, exchange_code_for_tokens,
    OAUTH_CALLBACK_PORT,
)
from src.ui.oauth_callback_server import OAuthCallbackServer

logger = logging.getLogger(__name__)


class _ProvisionSignals(QObject):
    """Signals for cross-thread communication during provisioning."""
    progress = pyqtSignal(str)
    success = pyqtSignal(dict)
    error = pyqtSignal(str)


class CloudConnectTab(QWidget):
    """Tab for connecting to Supabase via OAuth2 and auto-provisioning a project."""

    def __init__(self, main_window_ref):
        super().__init__()
        self.main_window = main_window_ref
        self.connect_button = None
        self.status_label = None
        self._signals = _ProvisionSignals()
        self._signals.progress.connect(self._on_progress)
        self._signals.success.connect(self._on_success)
        self._signals.error.connect(self._on_error)
        self.init_ui()
        self._refresh_status()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(50, 50, 50, 50)
        layout.setSpacing(20)

        header = TitleLabel("Cloud Connection")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        subtitle = BodyLabel(
            "Connect your Supabase account to enable cloud sync.\n"
            "Each user has their own free Supabase project — your data stays yours."
        )
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        # Status card
        status_card = CardWidget()
        status_layout = QVBoxLayout(status_card)
        self.status_label = BodyLabel("Checking connection status...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 14px; padding: 20px;")
        status_layout.addWidget(self.status_label)
        layout.addWidget(status_card)

        # Connect button
        self.connect_button = PrimaryPushButton(FluentIcon.LINK.icon(), "Connect to Supabase")
        self.connect_button.setFixedHeight(50)
        self.connect_button.setFixedWidth(250)
        self.connect_button.clicked.connect(self._on_connect_clicked)
        layout.addWidget(self.connect_button, alignment=Qt.AlignCenter)

        # Disconnect button (initially hidden)
        self.disconnect_button = PushButton(FluentIcon.CANCEL.icon(), "Disconnect")
        self.disconnect_button.setFixedHeight(40)
        self.disconnect_button.setFixedWidth(150)
        self.disconnect_button.clicked.connect(self._on_disconnect_clicked)
        self.disconnect_button.setVisible(False)
        layout.addWidget(self.disconnect_button, alignment=Qt.AlignCenter)

        # Progress label (shown during provisioning)
        self.progress_label = BodyLabel("")
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)

        # Help text
        help_text = BodyLabel(
            "Don't have a Supabase account? "
            "Create one for free at supabase.com before connecting."
        )
        help_text.setAlignment(Qt.AlignCenter)
        help_text.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(help_text)

        layout.addStretch(1)

    def _refresh_status(self):
        """Check if already connected and update UI accordingly."""
        db = self.main_window.db_manager
        tokens = db.get_oauth_tokens()
        project_ref = db.get_project_ref()

        if tokens and project_ref:
            self.status_label.setText(
                f"✅ Connected to Supabase\n"
                f"Project: {project_ref}\n"
                f"You can sync your data to the cloud."
            )
            self.connect_button.setVisible(False)
            self.disconnect_button.setVisible(True)
        else:
            self.status_label.setText(
                "Not connected to Supabase.\n"
                "Click 'Connect to Supabase' to get started."
            )
            self.connect_button.setVisible(True)
            self.disconnect_button.setVisible(False)

    def _on_connect_clicked(self):
        """Start the OAuth2 flow: open browser, wait for callback, provision."""
        self.connect_button.setEnabled(False)
        self.progress_label.setVisible(True)
        self.progress_label.setText("Opening browser for Supabase login...")

        thread = threading.Thread(target=self._run_oauth_flow, daemon=True)
        thread.start()

    def _run_oauth_flow(self):
        """The OAuth2 + provisioning flow, runs in a background thread."""
        try:
            # Step 1: Generate PKCE pair and state
            verifier, challenge = generate_pkce_pair()
            state = pysecrets.token_urlsafe(32)

            # Step 2: Start callback server
            self._signals.progress.emit("Waiting for authorization...")
            server = OAuthCallbackServer(port=OAUTH_CALLBACK_PORT, expected_state=state)
            server_thread = threading.Thread(target=server.serve_forever, daemon=True)
            server_thread.start()

            # Step 3: Open browser
            url = build_authorize_url(challenge, state)
            webbrowser.open(url)

            # Step 4: Wait for callback (120 second timeout)
            import time
            start = time.time()
            while not server.received and (time.time() - start) < 120:
                server.handle_request()

            if not server.received:
                self._signals.error.emit("Authorization timed out. Please try again.")
                server.shutdown()
                return

            if server.state_mismatch:
                self._signals.error.emit("Security check failed (state mismatch). Please try again.")
                server.shutdown()
                return

            if server.error:
                self._signals.error.emit(f"Authorization denied: {server.error}")
                server.shutdown()
                return

            server.shutdown()

            # Step 5: Exchange code for tokens
            self._signals.progress.emit("Exchanging authorization code...")
            tokens = exchange_code_for_tokens(
                code=server.auth_code,
                code_verifier=verifier,
            )

            # Step 6: Store tokens
            expires_at = (datetime.now() + timedelta(seconds=tokens.get("expires_in", 3600))).isoformat()
            self.main_window.db_manager.save_oauth_tokens({
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "expires_at": expires_at,
            })

            # Step 7: Provision project
            self._signals.progress.emit("Setting up your Supabase project...")
            from src.core.supabase_provisioner import SupabaseProvisioner
            provisioner = SupabaseProvisioner(access_token=tokens["access_token"])
            result = provisioner.provision(db_manager=self.main_window.db_manager)

            self._signals.success.emit(result)

        except Exception as e:
            logger.exception("OAuth provisioning flow failed")
            self._signals.error.emit(f"Connection failed: {e}")

    def _on_progress(self, message: str):
        self.progress_label.setText(message)

    def _on_success(self, result: dict):
        self.progress_label.setVisible(False)
        self.connect_button.setEnabled(True)
        InfoBar.success(
            title="Connected!",
            content=f"Your Supabase project is ready: {result['project_ref']}",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=5000,
            parent=self,
        )
        self._refresh_status()
        if hasattr(self.main_window, "_initialize_supabase_client"):
            self.main_window._initialize_supabase_client()

    def _on_error(self, message: str):
        self.progress_label.setVisible(False)
        self.connect_button.setEnabled(True)
        InfoBar.error(
            title="Connection Failed",
            content=message,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=8000,
            parent=self,
        )

    def _on_disconnect_clicked(self):
        """Disconnect from Supabase by clearing stored credentials."""
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Disconnect",
            "Are you sure you want to disconnect from Supabase?\n"
            "Your cloud data will remain on your Supabase project.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            db = self.main_window.db_manager
            db.clear_oauth_tokens()
            db.clear_project_ref()
            self._refresh_status()
            if hasattr(self.main_window, "_initialize_supabase_client"):
                self.main_window._initialize_supabase_client()
