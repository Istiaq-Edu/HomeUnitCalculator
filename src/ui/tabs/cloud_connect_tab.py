"""Cloud Connection tab — premium redesign with detailed status and progress.

Replaces the old SupabaseConfigTab with a clean, one-click OAuth2 flow.
Shows:
- Connection status card with project details when connected
- Step-by-step progress with icons during provisioning
- Detailed error messages with actionable guidance for every failure scenario
- Account info, project info, and quick links when connected
"""

import logging
import threading
import webbrowser
import secrets as pysecrets
from datetime import datetime, timedelta

from PyQt5.QtCore import Qt, pyqtSignal, QObject
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame,
)
from qfluentwidgets import (
    CardWidget, PrimaryPushButton, PushButton, TitleLabel,
    BodyLabel, CaptionLabel, InfoBar, InfoBarPosition, FluentIcon,
    IndeterminateProgressBar, SegmentedWidget,
)

from src.core.supabase_oauth import (
    generate_pkce_pair, build_authorize_url, exchange_code_for_tokens,
    OAUTH_CALLBACK_PORT,
)
from src.ui.oauth_callback_server import OAuthCallbackServer

logger = logging.getLogger(__name__)


class _ThreadSafeDBProxy:
    """Thread-safe proxy for DBManager methods called from background threads."""

    def __init__(self, store_credentials_signal):
        self._store_credentials_signal = store_credentials_signal

    def save_config(self, supabase_url: str, supabase_key: str):
        self._pending_url = supabase_url
        self._pending_key = supabase_key

    def save_project_ref(self, project_ref: str):
        self._store_credentials_signal.emit(
            project_ref,
            getattr(self, "_pending_url", ""),
            getattr(self, "_pending_key", ""),
        )


class _ProvisionSignals(QObject):
    """Signals for cross-thread communication during provisioning."""
    progress = pyqtSignal(str, str)  # (step_title, step_detail)
    success = pyqtSignal(dict)
    error = pyqtSignal(str, str)  # (error_type, error_message)
    store_tokens = pyqtSignal(dict)
    store_credentials = pyqtSignal(str, str, str)


# ─── Style constants (match app's existing dark theme) ──────────────────────

_ACCENT = "#0078D4"
_ACCENT_LIGHT = "#4aa8ff"
_SUCCESS = "#4fd38a"
_WARNING = "#e5b94c"
_ERROR = "#f06d6d"
_MUTED = "#5b616a"
_CARD_BG = "#2b2b2b"
_CARD_BORDER = "#3d3d3d"
_LABEL_FG = "#ffffff"
_LABEL_DIM = "#b0b0b0"


def _info_label(text, color=_LABEL_FG, size=15, bold=False):
    """Create a styled label with explicit transparent background."""
    weight = "bold" if bold else "normal"
    lbl = BodyLabel(text)
    lbl.setStyleSheet(f"""
        color: {color};
        font-size: {size}px;
        font-weight: {weight};
        background: transparent;
        border: none;
    """)
    return lbl


def _caption_label(text, color=_LABEL_DIM):
    """Create a small caption label."""
    lbl = CaptionLabel(text)
    lbl.setStyleSheet(f"""
        color: {color};
        font-size: 13px;
        background: transparent;
        border: none;
    """)
    return lbl


