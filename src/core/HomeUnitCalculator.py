import sys
import os

# Add the project root to the sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Suppress QFluentWidgets promotional messages
os.environ["QFLUENTWIDGETS_DISABLE_TIPS"] = "1"

# Optional: Enable startup timing (comment out to disable)
try:
    from src.core.startup_timer import StartupTimer

    StartupTimer.checkpoint("Imports started")
except ImportError:

    class StartupTimer:
        @staticmethod
        def checkpoint(label):
            pass

        @staticmethod
        def finish():
            pass


import logging
from PyQt5.QtCore import Qt, QEvent, QSize, QTimer
from PyQt5.QtGui import QFont, QIcon, QColor, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QMessageBox,
    QDesktopWidget,
    QSizePolicy,
)

# reportlab imports deferred to generate_pdf() for faster startup
import csv
import os
import traceback
from datetime import datetime
from src.core.db_manager import DBManager
from src.core.lazy_tab_loader import LazyTabLoader
from src.core.remote_change_monitor import RemoteChangeMonitor
from src.core.update_coordinator import UpdateCoordinator
from src.core.utils import resource_path
from src.core.utils import get_user_data_dir
from qfluentwidgets import (
    InfoBar,
    InfoBarPosition,
    NavigationInterface,
    NavigationItemPosition,
    setThemeColor,
    FluentIcon,
    setTheme,
    Theme,
    isDarkTheme,
    stacked_widget,
    ComboBox,
    PushButton,
    FluentWindow,
)

# Fluent design toast-like information bars (non-blocking replacements for QMessageBox.information)
try:

    def _non_blocking_information(parent, title, text, *_, **__):  # noqa: D401, ANN001
        """Patched replacement for QMessageBox.information that shows a transient Fluent InfoBar.

        Returns immediately with QMessageBox.Ok so that existing calling code keeps working
        without modifications.
        """
        # Use success style for positive feedback; feel free to tweak orientation/position here
        InfoBar.success(
            title=title,
            content=text,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=3000,  # auto-dismiss after 3 s; negative value means stay until closed
            parent=parent,
        )
        return QMessageBox.Ok

    def _non_blocking_warning(parent, title, text, *_, **__):  # noqa: D401, ANN001
        """Replacement for QMessageBox.warning → yellow InfoBar."""
        InfoBar.warning(
            title=title,
            content=text,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=4000,
            parent=parent,
        )
        return QMessageBox.Ok

    def _non_blocking_critical(parent, title, text, *_, **__):  # noqa: D401, ANN001
        """Replacement for QMessageBox.critical → red InfoBar."""
        InfoBar.error(
            title=title,
            content=text,
            orient=Qt.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=6000,
            parent=parent,
        )
        return QMessageBox.Ok

    # Monkey-patch only if it hasn't been patched yet (to avoid double-patching in tests)
    if not getattr(QMessageBox.information, "__fluent_patched__", False):
        _non_blocking_information.__fluent_patched__ = True  # type: ignore[attr-defined]
        QMessageBox.information = _non_blocking_information  # type: ignore[assignment]

    if not getattr(QMessageBox.warning, "__fluent_patched__", False):
        _non_blocking_warning.__fluent_patched__ = True  # type: ignore[attr-defined]
        QMessageBox.warning = _non_blocking_warning  # type: ignore[assignment]

    if not getattr(QMessageBox.critical, "__fluent_patched__", False):
        _non_blocking_critical.__fluent_patched__ = True  # type: ignore[attr-defined]
        QMessageBox.critical = _non_blocking_critical  # type: ignore[assignment]
except ImportError:
    # If PyQt-Fluent-Widgets isn't installed, fall back silently to the default behaviour.
    pass
# ----------------------------------------------------------------------------------------------