class _StatusCard(CardWidget):
    """Card showing connection status — connected or disconnected."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statusCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            #statusCard {{
                background-color: {_CARD_BG};
                border: 1px solid {_CARD_BORDER};
                border-radius: 12px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        # Status icon + title row
        top_row = QHBoxLayout()
        top_row.setSpacing(12)

        self.status_icon = QLabel()
        self.status_icon.setFixedSize(32, 32)
        self.status_icon.setAlignment(Qt.AlignCenter)
        self.status_icon.setStyleSheet("background: transparent; border: none;")
        top_row.addWidget(self.status_icon)

        self.status_title = _info_label("Checking status...", _LABEL_FG, 18, bold=True)
        top_row.addWidget(self.status_title)
        top_row.addStretch(1)
        layout.addLayout(top_row)

        # Detail line
        self.status_detail = _caption_label("")
        layout.addWidget(self.status_detail)

        # Project info grid (shown when connected)
        self.info_grid_widget = QWidget()
        self.info_grid_widget.setStyleSheet("background: transparent; border: none;")
        self.info_grid = QGridLayout(self.info_grid_widget)
        self.info_grid.setContentsMargins(0, 8, 0, 0)
        self.info_grid.setSpacing(6)
        self.info_grid.setHorizontalSpacing(16)
        self.info_grid_widget.setVisible(False)
        layout.addWidget(self.info_grid_widget)

    def show_connected(self, project_ref, project_url):
        """Show connected state with project details."""
        self.status_icon.setPixmap(FluentIcon.ACCEPT.icon(color=QColor(_SUCCESS)).pixmap(28, 28))
        self.status_title.setText("Connected to Supabase")
        self.status_title.setStyleSheet(f"""
            color: {_SUCCESS};
            font-size: 18px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        self.status_detail.setText("Your data is syncing to the cloud.")

        # Populate info grid
        self._set_info_grid(project_ref, project_url)
        self.info_grid_widget.setVisible(True)

    def show_disconnected(self):
        """Show not connected state."""
        self.status_icon.setPixmap(FluentIcon.CLOUD.icon(color=QColor(_MUTED)).pixmap(28, 28))
        self.status_title.setText("Not Connected")
        self.status_title.setStyleSheet(f"""
            color: {_LABEL_FG};
            font-size: 18px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        self.status_detail.setText("Click 'Connect to Supabase' to enable cloud sync.")
        self.info_grid_widget.setVisible(False)

    def show_progress(self, step_title, step_detail):
        """Show in-progress state."""
        self.status_icon.setPixmap(FluentIcon.SYNC.icon(color=QColor(_ACCENT_LIGHT)).pixmap(28, 28))
        self.status_title.setText(step_title)
        self.status_title.setStyleSheet(f"""
            color: {_ACCENT_LIGHT};
            font-size: 18px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        self.status_detail.setText(step_detail)
        self.info_grid_widget.setVisible(False)

    def show_error(self, error_title, error_detail):
        """Show error state."""
        self.status_icon.setPixmap(FluentIcon.CANCEL.icon(color=QColor(_ERROR)).pixmap(28, 28))
        self.status_title.setText(error_title)
        self.status_title.setStyleSheet(f"""
            color: {_ERROR};
            font-size: 18px;
            font-weight: bold;
            background: transparent;
            border: none;
        """)
        self.status_detail.setText(error_detail)
        self.info_grid_widget.setVisible(False)

    def _set_info_grid(self, project_ref, project_url):
        """Populate the project info grid with key-value pairs."""
        # Clear existing
        for i in reversed(range(self.info_grid.count())):
            self.info_grid.itemAt(i).widget().deleteLater()

        info_items = [
            ("Project ID", project_ref),
            ("Project URL", project_url),
            ("Plan", "Free Tier"),
            ("Database", "500 MB included"),
            ("Storage", "1 GB included"),
        ]

        for row, (key, value) in enumerate(info_items):
            key_lbl = _caption_label(key, _LABEL_DIM)
            val_lbl = _info_label(value, _LABEL_FG, 12)
            self.info_grid.addWidget(key_lbl, row, 0)
            self.info_grid.addWidget(val_lbl, row, 1)


class _ProgressCard(CardWidget):
    """Card showing step-by-step progress during provisioning."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("progressCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            #progressCard {{
                background-color: {_CARD_BG};
                border: 1px solid {_CARD_BORDER};
                border-radius: 12px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        self.title = _info_label("Setting up your project", _ACCENT_LIGHT, 16, bold=True)
        layout.addWidget(self.title)

        self.spinner = IndeterminateProgressBar()
        self.spinner.setVisible(False)
        layout.addWidget(self.spinner)

        self.detail = _caption_label("")
        layout.addWidget(self.detail)

        # Step labels
        self.steps_container = QWidget()
        self.steps_container.setStyleSheet("background: transparent; border: none;")
        self.steps_layout = QVBoxLayout(self.steps_container)
        self.steps_layout.setSpacing(6)
        self.step_labels = []
        steps = [
            "Waiting for browser authorization",
            "Exchanging authorization code",
            "Listing your Supabase projects",
            "Creating or finding your project",
            "Setting up database tables",
            "Fetching API credentials",
        ]
        for step_text in steps:
            lbl = _caption_label(f"○  {step_text}", _LABEL_DIM)
            self.step_labels.append(lbl)
            self.steps_layout.addWidget(lbl)
        self.steps_container.setVisible(False)
        layout.addWidget(self.steps_container)

    def start(self):
        self.spinner.setVisible(True)
        self.steps_container.setVisible(True)
        self.title.setText("Setting up your project")

    def set_step(self, step_index, detail_text=""):
        """Mark step as in progress, previous steps as done."""
        for i, lbl in enumerate(self.step_labels):
            if i < step_index:
                lbl.setText(f"✓  {lbl.text().split('  ', 1)[-1].replace('○  ', '')}")
                lbl.setStyleSheet(f"color: {_SUCCESS}; font-size: 13px; background: transparent; border: none;")
            elif i == step_index:
                lbl.setText(f"●  {lbl.text().split('  ', 1)[-1].replace('○  ', '').replace('✓  ', '').replace('●  ', '')}")
                lbl.setStyleSheet(f"color: {_ACCENT_LIGHT}; font-size: 13px; background: transparent; border: none;")
            else:
                lbl.setStyleSheet(f"color: {_LABEL_DIM}; font-size: 13px; background: transparent; border: none;")
        if detail_text:
            self.detail.setText(detail_text)

    def finish_success(self):
        self.spinner.setVisible(False)
        for lbl in self.step_labels:
            text = lbl.text().split("  ", 1)[-1].replace("○  ", "").replace("●  ", "").replace("✓  ", "")
            lbl.setText(f"✓  {text}")
            lbl.setStyleSheet(f"color: {_SUCCESS}; font-size: 13px; background: transparent; border: none;")
        self.title.setText("Setup complete!")

    def finish_error(self, error_msg):
        self.spinner.setVisible(False)
        self.title.setText("Setup failed")
        self.title.setStyleSheet(f"color: {_ERROR}; font-size: 14px; font-weight: bold; background: transparent; border: none;")
        self.detail.setText(error_msg)

    def reset(self):
        self.spinner.setVisible(False)
        self.steps_container.setVisible(False)
        self.detail.setText("")


class CloudConnectTab(QWidget):
    """Tab for connecting to Supabase via OAuth2 and auto-provisioning a project."""

    def __init__(self, main_window_ref):
        super().__init__()
        self.main_window = main_window_ref
        self.connect_button = None
        self.disconnect_button = None
        self.status_card = None
        self.progress_card = None
        self._signals = _ProvisionSignals()
        self._signals.progress.connect(self._on_progress)
        self._signals.success.connect(self._on_success)
        self._signals.error.connect(self._on_error)
        self._signals.store_tokens.connect(self._on_store_tokens)
        self._signals.store_credentials.connect(self._on_store_credentials)
        self.init_ui()
        self._refresh_status()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(16)

        # ─── Header ───
        header = TitleLabel("Cloud Connection")
        header.setAlignment(Qt.AlignLeft)
        header.setStyleSheet(f"color: {_LABEL_FG}; font-size: 22px; background: transparent; border: none;")
        layout.addWidget(header)

        subtitle = _caption_label(
            "Sync your calculations to the cloud. Each user gets their own free Supabase project — "
            "your data stays yours, completely isolated."
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # ─── Status card ───
        self.status_card = _StatusCard(self)
        layout.addWidget(self.status_card)

        # ─── Progress card (hidden initially) ───
        self.progress_card = _ProgressCard(self)
        self.progress_card.setVisible(False)
        layout.addWidget(self.progress_card)

        # ─── Action buttons row ───
        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        self.connect_button = PrimaryPushButton(FluentIcon.LINK.icon(), "Connect to Supabase")
        self.connect_button.setFixedHeight(44)
        self.connect_button.setFixedWidth(220)
        self.connect_button.clicked.connect(self._on_connect_clicked)
        button_row.addWidget(self.connect_button)

        self.disconnect_button = PushButton("Disconnect")
        self.disconnect_button.setFixedHeight(40)
        self.disconnect_button.setFixedWidth(140)
        self.disconnect_button.clicked.connect(self._on_disconnect_clicked)
        self.disconnect_button.setVisible(False)
        self.disconnect_button.setStyleSheet(f"""
            PushButton {{
                color: #f06d6d;
                background-color: rgba(240, 109, 109, 0.1);
                border: 1px solid rgba(240, 109, 109, 0.3);
                border-radius: 6px;
                font-weight: bold;
                padding: 0 16px;
                text-align: center;
            }}
            PushButton:hover {{
                background-color: rgba(240, 109, 109, 0.2);
                border: 1px solid rgba(240, 109, 109, 0.5);
            }}
            PushButton:pressed {{
                background-color: rgba(240, 109, 109, 0.3);
            }}
        """)
        button_row.addWidget(self.disconnect_button)

        button_row.addStretch(1)
        layout.addLayout(button_row)

        # ─── Help section ───
        help_card = CardWidget(self)
        help_card.setObjectName("helpCard")
        help_card.setAttribute(Qt.WA_StyledBackground, True)
        help_card.setStyleSheet(f"""
            #helpCard {{
                background-color: {_CARD_BG};
                border: 1px solid {_CARD_BORDER};
                border-radius: 12px;
            }}
        """)
        help_layout = QVBoxLayout(help_card)
        help_layout.setContentsMargins(24, 16, 24, 16)
        help_layout.setSpacing(8)

        help_title = _info_label("Need Help?", _LABEL_FG, 14, bold=True)
        help_layout.addWidget(help_title)

        help_items = [
            "• Don't have a Supabase account? Create one free at supabase.com",
            "• The app creates a free project for you automatically — no manual setup needed",
            "• Free projects pause after 7 days of inactivity. Just click Connect again to restore.",
            "• Each Supabase account gets 2 free projects maximum",
        ]
        for item_text in help_items:
            item = _caption_label(item_text, _LABEL_DIM)
            item.setWordWrap(True)
            help_layout.addWidget(item)

        layout.addWidget(help_card)

        layout.addStretch(1)

    def _refresh_status(self):
        """Check if already connected and update UI accordingly."""
        db = self.main_window.db_manager
        tokens = db.get_oauth_tokens()
        project_ref = db.get_project_ref()

        if tokens and project_ref:
            config = db.get_config()
            project_url = config.get("SUPABASE_URL", f"https://{project_ref}.supabase.co")
            self.status_card.show_connected(project_ref, project_url)
            self.connect_button.setVisible(False)
            self.disconnect_button.setVisible(True)
            self.disconnect_button.show()
        else:
            self.status_card.show_disconnected()
            self.connect_button.setVisible(True)
            self.connect_button.show()
            self.disconnect_button.setVisible(False)

    def _on_connect_clicked(self):
        """Start the OAuth2 flow."""
        self.connect_button.setEnabled(False)
        self.connect_button.setVisible(False)
        self.disconnect_button.setVisible(False)
        self.progress_card.setVisible(True)
        self.progress_card.start()
        self.progress_card.set_step(0, "Opening your browser...")
        self.status_card.show_progress("Connecting...", "Please complete the login in your browser.")

        thread = threading.Thread(target=self._run_oauth_flow, daemon=True)
        thread.start()

    def _run_oauth_flow(self):
        """The OAuth2 + provisioning flow, runs in a background thread."""
        try:
            # Step 1: Generate PKCE pair and state
            verifier, challenge = generate_pkce_pair()
            state = pysecrets.token_urlsafe(32)

            # Step 2: Start callback server
            self._signals.progress.emit("Waiting for authorization", "Please log in via your browser.")
            server = OAuthCallbackServer(port=OAUTH_CALLBACK_PORT, expected_state=state)

            # Step 3: Open browser
            url = build_authorize_url(challenge, state)
            webbrowser.open(url)

            # Step 4: Wait for callback
            import time
            start = time.time()
            while not server.received and (time.time() - start) < 120:
                server.handle_request()

            if not server.received:
                self._signals.error.emit(
                    "Authorization Timed Out",
                    "The browser authorization did not complete within 2 minutes.\n"
                    "Please try again and complete the login promptly."
                )
                server.server_close()
                return

            if server.state_mismatch:
                self._signals.error.emit(
                    "Security Check Failed",
                    "The state parameter didn't match. This can happen if you\n"
                    "have multiple browser tabs open. Please close all tabs\n"
                    "and try again."
                )
                server.server_close()
                return

            if server.error:
                error_map = {
                    "access_denied": "You denied the authorization request. Please try again and click 'Authorize'.",
                    "invalid_request": "The authorization request was malformed. Please try again.",
                    "invalid_scope": "The app requested invalid permissions. Please contact support.",
                    "server_error": "Supabase experienced an error. Please try again in a moment.",
                    "temporarily_unavailable": "Supabase is temporarily unavailable. Please try again later.",
                }
                detail = error_map.get(server.error, f"Error: {server.error}")
                if server.error_description:
                    detail += f"\nDetails: {server.error_description}"
                self._signals.error.emit("Authorization Denied", detail)
                server.server_close()
                return

            server.server_close()

            # Step 5: Exchange code for tokens
            self._signals.progress.emit("Exchanging authorization code", "Getting your access tokens...")
            tokens = exchange_code_for_tokens(
                code=server.auth_code,
                code_verifier=verifier,
            )

            # Step 6: Store tokens
            expires_at = (datetime.now() + timedelta(seconds=tokens.get("expires_in", 3600))).isoformat()
            token_data = {
                "access_token": tokens["access_token"],
                "refresh_token": tokens["refresh_token"],
                "expires_at": expires_at,
            }
            self._signals.store_tokens.emit(token_data)

            # Step 7: Provision project
            self._signals.progress.emit("Setting up your project", "Listing your Supabase projects...")
            from src.core.supabase_provisioner import SupabaseProvisioner

            db_proxy = _ThreadSafeDBProxy(self._signals.store_credentials)
            provisioner = SupabaseProvisioner(access_token=tokens["access_token"])
            result = provisioner.provision(db_manager=db_proxy)

            self._signals.success.emit(result)

        except Exception as e:
            logger.exception("OAuth provisioning flow failed")
            error_msg = str(e)

            # Map common errors to user-friendly messages
            if "Limit reached" in error_msg or "limit" in error_msg.lower():
                self._signals.error.emit(
                    "Free Tier Limit Reached",
                    "You've reached the maximum of 2 free projects on your Supabase account.\n\n"
                    "To fix this:\n"
                    "1. Go to supabase.com/dashboard/projects\n"
                    "2. Delete or pause one of your existing projects\n"
                    "3. Click Connect again\n\n"
                    "The app will reuse an existing project if one is available."
                )
            elif "No organizations found" in error_msg:
                self._signals.error.emit(
                    "No Organization Found",
                    "Your Supabase account doesn't have an organization yet.\n\n"
                    "To fix this:\n"
                    "1. Go to supabase.com/dashboard\n"
                    "2. Create a new organization (it's free)\n"
                    "3. Click Connect again"
                )
            elif "timed out" in error_msg.lower() or "timeout" in error_msg.lower():
                self._signals.error.emit(
                    "Connection Timed Out",
                    "The connection to Supabase took too long.\n\n"
                    "This could be due to:\n"
                    "• Slow internet connection\n"
                    "• Supabase servers under heavy load\n"
                    "• Your project is still provisioning\n\n"
                    "Please try again in a moment."
                )
            elif "network" in error_msg.lower() or "connection" in error_msg.lower():
                self._signals.error.emit(
                    "Network Error",
                    "Could not connect to Supabase.\n\n"
                    "Please check:\n"
                    "• Your internet connection is working\n"
                    "• Your firewall allows connections to api.supabase.com\n"
                    "• Try again in a moment"
                )
            elif "paused" in error_msg.lower():
                self._signals.error.emit(
                    "Project Paused",
                    "Your Supabase project is paused due to 7 days of inactivity.\n\n"
                    "To restore it:\n"
                    "1. Go to supabase.com/dashboard/projects\n"
                    "2. Find your project and click 'Restore'\n"
                    "3. Wait 1-2 minutes for it to wake up\n"
                    "4. Click Connect again"
                )
            elif "Token exchange failed" in error_msg:
                self._signals.error.emit(
                    "Authentication Failed",
                    f"Could not exchange the authorization code for tokens.\n\n"
                    f"This may be a temporary issue. Please try again.\n\n"
                    f"Technical details: {error_msg}"
                )
            else:
                self._signals.error.emit("Connection Failed", error_msg)

    def _on_progress(self, step_title: str, step_detail: str):
        self.progress_card.title.setText(step_title)
        self.progress_card.detail.setText(step_detail)
        self.status_card.show_progress(step_title, step_detail)

        # Update step indicators
        step_map = {
            "Waiting for authorization": 0,
            "Exchanging authorization code": 1,
            "Listing your Supabase projects": 2,
            "Setting up your project": 3,
        }
        step_idx = step_map.get(step_title, 0)
        self.progress_card.set_step(step_idx, step_detail)

    def _on_success(self, result: dict):
        self.progress_card.finish_success()
        self.progress_card.setVisible(False)
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

    def _on_store_tokens(self, token_data: dict):
        try:
            self.main_window.db_manager.save_oauth_tokens(token_data)
        except Exception as e:
            logger.error(f"Failed to store OAuth tokens: {e}")

    def _on_store_credentials(self, project_ref: str, project_url: str, anon_key: str):
        try:
            self.main_window.db_manager.save_project_ref(project_ref)
            self.main_window.db_manager.save_config(project_url, anon_key)
        except Exception as e:
            logger.error(f"Failed to store credentials: {e}")

    def _on_error(self, error_title: str, error_message: str):
        self.progress_card.finish_error(error_message)
        self.progress_card.setVisible(False)
        self.connect_button.setEnabled(True)
        self.connect_button.setVisible(True)
        self.status_card.show_error(error_title, error_message)

        InfoBar.error(
            title=error_title,
            content=error_message.split("\n")[0],  # First line only for InfoBar
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=8000,
            parent=self,
        )

    def _on_disconnect_clicked(self):
        """Disconnect from Supabase by clearing stored credentials."""
        from qfluentwidgets import MessageBox
        from PyQt5.QtCore import QTimer

        # Use Fluent MessageBox instead of QMessageBox — cleaner UI, no crash
        msg_box = MessageBox("Disconnect", (
            "Are you sure you want to disconnect from Supabase?\n\n"
            "Your cloud data will remain on your Supabase project.\n"
            "You can reconnect anytime by clicking 'Connect to Supabase'."
        ), self)

        if not msg_box.exec():
            return

        # Clear all credentials
        try:
            db = self.main_window.db_manager
            db.clear_oauth_tokens()
            db.clear_project_ref()
            # Also clear the Supabase URL/Key config
            try:
                db.cursor.execute(
                    "DELETE FROM app_config WHERE key IN ('SUPABASE_URL', 'SUPABASE_KEY')"
                )
                db.conn.commit()
            except Exception:
                pass
        except Exception as e:
            logger.error(f"Error clearing credentials: {e}")

        # Update UI immediately
        try:
            self._refresh_status()
        except Exception as e:
            logger.error(f"Error refreshing status: {e}")

        # Show confirmation
        InfoBar.success(
            title="Disconnected",
            content="You've been disconnected from Supabase.",
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000,
            parent=self,
        )

        # Defer the supabase client reinitialization to the next event loop tick
        # This prevents crashes from accessing tabs that may not be in a safe state
        QTimer.singleShot(100, self._safe_reinit_supabase)

    def _safe_reinit_supabase(self):
        """Safely disable cloud mode after disconnect.

        Instead of calling the complex _initialize_supabase_client (which
        creates new DBManagers, accesses tab instances, and can segfault),
        we directly disable cloud mode by:
        1. Setting supabase_manager to None
        2. Stopping the remote change monitor
        3. Setting connection mode to local
        4. Updating combo boxes to local mode
        5. Updating loaded tab source displays

        All operations are individually wrapped in try-catch to prevent
        any crash from propagating.
        """
        mw = self.main_window

        # 1. Disable supabase manager
        try:
            mw.supabase_manager = None
            mw._cloud_features_enabled = False
        except Exception:
            pass

        # 2. Stop remote change monitor
        try:
            if hasattr(mw, "_stop_remote_change_monitor"):
                mw._stop_remote_change_monitor()
            if hasattr(mw, "remote_change_monitor") and mw.remote_change_monitor is not None:
                mw.remote_change_monitor = None
        except Exception:
            pass

        # 3. Set connection mode to local
        try:
            if hasattr(mw, "update_coordinator") and mw.update_coordinator:
                mw.update_coordinator.set_connection_mode("local")
        except Exception:
            pass

        # 4. Update combo boxes to local mode
        try:
            if hasattr(mw, "load_history_sources_combo"):
                mw.load_history_sources_combo.setCurrentText("Load from PC (CSV)")
            if hasattr(mw, "load_info_source_combo"):
                mw.load_info_source_combo.setCurrentText("Load from PC (CSV)")
        except Exception:
            pass

        # 5. Update loaded tab source displays
        try:
            if hasattr(mw, "tab_loader") and mw.tab_loader:
                if mw.tab_loader.is_loaded("main") and hasattr(mw, "main_tab_instance"):
                    mw.main_tab_instance.sync_source_button_display()
                if mw.tab_loader.is_loaded("history") and hasattr(mw, "history_tab_instance"):
                    mw.history_tab_instance.sync_source_button_display()
                if mw.tab_loader.is_loaded("rental") and hasattr(mw, "rental_info_tab_instance"):
                    mw.rental_info_tab_instance.load_source_combo.setCurrentText("Local DB")
                    mw.rental_info_tab_instance.sync_source_button_display()
                if mw.tab_loader.is_loaded("archived") and hasattr(mw, "archived_info_tab_instance"):
                    mw.archived_info_tab_instance.load_source_combo.setCurrentText("Local DB")
                    mw.archived_info_tab_instance.sync_source_button_display()
        except Exception:
            pass