class MeterCalculationApp(FluentWindow):
    def __init__(self):
        StartupTimer.checkpoint("Creating main window")
        super().__init__()

        # Set a modern, cross-platform default font to avoid rendering issues
        # with missing system fonts like MS Shell Dlg 2, which can cause
        # "OpenType support missing" warnings.
        font = QFont("Segoe UI", 9)
        QApplication.setFont(font)

        self.setWindowTitle("Home Unit Calculator")

        # Force update the title bar after setting the title
        if hasattr(self, "titleBar") and hasattr(self.titleBar, "titleLabel"):
            self.titleBar.titleLabel.setText("Home Unit Calculator")

        # Use resize instead of setGeometry to allow flexible positioning
        self.resize(1300, 860)
        # Set minimum size to ensure usability and prevent layout collapse
        self.setMinimumSize(1000, 700)  # Increased minimum size for two-column layout

        # Set dark theme and accent color
        setTheme(Theme.DARK)
        setThemeColor("#0078D4")

        # Patch CardWidget colours to improve dark-theme consistency
        self._patch_cardwidget_dark_style()

        # Apply global dark stylesheet (dialogs, cards, scroll areas, etc.)
        self._apply_global_dark_styles()

        # Force Qt file dialogs to use the non-native variant so QSS styling applies
        self._patch_file_dialog_options()

        # Set window icon early in initialization
        self._set_window_icon_early()

        # Improve title bar text styling and visibility
        self.titleBar.titleLabel.setAlignment(Qt.AlignCenter)
        self.titleBar.titleLabel.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 0px 10px;
            }
        """)

        # Ensure the title bar itself has proper styling and height for larger icon
        self.titleBar.setStyleSheet("""
            TitleBar {
                background-color: #2b2b2b;
                border-bottom: 1px solid #3d3d3d;
                min-height: 40px;
            }
            TitleBar QLabel {
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            TitleBarButton {
                qproperty-normalColor: rgb(255,255,255);
                qproperty-hoverColor: rgb(240,240,240);
                qproperty-pressedColor: rgb(220,220,220);
                padding-top: 6px;
                padding-bottom: 4px;
            }
        """)

        # Set minimum height to accommodate larger icon (32x32 + padding)
        self.titleBar.setMinimumHeight(40)
        # Adjust layout to position buttons on the right and center vertically
        self.titleBar.hBoxLayout.setStretch(1, 0)  # Set title stretch to 0
        spacer = self.titleBar.hBoxLayout.takeAt(2)  # Remove existing spacer if any
        self.titleBar.hBoxLayout.insertStretch(
            2
        )  # Add stretch between title and buttons

        # Vertically center all title bar elements
        self.titleBar.hBoxLayout.setAlignment(self.titleBar.iconLabel, Qt.AlignVCenter)
        self.titleBar.hBoxLayout.setAlignment(self.titleBar.titleLabel, Qt.AlignVCenter)
        self.titleBar.hBoxLayout.setAlignment(self.titleBar.minBtn, Qt.AlignVCenter)
        self.titleBar.hBoxLayout.setAlignment(self.titleBar.maxBtn, Qt.AlignVCenter)
        self.titleBar.hBoxLayout.setAlignment(self.titleBar.closeBtn, Qt.AlignVCenter)

        self.update_coordinator = UpdateCoordinator(self)
        self._setup_global_update_status_area()
        self.update_coordinator.status_changed.connect(self._apply_global_update_status)
        self.update_coordinator.local_change_emitted.connect(self._handle_local_change)
        self.update_coordinator.remote_change_emitted.connect(
            self._handle_remote_change
        )
        self.update_coordinator.set_connection_mode("starting")
        self.remote_change_monitor = None

        self.image_storage_dir = str(get_user_data_dir() / "data" / "images")
        os.makedirs(self.image_storage_dir, exist_ok=True)

        StartupTimer.checkpoint("Initializing database")
        self.db_manager = DBManager()
        self.db_manager.bootstrap_rentals_table()
        self.db_manager.bootstrap_dashboard_cache_tables()
        self.supabase_manager = None
        self._cloud_features_enabled = False

        StartupTimer.checkpoint("Creating UI components")
        self.load_info_source_combo = ComboBox()
        self.load_info_source_combo.addItems(["Load from PC (CSV)", "Load from Cloud"])
        self.load_info_source_combo.setItemIcon(0, FluentIcon.DOCUMENT.icon())
        self.load_info_source_combo.setItemIcon(1, FluentIcon.CLOUD.icon())
        self.load_info_source_combo.setIconSize(QSize(16, 16))
        # Apply custom delegate so icon also appears when combo is closed

        self.load_history_source_combo = ComboBox()
        self.load_history_source_combo.addItems(
            ["Load from PC (CSV)", "Load from Cloud"]
        )
        self.load_history_source_combo.setItemIcon(0, FluentIcon.DOCUMENT.icon())
        self.load_history_source_combo.setItemIcon(1, FluentIcon.CLOUD.icon())
        self.load_history_source_combo.setIconSize(QSize(16, 16))

        StartupTimer.checkpoint("Creating tabs")
        self.tab_loader = LazyTabLoader(self)
        self.tab_loader.register_tab("dashboard", self._create_dashboard_tab)
        self.tab_loader.register_tab("main", self._create_main_tab)
        self.tab_loader.register_tab("rooms", self._create_rooms_tab)
        self.tab_loader.register_tab("history", self._create_history_tab)
        self.tab_loader.register_tab("rental", self._create_rental_tab)
        self.tab_loader.register_tab("archived", self._create_archived_tab)
        self.tab_loader.register_tab("supabase", self._create_supabase_config_tab)

        self._tab_interfaces = {
            "dashboard": self.tab_loader.get_placeholder("dashboard"),
            "main": self.tab_loader.get_placeholder("main"),
            "rooms": self.tab_loader.get_placeholder("rooms"),
            "history": self.tab_loader.get_placeholder("history"),
            "rental": self.tab_loader.get_placeholder("rental"),
            "archived": self.tab_loader.get_placeholder("archived"),
            "supabase": self.tab_loader.get_placeholder("supabase"),
        }
        self._route_to_tab = {}
        self._pending_tab_refreshes = set()

        # Table layout stabilization is now handled directly in the tab files

        StartupTimer.checkpoint("Setting up navigation")
        self.init_navigation()
        self.setup_navigation()
        self.center_window()
        self.refresh_all_rental_tabs()
        QTimer.singleShot(500, self._initialize_supabase_client)

        # Set title bar icon after everything is initialized
        self._set_title_bar_icon()

        # Force icon to be visible
        self._force_icon_visibility()

        # Keyboard navigation can initialize right after the first paint.
        QTimer.singleShot(0, self._initialize_keyboard_navigation)

        StartupTimer.checkpoint("Initialization complete")
        StartupTimer.finish()

    def _initialize_keyboard_navigation(self):
        try:
            from src.ui.keyboard_navigation import KeyboardNavigationManager

            self._kb_nav_manager = KeyboardNavigationManager(self)
        except (
            Exception
        ) as nav_exc:  # pragma: no cover – keep UI alive even if navigation fails
            print(f"Keyboard navigation failed to initialise: {nav_exc}")

    def _setup_global_update_status_area(self):
        self.global_update_status_label = QLabel(self)
        self.global_update_status_label.setObjectName("globalUpdateStatusLabel")
        self.global_update_status_label.setAlignment(Qt.AlignCenter)
        self.global_update_status_label.setSizePolicy(
            QSizePolicy.Maximum, QSizePolicy.Fixed
        )
        self.global_update_status_label.setMinimumWidth(180)
        self.global_update_status_label.setMaximumWidth(260)
        self.titleBar.hBoxLayout.insertWidget(
            2, self.global_update_status_label, 0, Qt.AlignVCenter
        )
        self._apply_global_update_status("Updates: starting", "info")

    def _apply_global_update_status(self, text: str, level: str = "muted"):
        style_map = {
            "success": (
                "#163a27",
                "#4fd38a",
                "#dff7e8",
            ),
            "warning": (
                "#4a3510",
                "#e5b94c",
                "#fff3cf",
            ),
            "info": (
                "#123047",
                "#4aa8ff",
                "#e5f2ff",
            ),
            "muted": (
                "#2f3136",
                "#5b616a",
                "#d8dde4",
            ),
        }
        background, border, foreground = style_map.get(level, style_map["muted"])
        self.global_update_status_label.setText(str(text or "Updates: ready"))
        self.global_update_status_label.setStyleSheet(
            f"""
            QLabel#globalUpdateStatusLabel {{
                background-color: {background};
                border: 1px solid {border};
                border-radius: 10px;
                color: {foreground};
                font-size: 11px;
                font-weight: 600;
                padding: 4px 10px;
                margin: 4px 8px;
            }}
            """
        )

    def _emit_local_change(self, domain: str, action: str, payload=None):
        if hasattr(self, "update_coordinator") and self.update_coordinator is not None:
            self.update_coordinator.emit_local_change(domain, action, payload)
        if getattr(self, "remote_change_monitor", None) is not None:
            self.remote_change_monitor.mark_local_change(domain)

    def _handle_local_change(self, domain: str, action: str, payload):
        domain_key = str(domain or "")
        if domain_key == "rental":
            self._handle_local_rental_change(str(action or ""), payload)
            return

        if domain_key == "main_calculation":
            self._handle_local_main_calculation_change(str(action or ""), payload)

    def _handle_remote_change(self, domain: str, action: str, payload):
        domain_key = str(domain or "")
        if domain_key == "rental":
            self._handle_remote_rental_change(str(action or ""), payload)
            return

        if domain_key in {"main_calculation", "room_calculation"}:
            self._handle_remote_main_calculation_change(str(action or ""), payload)

    def _current_tab_key(self) -> str | None:
        try:
            stacked_widget = object.__getattribute__(self, "stackedWidget")
        except Exception:
            return None
        if stacked_widget is None:
            return None
        current_widget = stacked_widget.currentWidget()
        if current_widget is None:
            return None
        return self._route_to_tab.get(current_widget.objectName())

    def _run_tab_refresh(self, tab_key: str):
        if tab_key == "rental" and self.tab_loader.is_loaded("rental"):
            self.rental_info_tab_instance.load_rental_records(force_refresh=True)
            return

        if tab_key == "archived" and self.tab_loader.is_loaded("archived"):
            self.archived_info_tab_instance.load_archived_records()
            return

        if tab_key == "history" and self.tab_loader.is_loaded("history"):
            if self.load_history_source_combo.currentText() == "Load from Cloud":
                self.history_tab_instance.load_history()

    def _refresh_or_queue_tab(self, tab_key: str):
        if not self.tab_loader.is_loaded(tab_key):
            return

        current_tab_key = self._current_tab_key()
        if current_tab_key is None or current_tab_key == tab_key:
            self._pending_tab_refreshes.discard(tab_key)
            self._run_tab_refresh(tab_key)
        else:
            self._pending_tab_refreshes.add(tab_key)

    def _flush_pending_tab_refresh(self, tab_key: str):
        if tab_key not in self._pending_tab_refreshes:
            return
        self._pending_tab_refreshes.discard(tab_key)
        self._run_tab_refresh(tab_key)

    def _handle_local_rental_change(self, action: str, payload):
        try:
            self._refresh_or_queue_tab("rental")
        except Exception as exc:
            logging.error(
                f"Failed to schedule rental tab refresh after local rental change: {exc}"
            )

        try:
            self._refresh_or_queue_tab("archived")
        except Exception as exc:
            logging.error(
                f"Failed to schedule archived tab refresh after local rental change: {exc}"
            )

        if self.tab_loader.is_loaded("dashboard"):
            try:
                self.dashboard_tab_instance._sync_rentals_cache_async()
            except Exception as exc:
                logging.error(f"Failed to refresh dashboard rental cache: {exc}")

    def _handle_local_main_calculation_change(self, action: str, payload):
        payload = payload if isinstance(payload, dict) else {}
        year = payload.get("year")

        if self.tab_loader.is_loaded("dashboard"):
            try:
                if year is not None:
                    self.dashboard_tab_instance._sync_year_async(int(year))
                    self.dashboard_tab_instance._sync_owner_room_year_async(int(year))
                else:
                    self.dashboard_tab_instance._refresh_years_from_supabase_async()
            except Exception as exc:
                logging.error(
                    f"Failed to refresh dashboard after local calculation change: {exc}"
                )

        if self.tab_loader.is_loaded("history"):
            try:
                self._refresh_or_queue_tab("history")
            except Exception as exc:
                logging.error(
                    f"Failed to refresh history after local calculation change: {exc}"
                )

    def _handle_remote_rental_change(self, action: str, payload):
        if self.tab_loader.is_loaded("rental"):
            try:
                if (
                    self.rental_info_tab_instance.load_source_combo.currentText()
                    == "Cloud (Supabase)"
                ):
                    self._refresh_or_queue_tab("rental")
            except Exception as exc:
                logging.error(
                    f"Failed to schedule rental tab refresh after remote rental change: {exc}"
                )

        if self.tab_loader.is_loaded("archived"):
            try:
                if (
                    self.archived_info_tab_instance.load_source_combo.currentText()
                    == "Cloud (Supabase)"
                ):
                    self._refresh_or_queue_tab("archived")
            except Exception as exc:
                logging.error(
                    f"Failed to schedule archived tab refresh after remote rental change: {exc}"
                )

        if self.tab_loader.is_loaded("dashboard"):
            try:
                self.dashboard_tab_instance._sync_rentals_cache_async()
            except Exception as exc:
                logging.error(
                    f"Failed to refresh dashboard after remote rental change: {exc}"
                )

    def _handle_remote_main_calculation_change(self, action: str, payload):
        if self.tab_loader.is_loaded("dashboard"):
            try:
                self.dashboard_tab_instance._refresh_years_from_supabase_async()
                selected_year = self.dashboard_tab_instance._selected_year()
                if selected_year is not None:
                    self.dashboard_tab_instance._sync_year_async(selected_year)
                owner_year = self.dashboard_tab_instance._selected_owner_room_year()
                if owner_year is not None:
                    self.dashboard_tab_instance._sync_owner_room_year_async(owner_year)
            except Exception as exc:
                logging.error(
                    f"Failed to refresh dashboard after remote calculation change: {exc}"
                )

        if self.tab_loader.is_loaded("history"):
            try:
                self._refresh_or_queue_tab("history")
            except Exception as exc:
                logging.error(
                    f"Failed to refresh history after remote calculation change: {exc}"
                )

    def _start_remote_change_monitor(self):
        if not self._cloud_features_enabled:
            return

        if self.remote_change_monitor is None:
            self.remote_change_monitor = RemoteChangeMonitor(
                self, self.update_coordinator, parent=self
            )
        self.remote_change_monitor.start()

    def _stop_remote_change_monitor(self):
        if self.remote_change_monitor is not None:
            self.remote_change_monitor.stop()

    def _set_title_bar_icon(self):
        """Set a larger title bar icon by directly manipulating the title bar widgets."""
        if not hasattr(self, "titleBar"):
            return

        try:
            # Try multiple possible icon paths. Prefer resource_path so PyInstaller/Nuitka bundles work.
            try:
                possible_icon_paths = [resource_path("icons/icon.png")]
            except Exception:
                possible_icon_paths = [
                    "icons/icon.png",
                    os.path.join(
                        os.path.dirname(__file__), "..", "..", "icons", "icon.png"
                    ),
                    os.path.join(
                        os.path.abspath(os.path.dirname(__file__)),
                        "..",
                        "..",
                        "icons",
                        "icon.png",
                    ),
                ]

            icon_to_use = None
            icon_path_used = None

            # Try to load custom icon first
            for icon_path in possible_icon_paths:
                if os.path.exists(icon_path):
                    pixmap = QPixmap(icon_path)
                    if not pixmap.isNull():
                        icon_to_use = QIcon()
                        # Create larger icon - 28x28 for better visibility
                        icon_to_use.addPixmap(
                            pixmap.scaled(
                                28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation
                            )
                        )
                        icon_path_used = icon_path
                        break

            # Fallback to FluentIcon if custom icon failed
            if icon_to_use is None:
                icon_to_use = FluentIcon.APPLICATION.icon()
                icon_path_used = "FluentIcon.APPLICATION"

            # Set window icon (for taskbar)
            self.setWindowIcon(icon_to_use)

            # Method 1: Try the standard setIcon method
            if hasattr(self.titleBar, "setIcon"):
                self.titleBar.setIcon(icon_to_use)

                # Now make sure the icon label is visible and properly sized
                if hasattr(self.titleBar, "iconLabel"):
                    icon_label = self.titleBar.iconLabel
                    if icon_label:
                        # Make the icon larger and visible
                        larger_pixmap = icon_to_use.pixmap(
                            32, 32
                        )  # Create 32x32 pixmap
                        icon_label.setPixmap(larger_pixmap)
                        icon_label.setFixedSize(36, 36)  # Container size
                        icon_label.setVisible(True)
                        icon_label.show()
                        icon_label.setAlignment(Qt.AlignCenter)
                        icon_label.setStyleSheet("""
                            QLabel {
                                background: transparent;
                                padding: 2px;
                                margin: 2px;
                            }
                        """)
                        return

                # Fallback: find the icon label manually
                for child in self.titleBar.findChildren(QLabel):
                    if (
                        hasattr(child, "pixmap")
                        and child.pixmap()
                        and not child.pixmap().isNull()
                    ):
                        # This is likely the icon label
                        larger_pixmap = icon_to_use.pixmap(32, 32)
                        child.setPixmap(larger_pixmap)
                        child.setFixedSize(36, 36)
                        child.setVisible(True)
                        child.show()
                        child.setAlignment(Qt.AlignCenter)
                        child.setStyleSheet("""
                            QLabel {
                                background: transparent;
                                padding: 2px;
                                margin: 2px;
                            }
                        """)
                        return

            # Method 2: Find and modify icon widgets directly
            icon_set = False

            # Look for existing icon widgets in the title bar
            for child in self.titleBar.findChildren(QLabel):
                # Skip the title label
                if hasattr(child, "text") and child.text() == self.windowTitle():
                    continue

                # Try to set icon on labels that might be icon containers
                if hasattr(child, "setPixmap"):
                    pixmap = icon_to_use.pixmap(28, 28)  # Get 28x28 pixmap
                    child.setPixmap(pixmap)
                    child.setFixedSize(32, 32)  # Slightly larger container
                    child.setAlignment(Qt.AlignCenter)
                    child.setVisible(True)
                    child.show()
                    child.setStyleSheet("""
                        QLabel {
                            background: transparent;
                            padding: 2px;
                            margin: 2px;
                        }
                    """)
                    print(f"Icon set on QLabel: {child.objectName()}")
                    icon_set = True
                    break

            # Method 3: Look for buttons that might hold icons
            if not icon_set:
                for child in self.titleBar.findChildren(QPushButton):
                    # Skip window control buttons (minimize, maximize, close)
                    if any(
                        name in child.objectName().lower()
                        for name in ["min", "max", "close", "restore"]
                    ):
                        continue

                    child.setIcon(icon_to_use)
                    child.setIconSize(QSize(28, 28))
                    child.setFixedSize(36, 36)
                    child.setVisible(True)
                    child.show()
                    child.setStyleSheet("""
                        QPushButton {
                            background: transparent;
                            border: none;
                            padding: 4px;
                            margin: 2px;
                        }
                        QPushButton:hover {
                            background: rgba(255, 255, 255, 0.1);
                            border-radius: 4px;
                        }
                    """)
                    icon_set = True
                    break

        except Exception as e:
            pass

    def _set_window_icon_early(self):
        """Set window icon early in initialization process."""
        try:
            # Load the custom icon, prioritising packaged resources
            icon_path = None
            try:
                icon_path = resource_path("icons/icon.png")
            except Exception:
                # Fall back to relative/absolute search
                for p in (
                    "icons/icon.png",
                    os.path.join(
                        os.path.dirname(__file__), "..", "..", "icons", "icon.png"
                    ),
                    os.path.join(
                        os.path.abspath(os.path.dirname(__file__)),
                        "..",
                        "..",
                        "icons",
                        "icon.png",
                    ),
                ):
                    if os.path.exists(p):
                        icon_path = p
                        break

            if icon_path and os.path.exists(icon_path):
                pixmap = QPixmap(icon_path)
                if not pixmap.isNull():
                    icon = QIcon()
                    icon.addPixmap(
                        pixmap.scaled(
                            32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation
                        )
                    )
                    self.setWindowIcon(icon)
                    return

            # Fallback
            fluent_icon = FluentIcon.APPLICATION.icon()
            self.setWindowIcon(fluent_icon)
        except Exception as e:
            pass

    def _force_icon_visibility(self):
        """Ensure the title bar icon is visible by targeting the specific icon label."""
        if not hasattr(self, "titleBar"):
            return

        try:
            # Method 1: Use the iconLabel property if available
            if hasattr(self.titleBar, "iconLabel"):
                icon_label = self.titleBar.iconLabel
                if icon_label and hasattr(icon_label, "pixmap") and icon_label.pixmap():
                    icon_label.setVisible(True)
                    icon_label.show()
                    icon_label.raise_()
                    # Ensure it has a reasonable size
                    if icon_label.size().width() < 20:
                        icon_label.setFixedSize(36, 36)
                    return

            # Method 2: Find icon labels manually
            for child in self.titleBar.findChildren(QLabel):
                if (
                    hasattr(child, "pixmap")
                    and child.pixmap()
                    and not child.pixmap().isNull()
                ):
                    child.setVisible(True)
                    child.show()
                    child.raise_()
                    # Ensure it has a reasonable size
                    if child.size().width() < 20:
                        child.setFixedSize(36, 36)

        except Exception as e:
            pass

    def _apply_global_dark_styles(self):
        """Apply a single dark stylesheet to the entire QApplication so that
        *all* widgets – including top-level dialogs such as QFileDialog and
        custom QDialog subclasses – inherit a consistent dark appearance.
        """
        from PyQt5.QtWidgets import QApplication

        dark_css = """
        /* Card-like panels with enhanced styling */
        CardWidget {
            background-color: #2b2b2b;
            border: 1px solid #3d3d3d;
            border-radius: 12px;
        }

        /* Explicitly keep the outer unified container static on hover */
        #billing_meter_container {
            background-color: #2b2b2b;
        }
        #billing_meter_container:hover {
            background-color: #2b2b2b;
            border: 1px solid #3d3d3d;
        }
        
        /* Disable interaction for the three section boxes - they should not be clickable */
        #billing_period_box, #reading_pairs_box, #additional_amount_box {
            background: transparent !important;
            border: none !important;
        }
        #billing_period_box:hover, #billing_period_box:pressed,
        #reading_pairs_box:hover, #reading_pairs_box:pressed,
        #additional_amount_box:hover, #additional_amount_box:pressed {
            background: transparent !important;
            border: none !important;
        }

        /* Ensure inner frosted panels do not change colour on hover/press/focus */
        #billing_period_inner, 
        #billing_period_inner:hover, 
        #billing_period_inner:focus, 
        #billing_period_inner:pressed {
            background-color: rgba(255, 255, 255, 0.14) !important;
            border: 1px solid rgba(255, 255, 255, 0.28) !important;
        }
        #reading_pairs_inner, 
        #reading_pairs_inner:hover, 
        #reading_pairs_inner:focus, 
        #reading_pairs_inner:pressed {
            background-color: rgba(255, 255, 255, 0.14) !important;
            border: 1px solid rgba(255, 255, 255, 0.28) !important;
        }
        #additional_amount_inner, 
        #additional_amount_inner:hover, 
        #additional_amount_inner:focus, 
        #additional_amount_inner:pressed {
            background-color: rgba(255, 255, 255, 0.14) !important;
            border: 1px solid rgba(255, 255, 255, 0.28) !important;
        }

        /* Scroll areas should be transparent so underlying card shows */
        ScrollArea {
            background: transparent;
            border: none;
        }

        /* Dialogs / file dialogs */
        QDialog, QFileDialog {
            background-color: #2b2b2b;
            color: #ffffff;
            border-radius: 8px;
        }

        /* Ensure text in dialogs is visible */
        QDialog QLabel, QFileDialog QLabel {
            color: #ffffff;
        }

        /* QLabels default to white for better contrast */
        QLabel {
            color: #ffffff;
        }

        /* Title bar customization */
        TitleBar {
            background-color: #2b2b2b;
            border-bottom: 1px solid #3d3d3d;
        }
        
        TitleBar QLabel {
            color: white !important;
            font-weight: bold;
            font-size: 14px;
            padding: 0px 10px;
        }
        
        FluentWindow > TitleBar > QLabel {
            font-weight: bold;
            font-size: 14px;
            color: white !important;
        }

        /* Enhanced tooltips */
        QToolTip {
            background-color: #3d3d3d;
            color: #ffffff;
            border: 1px solid #5a5a5a;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 12px;
        }

        /* Modern input controls with consistent theming */
        QLineEdit::placeholder {
            color: #888888;
        }

        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
            background-color: #2f2f2f;
            border: 1px solid #555555;
            border-radius: 6px;
            padding: 8px 12px;
            color: #ffffff;
            font-size: 13px;
        }

        QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover {
            border: 1px solid #666666;
            background-color: #353535;
        }

        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
            border: 2px solid #0078D4;
            background-color: #353535;
            outline: none;
        }

        /* Enhanced button styling */
        QPushButton {
            border-radius: 6px;
            padding: 8px 16px;
            font-weight: 600;
        }

        /* Consistent spacing for layouts */
        QVBoxLayout {
            spacing: 12px;
        }

        QHBoxLayout {
            spacing: 8px;
        }

        /* Frame styling for separators */
        QFrame[frameShape="4"] { /* HLine */
            color: #4a4a4a;
            background-color: #4a4a4a;
            border: none;
            height: 1px;
            margin: 8px 0px;
        }
"""

        app = QApplication.instance()
        if app is not None:
            existing = app.styleSheet() or ""
            # Avoid duplicate stylesheet injection
            if dark_css.strip() not in existing:
                app.setStyleSheet(existing + "\n" + dark_css)

    # ----------------------------------------------------------------------
    #                              FILE DIALOGS
    # ----------------------------------------------------------------------
    def _patch_file_dialog_options(self):
        """Force :class:`QFileDialog` static helpers to use the **Qt** variant
        instead of the operating-system native dialog. Native dialogs do not
        respect Qt style-sheets, so they stay bright in dark mode. This shim
        transparently ORs the ``DontUseNativeDialog`` flag for all helpers.
        """
        from PyQt5.QtWidgets import QFileDialog

        if getattr(QFileDialog, "__hmc_patched__", False):
            return  # Already done

        def _wrap_static(method_name):
            original = getattr(QFileDialog, method_name)

            def wrapper(*args, **kwargs):  # type: ignore[override]
                opts = kwargs.get("options", QFileDialog.Options())
                opts |= QFileDialog.DontUseNativeDialog
                kwargs["options"] = opts
                return original(*args, **kwargs)

            setattr(QFileDialog, method_name, staticmethod(wrapper))

        for _m in (
            "getOpenFileName",
            "getOpenFileNames",
            "getSaveFileName",
            "getExistingDirectory",
        ):
            if hasattr(QFileDialog, _m):
                _wrap_static(_m)

        QFileDialog.__hmc_patched__ = True

    # ----------------------------------------------------------------------
    #                       CARDWIDGET COLOUR PATCHING
    # ----------------------------------------------------------------------
    def _patch_cardwidget_dark_style(self):
        """Globally monkey-patch CardWidget colours for dark theme with enhanced styling.

        The default CardWidget background is a semi-transparent white overlay which appears
        too bright against the dark window background. We override the internal colour
        helpers so that every CardWidget (existing and future) uses solid dark greys that
        match the rest of the UI with improved hover effects and animations.
        """
        try:
            from PyQt5.QtGui import QColor
            from PyQt5.QtCore import QPropertyAnimation, QEasingCurve, pyqtProperty
            from qfluentwidgets.components.widgets.card_widget import (
                CardWidget,
                SimpleCardWidget,
                ElevatedCardWidget,
            )

            # Avoid double-patching in case the window is reinstantiated
            if getattr(CardWidget, "__hmc_dark_patched__", False):
                return

            def _normal(self):
                # Give specific boxes a frosted look with semi-transparent white overlay
                try:
                    if hasattr(self, "objectName") and self.objectName() in {
                        "billing_period_box",
                        "reading_pairs_box",
                        "additional_amount_box",
                    }:
                        return QColor(255, 255, 255, 72)  # stronger frosted lightening
                except Exception:
                    pass
                return QColor(43, 43, 43)  # main card fill for others

            def _hover(self):
                # Keep hover static for specific containers (no visual change)
                try:
                    if hasattr(self, "objectName"):
                        if self.objectName() in {
                            "billing_meter_container",
                            "billing_period_box",
                            "reading_pairs_box",
                            "additional_amount_box",
                        }:
                            # Match normal for these containers (frosted or static)
                            if self.objectName() in {
                                "billing_period_box",
                                "reading_pairs_box",
                                "additional_amount_box",
                            }:
                                return QColor(255, 255, 255, 72)
                            return QColor(43, 43, 43)
                except Exception:
                    pass
                return QColor(54, 54, 54)  # slightly lighter on hover for others

            def _pressed(self):
                # Keep pressed identical to normal for frosted boxes (no visual change)
                try:
                    if hasattr(self, "objectName") and self.objectName() in {
                        "billing_period_box",
                        "reading_pairs_box",
                        "additional_amount_box",
                    }:
                        return QColor(255, 255, 255, 72)
                except Exception:
                    pass
                return QColor(37, 37, 37)  # slightly darker on press for others

            # Enhanced card styling with animations
            def _enhanced_enter_event(self, event):
                """Enhanced enter event with subtle animation."""
                # Skip hover behavior for containers that should not react on hover
                # Also skip for any CardWidget inside the Rental Info interface to avoid hover crashes
                try:
                    p = getattr(self, "parent", lambda: None)()
                    while p is not None:
                        if hasattr(p, "objectName") and p.objectName() == "RentalId":
                            event.accept()
                            return
                        p = getattr(p, "parent", lambda: None)()
                except Exception:
                    pass
                try:
                    if hasattr(self, "objectName"):
                        obj_name = self.objectName()
                        # Skip hover for specific containers
                        if obj_name in {
                            "billing_meter_container",
                            "billing_period_box",
                            "reading_pairs_box",
                            "additional_amount_box",
                            "room_selection_card",  # Room tab selector
                        }:
                            event.accept()
                            return
                        # Skip hover for all room containers
                        if obj_name.startswith("room_") and obj_name.endswith("_card"):
                            event.accept()
                            return
                except Exception:
                    pass

                # Call original enter event if it exists
                if hasattr(self.__class__, "_original_enterEvent"):
                    self._original_enterEvent(event)

                # Add subtle scale animation on hover
                if not hasattr(self, "_hover_animation"):
                    self._hover_animation = QPropertyAnimation(self, b"geometry")
                    self._hover_animation.setDuration(150)
                    self._hover_animation.setEasingCurve(QEasingCurve.OutCubic)

                # Subtle elevation effect disabled at global level; individual cards/boxes handle their own hover styling

            def _enhanced_leave_event(self, event):
                """Enhanced leave event to reset styling."""
                # Skip hover behavior for containers that should not react on hover
                # Also skip for any CardWidget inside the Rental Info interface to avoid hover crashes
                try:
                    p = getattr(self, "parent", lambda: None)()
                    while p is not None:
                        if hasattr(p, "objectName") and p.objectName() == "RentalId":
                            event.accept()
                            return
                        p = getattr(p, "parent", lambda: None)()
                except Exception:
                    pass
                try:
                    if hasattr(self, "objectName"):
                        obj_name = self.objectName()
                        # Skip hover for specific containers
                        if obj_name in {
                            "billing_meter_container",
                            "billing_period_box",
                            "reading_pairs_box",
                            "additional_amount_box",
                            "room_selection_card",  # Room tab selector
                        }:
                            event.accept()
                            return
                        # Skip hover for all room containers
                        if obj_name.startswith("room_") and obj_name.endswith("_card"):
                            event.accept()
                            return
                except Exception:
                    pass

                # Call original leave event if it exists
                if hasattr(self.__class__, "_original_leaveEvent"):
                    self._original_leaveEvent(event)

            for _cls in (CardWidget, SimpleCardWidget, ElevatedCardWidget):
                _cls._normalBackgroundColor = _normal  # type: ignore[assignment]
                _cls._hoverBackgroundColor = _hover  # type: ignore[assignment]
                _cls._pressedBackgroundColor = _pressed  # type: ignore[assignment]

                # Store original event handlers if they exist
                if hasattr(_cls, "enterEvent"):
                    _cls._original_enterEvent = _cls.enterEvent
                if hasattr(_cls, "leaveEvent"):
                    _cls._original_leaveEvent = _cls.leaveEvent

                # Apply enhanced event handlers
                _cls.enterEvent = _enhanced_enter_event
                _cls.leaveEvent = _enhanced_leave_event

                _cls.__hmc_dark_patched__ = True
        except Exception as e:
            # Silently continue if patching fails; better to show default than crash
            print(f"Failed to patch CardWidget for dark theme: {e}")

    def check_internet_connectivity(self):
        import socket

        try:
            socket.create_connection(("8.8.8.8", 53), timeout=1)
            return True
        except OSError:
            return False

    def _initialize_supabase_client(self):
        self.update_coordinator.begin_activity(
            "supabase-init", "Updates: initializing cloud"
        )
        # Re-create the SupabaseManager so that it (re)initializes its client
        # internally. This avoids calling its protected methods directly and
        # keeps the encapsulation boundary intact.

        from src.core.supabase_manager import SupabaseManager

        self.supabase_manager = SupabaseManager()
        self._cloud_features_enabled = bool(
            self.supabase_manager.is_client_initialized()
        )

        if self._cloud_features_enabled:
            self.update_coordinator.set_connection_mode("polling")
            self._start_remote_change_monitor()
            # Set default load source to Cloud if Supabase is configured for all tabs
            self.load_history_source_combo.setCurrentText("Load from Cloud")
            self.load_info_source_combo.setCurrentText("Load from Cloud")

            # Sync the button displays to match the combo box selections
            if self.tab_loader.is_loaded("main"):
                self.main_tab_instance.sync_source_button_display()
            if self.tab_loader.is_loaded("history"):
                self.history_tab_instance.sync_source_button_display()
            if self.tab_loader.is_loaded("rental"):
                self.rental_info_tab_instance.load_source_combo.setCurrentText(
                    "Cloud (Supabase)"
                )
                self.rental_info_tab_instance.sync_source_button_display()
            if self.tab_loader.is_loaded("archived"):
                self.archived_info_tab_instance.load_source_combo.setCurrentText(
                    "Cloud (Supabase)"
                )
                self.archived_info_tab_instance.sync_source_button_display()
        else:
            self._stop_remote_change_monitor()
            self.update_coordinator.set_connection_mode("local")
            print("Supabase client not initialized. Cloud features disabled.")
            # If Supabase fails to initialize, ensure source is PC (CSV) / Local DB
            self.load_history_source_combo.setCurrentText("Load from PC (CSV)")
            self.load_info_source_combo.setCurrentText("Load from PC (CSV)")

            # Sync the button displays to match the combo box selections
            if self.tab_loader.is_loaded("main"):
                self.main_tab_instance.sync_source_button_display()
            if self.tab_loader.is_loaded("history"):
                self.history_tab_instance.sync_source_button_display()
            if self.tab_loader.is_loaded("rental"):
                self.rental_info_tab_instance.load_source_combo.setCurrentText(
                    "Local DB"
                )
                self.rental_info_tab_instance.sync_source_button_display()
            if self.tab_loader.is_loaded("archived"):
                self.archived_info_tab_instance.load_source_combo.setCurrentText(
                    "Local DB"
                )
                self.archived_info_tab_instance.sync_source_button_display()

        self.update_coordinator.end_activity("supabase-init")

    def _create_history_tab(self):
        from src.ui.tabs.history_tab import HistoryTab

        return HistoryTab(self)

    def _create_dashboard_tab(self):
        from src.ui.tabs.dashboard_tab import DashboardTab

        return DashboardTab(self)

    def _create_main_tab(self):
        from src.ui.tabs.main_tab import MainTab

        return MainTab(self)

    def _create_rooms_tab(self):
        from src.ui.tabs.rooms_tab import RoomsTab

        return RoomsTab(self.main_tab_instance, self)

    def _create_rental_tab(self):
        from src.ui.tabs.rental_info_tab import RentalInfoTab

        return RentalInfoTab(self)

    def _create_archived_tab(self):
        from src.ui.tabs.archived_info_tab import ArchivedInfoTab

        return ArchivedInfoTab(self)

    def _create_supabase_config_tab(self):
        from src.ui.tabs.supabase_config_tab import SupabaseConfigTab

        return SupabaseConfigTab(self)

    @property
    def dashboard_tab_instance(self):
        return self.tab_loader.get_tab("dashboard")

    @property
    def main_tab_instance(self):
        return self.tab_loader.get_tab("main")

    @property
    def rooms_tab_instance(self):
        return self.tab_loader.get_tab("rooms")

    @property
    def history_tab_instance(self):
        return self.tab_loader.get_tab("history")

    @property
    def rental_info_tab_instance(self):
        return self.tab_loader.get_tab("rental")

    @property
    def archived_info_tab_instance(self):
        return self.tab_loader.get_tab("archived")

    @property
    def supabase_config_tab_instance(self):
        return self.tab_loader.get_tab("supabase")

    def _get_loaded_widget(self, interface_widget):
        if interface_widget is None:
            return None
        loaded = getattr(interface_widget, "_hmc_loaded_widget", None)
        return loaded or interface_widget

    def _mount_lazy_tab(self, tab_key: str, interface_widget):
        if (
            tab_key in {"history", "rental", "archived", "supabase"}
            and self.supabase_manager is None
        ):
            self._initialize_supabase_client()

        tab_widget = self.tab_loader.get_tab(tab_key)
        tab_widget.setObjectName(interface_widget.objectName())

        layout = interface_widget.layout()
        if layout is None:
            layout = QVBoxLayout(interface_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
        else:
            while layout.count():
                item = layout.takeAt(0)
                w = item.widget()
                if w is not None:
                    w.setParent(None)

        layout.addWidget(tab_widget)
        interface_widget._hmc_loaded_widget = tab_widget
        self._apply_cloud_defaults_to_tab(tab_key, tab_widget)
        return tab_widget

    def _apply_cloud_defaults_to_tab(self, tab_key: str, tab_widget):
        if tab_key == "history" and hasattr(tab_widget, "sync_source_button_display"):
            tab_widget.sync_source_button_display()
            return

        if tab_key == "main" and hasattr(tab_widget, "sync_source_button_display"):
            tab_widget.sync_source_button_display()
            return

        if tab_key in {"rental", "archived"} and hasattr(
            tab_widget, "load_source_combo"
        ):
            if self._cloud_features_enabled:
                tab_widget.load_source_combo.setCurrentText("Cloud (Supabase)")
            else:
                tab_widget.load_source_combo.setCurrentText("Local DB")

            if hasattr(tab_widget, "sync_source_button_display"):
                tab_widget.sync_source_button_display()

    def _ensure_interface_loaded(self, interface_widget):
        if interface_widget is None:
            return None

        route_key = interface_widget.objectName()
        tab_key = self._route_to_tab.get(route_key)
        if not tab_key:
            return self._get_loaded_widget(interface_widget)

        if getattr(interface_widget, "_hmc_loaded_widget", None) is not None:
            return interface_widget._hmc_loaded_widget

        if getattr(interface_widget, "_hmc_loading", False):
            return interface_widget

        interface_widget._hmc_loading = True

        def _load():
            try:
                self._mount_lazy_tab(tab_key, interface_widget)
            finally:
                interface_widget._hmc_loading = False
                self.set_focus_on_tab_change(self.stackedWidget.currentIndex())

        QTimer.singleShot(0, _load)
        return interface_widget

    def _ensure_current_interface_loaded(self):
        return self._ensure_interface_loaded(self.stackedWidget.currentWidget())

    def init_navigation(self):
        self._tab_interfaces["dashboard"].setObjectName("DashboardId")
        self._tab_interfaces["main"].setObjectName("CalculatorId")
        self._tab_interfaces["rooms"].setObjectName("RoomsId")
        self._tab_interfaces["history"].setObjectName("HistoryId")
        self._tab_interfaces["rental"].setObjectName("RentalId")
        self._tab_interfaces["archived"].setObjectName("ArchivedId")
        self._tab_interfaces["supabase"].setObjectName("SupabaseId")

        self._route_to_tab = {
            "DashboardId": "dashboard",
            "CalculatorId": "main",
            "RoomsId": "rooms",
            "HistoryId": "history",
            "RentalId": "rental",
            "ArchivedId": "archived",
            "SupabaseId": "supabase",
        }

        # Keep the nav rail narrower so the main content has more usable width
        # without introducing a draggable persisted resize path.
        self.navigationInterface.setMinimumWidth(180)
        self.navigationInterface.setMaximumWidth(220)
        self.navigationInterface.resize(220, self.navigationInterface.height())

        # Enable scroll policy for navigation interface content
        self.navigationInterface.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        self.addSubInterface(
            self._tab_interfaces["dashboard"], FluentIcon.HOME, "Dashboard"
        )
        self.addSubInterface(
            self._tab_interfaces["main"], FluentIcon.EDIT, "Calculator"
        )
        self.addSubInterface(
            self._tab_interfaces["rooms"], FluentIcon.APPLICATION, "Room Calculations"
        )
        self.addSubInterface(
            self._tab_interfaces["history"], FluentIcon.HISTORY, "Calculation History"
        )
        self.addSubInterface(
            self._tab_interfaces["rental"], FluentIcon.PEOPLE, "Rental Info"
        )
        self.addSubInterface(
            self._tab_interfaces["archived"], FluentIcon.DOCUMENT, "Archived Info"
        )
        self.addSubInterface(
            self._tab_interfaces["supabase"],
            FluentIcon.SETTING,
            "Supabase Config",
            position=NavigationItemPosition.BOTTOM,
        )

        # Enable scroll area for navigation items if needed
        self._setup_navigation_scroll_area()

        self.stackedWidget.currentChanged.connect(self.on_current_interface_changed)
        self.navigationInterface.setCurrentItem(
            self._tab_interfaces["dashboard"].objectName()
        )
        QTimer.singleShot(0, self._ensure_current_interface_loaded)

    def _setup_navigation_scroll_area(self):
        """Set up scroll area for navigation interface when tabs exceed available space."""
        try:
            # Find the navigation panel widget and enable scroll area
            from PyQt5.QtWidgets import QScrollArea
            from PyQt5.QtCore import Qt

            # Apply scroll area styling to navigation interface
            self.navigationInterface.setStyleSheet(
                self.navigationInterface.styleSheet()
                + """
                NavigationInterface {
                    background-color: #2b2b2b;
                }
                NavigationInterface QScrollArea {
                    background: transparent;
                    border: none;
                }
                NavigationInterface QScrollBar:vertical {
                    background-color: #3d3d3d;
                    width: 8px;
                    border-radius: 4px;
                    margin: 0px;
                }
                NavigationInterface QScrollBar::handle:vertical {
                    background-color: #5a5a5a;
                    border-radius: 4px;
                    min-height: 20px;
                }
                NavigationInterface QScrollBar::handle:vertical:hover {
                    background-color: #6a6a6a;
                }
                NavigationInterface QScrollBar::add-line:vertical,
                NavigationInterface QScrollBar::sub-line:vertical {
                    height: 0px;
                }
            """
            )
        except Exception as e:
            # Silently continue if scroll area setup fails
            pass

    def on_current_interface_changed(self, index):
        """Handle tab change: set focus appropriately."""
        current_widget = self.stackedWidget.widget(index)
        current_tab_key = (
            self._route_to_tab.get(current_widget.objectName())
            if current_widget is not None
            else None
        )
        resolved_widget = self._ensure_interface_loaded(current_widget)
        active_widget = self._get_loaded_widget(resolved_widget)
        if current_tab_key is not None:
            QTimer.singleShot(
                0, lambda key=current_tab_key: self._flush_pending_tab_refresh(key)
            )
        if hasattr(active_widget, "set_focus_on_tab_change"):
            active_widget.set_focus_on_tab_change()

        # Standard tab switching behavior - table stabilization handled in tab files
        if hasattr(active_widget, "force_table_resize"):
            QTimer.singleShot(150, active_widget.force_table_resize)

        # QFluentWidgets sometimes resets the TitleBar icon to the current page's FluentIcon
        # (e.g., HOME). Re-apply our app icon right after the page switch.
        QTimer.singleShot(0, self._set_title_bar_icon)

    def save_to_pdf(self):
        from src.ui.save_dialog import SaveDialog

        month_name = self.main_tab_instance.month_combo.currentText()
        year_value = self.main_tab_instance.year_spinbox.value()
        default_filename = f"MeterCalculation_{month_name}_{year_value}.pdf"

        def try_save_pdf(path):
            try:
                self.generate_pdf(path)
                QMessageBox.information(self, "PDF Saved", f"Report saved to {path}")
                return True
            except PermissionError:
                QMessageBox.warning(
                    self,
                    "Permission Denied",
                    f"Cannot save to {path}\n\nThe file may be open in another program or you don't have write permission to this location. Please close any programs using this file and try again or select a different location.",
                )
                return False
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "PDF Save Error",
                    f"Failed to save PDF: {e}\n{traceback.format_exc()}",
                )
                return False

        # Use modern file dialog
        file_path = SaveDialog.get_save_filename(
            parent=self,
            title="Save PDF Report",
            default_filename=default_filename,
            file_filter="PDF Files (*.pdf);;All Files (*)",
        )

        if file_path:
            try_save_pdf(file_path)

    def generate_pdf(self, file_path):
        # Import reportlab modules only when generating PDF (deferred for faster startup)
        from reportlab.lib.units import inch
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import (
            SimpleDocTemplate,
            Table,
            TableStyle,
            Paragraph,
            Spacer,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER

        doc = SimpleDocTemplate(
            file_path,
            pagesize=letter,
            topMargin=0.3 * inch,
            bottomMargin=0.3 * inch,
            leftMargin=0.3 * inch,
            rightMargin=0.3 * inch,
        )
        elements = []
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "TitleStyle",
            parent=styles["Heading1"],
            fontSize=16,
            textColor=colors.darkblue,
            spaceAfter=10,
            alignment=TA_CENTER,
        )
        header_style = ParagraphStyle(
            "HeaderStyle",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.darkblue,
            spaceAfter=5,
            alignment=TA_CENTER,
        )
        normal_style = ParagraphStyle(
            "NormalStyle",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.black,
            spaceAfter=2,
        )
        label_style = ParagraphStyle(
            "LabelStyle",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.grey,
            spaceAfter=1,
        )
        bold_number_style = ParagraphStyle(
            "BoldNumberStyle",
            parent=styles["Normal"],
            fontSize=12,
            textColor=colors.black,
            spaceAfter=2,
            fontName="Helvetica-Bold",
        )

        def create_cell(
            content,
            bgcolor=colors.lightsteelblue,
            textcolor=colors.black,
            style=normal_style,
            height=0.2 * inch,
        ):
            if isinstance(content, str):
                content = Paragraph(content, style)
            return Table(
                [[content]],
                colWidths=[7.5 * inch],
                rowHeights=[height],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), bgcolor),
                        ("BOX", (0, 0), (-1, -1), 1, colors.darkblue),
                        ("TEXTCOLOR", (0, 0), (-1, -1), textcolor),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ]
                ),
            )

        elements.append(Paragraph("Meter Calculation Report", title_style))
        elements.append(Spacer(1, 0.1 * inch))
        month_year = f"{self.main_tab_instance.month_combo.currentText()} {self.main_tab_instance.year_spinbox.value()}"
        elements.append(
            create_cell(
                Paragraph(
                    f"Month: <font color='red'>{month_year}</font>", header_style
                ),
                bgcolor=colors.lightsteelblue,
                height=0.3 * inch,
            )
        )
        elements.append(Spacer(1, 0.05 * inch))
        elements.append(
            create_cell(
                "Main Meter Info",
                bgcolor=colors.lightsteelblue,
                textcolor=colors.darkblue,
                style=header_style,
                height=0.3 * inch,
            )
        )

        meter_info_left_data = []
        for i in range(len(self.main_tab_instance.meter_entries)):
            meter_info_left_data.append(
                [
                    Paragraph(f"Meter-{i + 1} Unit:", normal_style),
                    Paragraph(
                        self.main_tab_instance.meter_entries[i].text() or "0",
                        normal_style,
                    ),
                ]
            )
        meter_info_left_data.append(
            [
                Paragraph("Total Difference:", normal_style),
                Paragraph(
                    f"{self.main_tab_instance.total_diff_value_label.text() or 'N/A'}",
                    normal_style,
                ),
            ]
        )

        meter_info_right_data = [
            [
                Paragraph("Per Unit Cost:", normal_style),
                Paragraph(
                    f"{self.main_tab_instance.per_unit_cost_value_label.text() or 'N/A'}",
                    bold_number_style,
                ),
            ],
            [
                Paragraph("Total Unit Cost:", normal_style),
                Paragraph(
                    f"{self.main_tab_instance.total_unit_value_label.text() or 'N/A'} TK",
                    bold_number_style,
                ),
            ],
            [
                Paragraph("Added Amount:", normal_style),
                Paragraph(
                    f"{self.main_tab_instance.additional_amount_value_label.text() or 'N/A'}",
                    normal_style,
                ),
            ],
            [
                Paragraph("In Total Amount:", normal_style),
                Paragraph(
                    f"{self.main_tab_instance.in_total_value_label.text() or 'N/A'}",
                    bold_number_style,
                ),
            ],
        ]

        max_rows = max(len(meter_info_left_data), len(meter_info_right_data))
        while len(meter_info_left_data) < max_rows:
            meter_info_left_data.append(
                [Paragraph("", normal_style), Paragraph("", normal_style)]
            )
        while len(meter_info_right_data) < max_rows:
            meter_info_right_data.append(
                [Paragraph("", normal_style), Paragraph("", normal_style)]
            )

        main_meter_table_data = [
            meter_info_left_data[i] + meter_info_right_data[i] for i in range(max_rows)
        ]
        main_meter_table = Table(
            main_meter_table_data,
            colWidths=[2.5 * inch, 1.25 * inch, 2.5 * inch, 1.25 * inch],
            rowHeights=[0.2 * inch] * max_rows,
        )
        main_meter_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                    ("BOX", (0, 0), (-1, -1), 1, colors.darkblue),
                    ("LINEABOVE", (0, 0), (-1, -1), 1, colors.lightgrey),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        elements.append(main_meter_table)
        elements.append(Spacer(1, 0.1 * inch))

        elements.append(
            create_cell(
                "Room Information",
                bgcolor=colors.lightsteelblue,
                textcolor=colors.darkblue,
                style=header_style,
                height=0.3 * inch,
            )
        )

        room_pdf_data = []
        if self.rooms_tab_instance.room_entries:
            for i in range(0, len(self.rooms_tab_instance.room_entries), 2):
                row = []
                for j in range(2):
                    if i + j < len(self.rooms_tab_instance.room_entries):
                        room_data = self.rooms_tab_instance.room_entries[i + j]

                        real_unit_label = room_data["real_unit_label"]
                        unit_bill_label = room_data["unit_bill_label"]
                        gas_bill_entry = room_data["gas_bill_entry"]
                        water_bill_entry = room_data["water_bill_entry"]
                        house_rent_entry = room_data["house_rent_entry"]
                        grand_total_label = room_data["grand_total_label"]

                        room_group_widget = (
                            self.rooms_tab_instance.rooms_scroll_layout.itemAt(
                                i + j
                            ).widget()
                        )
                        room_name = (
                            room_group_widget.title()
                            if isinstance(room_group_widget, QGroupBox)
                            else f"Room {i + j + 1}"
                        )
                        month_idx = self.main_tab_instance.month_combo.currentIndex()
                        next_month_name = self.main_tab_instance.month_combo.itemText(
                            (month_idx + 1) % 12
                        )

                        room_header_style_pdf = ParagraphStyle(
                            "RoomHeaderStylePdf",
                            parent=styles["Normal"],
                            fontSize=10,
                            textColor=colors.darkblue,
                            spaceAfter=2,
                            fontName="Helvetica-Bold",
                        )
                        bold_unit_bill_style_pdf = ParagraphStyle(
                            "BoldUnitBillStylePdf",
                            parent=styles["Normal"],
                            fontSize=11,
                            textColor=colors.black,
                            spaceAfter=2,
                            fontName="Helvetica-Bold",
                        )
                        header_style_left_pdf = ParagraphStyle(
                            "HeaderStyleLeftPdf",
                            parent=room_header_style_pdf,
                            alignment=0,
                        )
                        header_style_right_gray_pdf = ParagraphStyle(
                            "HeaderStyleRightGrayPdf",
                            parent=room_header_style_pdf,
                            alignment=2,
                            textColor=colors.gray,
                        )

                        header_row_pdf = [
                            Paragraph(f"{room_name}", header_style_left_pdf),
                            Paragraph(
                                f"Created: {next_month_name}",
                                header_style_right_gray_pdf,
                            ),
                        ]

                        room_info_data = [
                            header_row_pdf,
                            [
                                Paragraph("Month:", label_style),
                                Paragraph(month_year, normal_style),
                            ],
                            [
                                Paragraph("Per-Unit Cost:", label_style),
                                Paragraph(
                                    self.main_tab_instance.per_unit_cost_value_label.text()
                                    or "N/A",
                                    normal_style,
                                ),
                            ],
                            [
                                Paragraph("Unit:", label_style),
                                Paragraph(
                                    real_unit_label.text() or "N/A", normal_style
                                ),
                            ],
                            [
                                Paragraph("Unit Bill:", label_style),
                                Paragraph(
                                    unit_bill_label.text() or "N/A",
                                    bold_unit_bill_style_pdf,
                                ),
                            ],
                            [
                                Paragraph("Gas Bill:", label_style),
                                Paragraph(
                                    gas_bill_entry.text() or "0.00", normal_style
                                ),
                            ],
                            [
                                Paragraph("Water Bill:", label_style),
                                Paragraph(
                                    water_bill_entry.text() or "0.00", normal_style
                                ),
                            ],
                            [
                                Paragraph("House Rent:", label_style),
                                Paragraph(
                                    house_rent_entry.text() or "0.00", normal_style
                                ),
                            ],
                            [
                                Paragraph("Grand Total:", label_style),
                                Paragraph(
                                    grand_total_label.text() or "N/A",
                                    bold_unit_bill_style_pdf,
                                ),
                            ],
                        ]
                        room_table_pdf = Table(
                            room_info_data,
                            colWidths=[1.5 * inch, 2.15 * inch],
                            rowHeights=[0.3 * inch] + [0.2 * inch] * 8,
                        )
                        room_table_pdf.setStyle(
                            TableStyle(
                                [
                                    (
                                        "BACKGROUND",
                                        (0, 0),
                                        (-1, 0),
                                        colors.lightsteelblue,
                                    ),
                                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                                    ("BOX", (0, 0), (-1, -1), 1, colors.darkblue),
                                    ("LINEBELOW", (0, 0), (-1, 0), 1, colors.darkblue),
                                    (
                                        "LINEBELOW",
                                        (0, 4),
                                        (-1, 4),
                                        2,
                                        colors.darkblue,
                                    ),  # Thick line below Unit Bill (row 4, 0-indexed)
                                    (
                                        "LINEABOVE",
                                        (0, 1),
                                        (-1, -1),
                                        1,
                                        colors.lightgrey,
                                    ),
                                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                                ]
                            )
                        )
                        row.append(room_table_pdf)
                    else:
                        row.append("")
                room_pdf_data.append(row)
        if room_pdf_data:
            room_table_main = Table(
                room_pdf_data,
                colWidths=[3.85 * inch, 3.85 * inch],
                spaceBefore=0.05 * inch,
            )
            room_table_main.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
            elements.append(room_table_main)

        # Add summary section for all room bills
        if self.rooms_tab_instance.room_entries:
            room_bill_totals = self.rooms_tab_instance.get_all_room_bill_totals()

            elements.append(Spacer(1, 0.1 * inch))
            elements.append(
                create_cell(
                    "Total Room Bills Summary",
                    bgcolor=colors.lightsteelblue,
                    textcolor=colors.darkblue,
                    style=header_style,
                    height=0.3 * inch,
                )
            )

            summary_data = [
                [
                    Paragraph("Total House Rent:", normal_style),
                    Paragraph(
                        f"{room_bill_totals['total_house_rent']:.2f} TK", normal_style
                    ),
                ],
                [
                    Paragraph("Total Water Bill:", normal_style),
                    Paragraph(
                        f"{room_bill_totals['total_water_bill']:.2f} TK", normal_style
                    ),
                ],
                [
                    Paragraph("Total Gas Bill:", normal_style),
                    Paragraph(
                        f"{room_bill_totals['total_gas_bill']:.2f} TK", normal_style
                    ),
                ],
                [
                    Paragraph("Total Room Unit Bill:", normal_style),
                    Paragraph(
                        f"{room_bill_totals['total_room_unit_bill']:.2f} TK",
                        normal_style,
                    ),
                ],
            ]
            summary_table = Table(
                summary_data,
                colWidths=[2.5 * inch, 2.5 * inch],
                rowHeights=[0.2 * inch] * 4,
            )
            summary_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                        ("BOX", (0, 0), (-1, -1), 1, colors.darkblue),
                        ("LINEABOVE", (0, 0), (-1, -1), 1, colors.lightgrey),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ]
                )
            )
            elements.append(summary_table)

            # Add Owner Unit Bill section
            elements.append(Spacer(1, 0.1 * inch))
            elements.append(
                create_cell(
                    "Owner Unit Bill",
                    bgcolor=colors.lightsteelblue,
                    textcolor=colors.darkblue,
                    style=header_style,
                    height=0.3 * inch,
                )
            )

            # Calculate owner unit bill: total unit cost - (total water bill + total room unit bill)
            # Owner pays the full electricity bill, tenants pay their portion (electricity + water pump usage)
            # Owner's portion = Total bill - What tenants pay
            total_unit_cost_text = (
                self.main_tab_instance.total_unit_value_label.text() or "0"
            )
            total_unit_cost = (
                float(total_unit_cost_text.replace("TK", "").strip())
                if total_unit_cost_text != "N/A"
                else 0.0
            )

            owner_unit_bill = total_unit_cost - (
                room_bill_totals["total_water_bill"]
                + room_bill_totals["total_room_unit_bill"]
            )

            owner_data = [
                [
                    Paragraph("Owner Unit Bill:", normal_style),
                    Paragraph(f"{owner_unit_bill:.2f} TK", normal_style),
                ],
            ]
            owner_table = Table(
                owner_data, colWidths=[2.5 * inch, 2.5 * inch], rowHeights=[0.2 * inch]
            )
            owner_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                        ("BOX", (0, 0), (-1, -1), 1, colors.darkblue),
                        ("LINEABOVE", (0, 0), (-1, -1), 1, colors.lightgrey),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 2),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                    ]
                )
            )
            elements.append(owner_table)

        doc.build(elements)

    def save_calculation_to_csv(self):
        month_name = f"{self.main_tab_instance.month_combo.currentText()} {self.main_tab_instance.year_spinbox.value()}"
        filename = "meter_calculation_history.csv"
        meter_texts = [me.text() for me in self.main_tab_instance.meter_entries]
        diff_texts = [de.text() for de in self.main_tab_instance.diff_entries]
        if all(not text for text in meter_texts) and all(
            not text for text in diff_texts
        ):
            QMessageBox.warning(
                self, "Empty Data", "Cannot save empty calculation data."
            )
            return
        try:
            file_exists = os.path.isfile(filename)
            with open(filename, mode="a", newline="") as file:
                writer = csv.writer(file)
                if not file_exists or os.path.getsize(filename) == 0:
                    header = (
                        ["Month"]
                        + [f"Meter-{i + 1}" for i in range(10)]
                        + [f"Diff-{i + 1}" for i in range(10)]
                        + [
                            "Total Unit",
                            "Total Diff",
                            "Per Unit Cost",
                            "Added Amount",
                            "In Total",
                        ]
                        + [
                            "Room Name",
                            "Present Unit",
                            "Previous Unit",
                            "Real Unit",
                            "Unit Bill",
                            "Gas Bill",
                            "Water Bill",
                            "House Rent",
                            "Grand Total",
                            "Total House Rent",
                            "Total Water Bill",
                            "Total Gas Bill",
                            "Total Room Unit Bill",
                        ]
                    )
                    writer.writerow(header)
                main_data_row = [month_name]
                for i in range(10):
                    main_data_row.append(
                        self.main_tab_instance.meter_entries[i].text()
                        if i < len(self.main_tab_instance.meter_entries)
                        and self.main_tab_instance.meter_entries[i].text()
                        else "0"
                    )
                for i in range(10):
                    main_data_row.append(
                        self.main_tab_instance.diff_entries[i].text()
                        if i < len(self.main_tab_instance.diff_entries)
                        and self.main_tab_instance.diff_entries[i].text()
                        else "0"
                    )
                main_data_row.extend(
                    [
                        (
                            self.main_tab_instance.total_unit_value_label.text()
                            .split(":")[-1]
                            .replace("TK", "")
                            .strip()
                            or "0"
                        ),
                        (
                            self.main_tab_instance.total_diff_value_label.text()
                            .split(":")[-1]
                            .replace("TK", "")
                            .strip()
                            or "0"
                        ),
                        (
                            self.main_tab_instance.per_unit_cost_value_label.text()
                            .split(":")[-1]
                            .replace("TK", "")
                            .strip()
                            or "0.00"
                        ),
                        str(self.main_tab_instance.get_additional_amount()),
                        (
                            self.main_tab_instance.in_total_value_label.text()
                            .split(":")[-1]
                            .replace("TK", "")
                            .strip()
                            or "0.00"
                        ),
                    ]
                )
                if (
                    hasattr(self.rooms_tab_instance, "room_entries")
                    and self.rooms_tab_instance.room_entries
                ):
                    for i, room_data in enumerate(self.rooms_tab_instance.room_entries):
                        # Try to get room name from group widget, fallback to generic name
                        try:
                            room_group_widget = self.rooms_tab_instance.rooms_scroll_layout.itemAtPosition(
                                i // 3, i % 3
                            ).widget()
                            room_name = (
                                room_group_widget.title()
                                if isinstance(room_group_widget, QGroupBox)
                                else f"Room {i + 1}"
                            )
                        except:
                            room_name = f"Room {i + 1}"

                        present_text = room_data["present_entry"].text() or "0"
                        previous_text = room_data["previous_entry"].text() or "0"
                        real_unit = (
                            room_data["real_unit_label"].text()
                            if room_data["real_unit_label"].text() != "Incomplete"
                            else "N/A"
                        )
                        unit_bill = (
                            room_data["unit_bill_label"].text().replace(" TK", "")
                            if room_data["unit_bill_label"].text() != "Incomplete"
                            else "N/A"
                        )
                        gas_bill = room_data["gas_bill_entry"].text() or "0.00"
                        water_bill = room_data["water_bill_entry"].text() or "0.00"
                        house_rent = room_data["house_rent_entry"].text() or "0.00"
                        grand_total = (
                            room_data["grand_total_label"].text().replace(" TK", "")
                            if room_data["grand_total_label"].text() != "Incomplete"
                            else "N/A"
                        )

                        room_csv_data_parts = [
                            room_name,
                            present_text,
                            previous_text,
                            real_unit,
                            unit_bill,
                            gas_bill,
                            water_bill,
                            house_rent,
                            grand_total,
                        ]
                        if i == 0:
                            # For the first room, append room data and then the summary totals
                            if hasattr(
                                self.rooms_tab_instance, "get_all_room_bill_totals"
                            ):
                                room_bill_totals = (
                                    self.rooms_tab_instance.get_all_room_bill_totals()
                                )
                                summary_csv_parts = [
                                    f"{room_bill_totals['total_house_rent']:.2f}",
                                    f"{room_bill_totals['total_water_bill']:.2f}",
                                    f"{room_bill_totals['total_gas_bill']:.2f}",
                                    f"{room_bill_totals['total_room_unit_bill']:.2f}",
                                ]
                            else:
                                summary_csv_parts = ["0.00", "0.00", "0.00", "0.00"]
                            writer.writerow(
                                main_data_row + room_csv_data_parts + summary_csv_parts
                            )
                        else:
                            writer.writerow(
                                [""] * len(main_data_row)
                                + room_csv_data_parts
                                + [""] * 4
                            )  # Empty cells for totals in subsequent room rows
                else:
                    writer.writerow(
                        main_data_row + ["N/A"] * 9 + ["0.00"] * 4
                    )  # 9 new fields for rooms + 4 for totals
            QMessageBox.information(
                self, "Save Successful", f"Data saved to {filename}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save data to CSV: {e}\n{traceback.format_exc()}",
            )

    def save_calculation_to_supabase(self):
        from postgrest.exceptions import APIError

        if (
            not self.supabase_manager
            or not self.supabase_manager.is_client_initialized()
            or not self.check_internet_connectivity()
        ):
            QMessageBox.warning(
                self,
                "Supabase Not Configured",
                "Please configure Supabase client in settings or check internet connection.",
            )
            return

        try:
            month = self.main_tab_instance.month_combo.currentText()
            year = self.main_tab_instance.year_spinbox.value()

            # Check for existing record
            existing_record = self.supabase_manager.get_main_calculation_by_month_year(
                month, year
            )
            if existing_record:
                reply = QMessageBox.question(
                    self,
                    "Record Exists",
                    f"A record for {month} {year} already exists. Do you want to overwrite it?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if reply == QMessageBox.No:
                    return

            # Helper function to safely extract numeric values from labels
            def extract_numeric_value(text):
                if not text or text in ["N/A", "Incomplete"]:
                    return 0.0
                # Remove "TK" and other text, keep only numbers and decimal points
                cleaned = text.replace("TK", "").replace(" ", "").strip()
                # Extract only digits and decimal points
                cleaned = "".join(c for c in cleaned if c.isdigit() or c == ".")
                try:
                    return float(cleaned) if cleaned else 0.0
                except ValueError:
                    return 0.0

            # Main calculation data - using field names that match what HistoryTab expects
            meter_readings = {
                f"meter_{i + 1}": int(
                    self.main_tab_instance.meter_entries[i].text() or 0
                )
                for i in range(len(self.main_tab_instance.meter_entries))
            }
            diff_readings = {
                f"diff_{i + 1}": int(self.main_tab_instance.diff_entries[i].text() or 0)
                for i in range(len(self.main_tab_instance.diff_entries))
            }

            main_data = {
                "month": month,
                "year": year,
                "meter_readings": meter_readings,
                "diff_readings": diff_readings,
                "total_unit_cost": extract_numeric_value(
                    self.main_tab_instance.total_unit_value_label.text()
                ),
                "total_diff_units": extract_numeric_value(
                    self.main_tab_instance.total_diff_value_label.text()
                ),
                "per_unit_cost": extract_numeric_value(
                    self.main_tab_instance.per_unit_cost_value_label.text()
                ),
                "added_amount": extract_numeric_value(
                    self.main_tab_instance.additional_amount_value_label.text()
                ),
                "grand_total": extract_numeric_value(
                    self.main_tab_instance.in_total_value_label.text()
                ),
            }

            # Also add individual meter and diff readings as separate fields for HistoryTab compatibility
            main_data.update(meter_readings)
            main_data.update(diff_readings)

            # Save main calculation
            main_calc_id = self.supabase_manager.save_main_calculation(main_data)

            if not main_calc_id:
                QMessageBox.critical(
                    self,
                    "Cloud Save Error",
                    "Failed to save main calculation data. Check console for details.",
                )
                return

            # Room calculation data
            room_data_list = []
            if self.rooms_tab_instance.room_entries:
                for i, room_data in enumerate(self.rooms_tab_instance.room_entries):
                    room_record = {
                        "room_name": f"Room {i + 1}",
                        "present_unit": int(room_data["present_entry"].text() or 0),
                        "previous_unit": int(room_data["previous_entry"].text() or 0),
                        "real_unit": extract_numeric_value(
                            room_data["real_unit_label"].text()
                        ),
                        "unit_bill": extract_numeric_value(
                            room_data["unit_bill_label"].text()
                        ),
                        "gas_bill": float(room_data["gas_bill_entry"].text() or 0),
                        "water_bill": float(room_data["water_bill_entry"].text() or 0),
                        "house_rent": float(room_data["house_rent_entry"].text() or 0),
                        "grand_total": extract_numeric_value(
                            room_data["grand_total_label"].text()
                        ),
                    }
                    room_data_list.append({"room_data": room_record})

            # Save room calculations
            if room_data_list:
                print(f"Debug - Saving {len(room_data_list)} room records...")
                room_save_success = self.supabase_manager.save_room_calculations(
                    main_calc_id, room_data_list
                )
                print(f"Debug - Room save success: {room_save_success}")
                if not room_save_success:
                    QMessageBox.warning(
                        self,
                        "Partial Save",
                        "Main calculation saved, but room data failed to save.",
                    )
                    return
            else:
                print("Debug - No room data to save")

            print("Debug - About to show success message")
            self._emit_local_change(
                "main_calculation",
                "saved",
                {"month": month, "year": year, "main_calc_id": main_calc_id},
            )
            QMessageBox.information(
                self, "Cloud Save", "Data saved to Supabase successfully."
            )

        except APIError as e:
            QMessageBox.critical(
                self, "Supabase API Error", f"An API error occurred: {e}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Cloud Save Error",
                f"Failed to save data to Supabase: {e}\n{traceback.format_exc()}",
            )

    def setup_navigation(self):
        # Connect stacked widget change to focus-management helper
        self.stackedWidget.currentChanged.connect(self.set_focus_on_tab_change)

        # Initialise focus for the first interface
        self.set_focus_on_tab_change(self.stackedWidget.currentIndex())

    def set_focus_on_tab_change(self, index):
        interface_widget = self.stackedWidget.widget(index)
        active_widget = self._get_loaded_widget(interface_widget)
        route_key = (
            interface_widget.objectName() if interface_widget is not None else ""
        )

        if route_key == "CalculatorId" and self.tab_loader.is_loaded("main"):
            self.main_tab_instance.meter_entries[0].setFocus()
            return

        if route_key == "RoomsId" and self.tab_loader.is_loaded("rooms"):
            if getattr(self.rooms_tab_instance, "room_entries", None):
                self.rooms_tab_instance.room_entries[0]["present_entry"].setFocus()
            return

        if route_key == "HistoryId" and self.tab_loader.is_loaded("history"):
            if hasattr(self.history_tab_instance, "main_history_table"):
                self.history_tab_instance.main_history_table.setFocus()
            return

        if route_key == "SupabaseId" and self.tab_loader.is_loaded("supabase"):
            if hasattr(self.supabase_config_tab_instance, "supabase_url_input"):
                self.supabase_config_tab_instance.supabase_url_input.setFocus()
            return

        if route_key == "RentalId" and self.tab_loader.is_loaded("rental"):
            if hasattr(self.rental_info_tab_instance, "rental_records_table"):
                self.rental_info_tab_instance.rental_records_table.setFocus()
            return

        if route_key == "ArchivedId" and self.tab_loader.is_loaded("archived"):
            if hasattr(self.archived_info_tab_instance, "archived_records_table"):
                self.archived_info_tab_instance.archived_records_table.setFocus()
            return

        if hasattr(active_widget, "setFocus"):
            active_widget.setFocus()

    def center_window(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def resizeEvent(self, event):
        """Handle main window resize events and notify tabs with error handling"""
        try:
            super().resizeEvent(event)

            # Validate event
            if event is None:
                # Null resize event received, ignoring
                pass
                return

            # Window resized, notify tabs
            self.notify_tabs_of_resize()

        except Exception as e:
            print(f"[MAIN WINDOW RESIZE ERROR] Error in main window resizeEvent: {e}")
            # Try to continue with basic functionality
            try:
                super().resizeEvent(event)
            except Exception as super_error:
                print(
                    f"[MAIN WINDOW RESIZE ERROR] Failed to call super().resizeEvent: {super_error}"
                )

    def changeEvent(self, event):
        """Handle window state changes (maximize, minimize, restore) with error handling"""
        try:
            super().changeEvent(event)

            # Validate event
            if event is None:
                print("[MAIN WINDOW RESIZE ERROR] Received null change event")
                return

            # Handle window state changes that affect table sizing
            if event.type() == QEvent.WindowStateChange:
                # Longer delay for window state changes as they take more time to complete
                QTimer.singleShot(100, self.notify_tabs_of_resize)

        except Exception as e:
            print(f"[MAIN WINDOW RESIZE ERROR] Error in changeEvent: {e}")
            # Try to continue with basic functionality
            try:
                super().changeEvent(event)
            except Exception as super_error:
                print(
                    f"[MAIN WINDOW RESIZE ERROR] Failed to call super().changeEvent: {super_error}"
                )

    def get_current_tab(self):
        """Get the currently active tab widget"""
        return self._get_loaded_widget(self.stackedWidget.currentWidget())

    def notify_tabs_of_resize(self):
        """Notify current tab about resize events with comprehensive error handling"""
        try:
            current_tab = self.get_current_tab()
            if current_tab is None:
                return

            if hasattr(current_tab, "force_table_resize"):
                try:
                    current_tab.force_table_resize()
                except Exception as resize_error:
                    print(f"[RESIZE ERROR] Failed to resize tables: {resize_error}")

        except Exception as e:
            # Silently ignore resize notification errors
            pass
            # Continue silently to prevent crashes

    def refresh_all_rental_tabs(self):
        """Refresh all rental-related tabs to show updated records."""
        try:
            if self.tab_loader.is_loaded("rental"):
                print("Refreshing rental tabs...")
                self.rental_info_tab_instance.load_rental_records(force_refresh=True)
                print("[OK] Rental Info Tab refreshed")
            if self.tab_loader.is_loaded("archived"):
                print("Refreshing rental tabs...")
                self.archived_info_tab_instance.load_archived_records()
                print("[OK] Archived Info Tab refreshed")
        except Exception as e:
            logging.error(f"Error refreshing rental tabs: {e}")
            print(f"[ERROR] Failed to refresh tabs: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # Set application style for better aesthetics
    app.setStyle("Fusion")
    ex = MeterCalculationApp()
    ex.show()
    sys.exit(app.exec_())
