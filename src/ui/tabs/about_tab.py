"""About tab — minimal, clean app information."""

import os
import sys
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from qfluentwidgets import (
    CardWidget, TitleLabel, BodyLabel, CaptionLabel, FluentIcon,
    PushButton, ScrollArea,
)

APP_NAME = "Home Unit Calculator"
APP_VERSION = "6.5.0"
APP_DESCRIPTION = "Calculate and manage home unit consumption, costs, and rental records with cloud sync."
APP_REPO = "https://github.com/Istiaq-Edu/HomeUnitCalculator"

_CARD_BG = "#2b2b2b"
_CARD_BORDER = "#3d3d3d"
_FG = "#ffffff"
_DIM = "#b0b0b0"
_ACCENT = "#4aa8ff"


class AboutTab(QWidget):
    """About tab — app name, version, description, and link."""

    def __init__(self, main_window_ref):
        super().__init__()
        self.main_window = main_window_ref
        self.init_ui()

    def init_ui(self):
        scroll = ScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("ScrollArea { background: transparent; border: none; }")

        content = QWidget()
        content.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        layout.addStretch(1)

        # ─── App icon ───
        icon_label = QLabel()
        icon_label.setFixedSize(64, 64)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("background: transparent; border: none;")
        try:
            from src.core.utils import resource_path
            icon_path = resource_path("icons/icon.png")
            if os.path.exists(icon_path):
                pix = QPixmap(icon_path)
                if not pix.isNull():
                    icon_label.setPixmap(pix.scaled(56, 56, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            pass
        layout.addWidget(icon_label, alignment=Qt.AlignCenter)

        # ─── App name ───
        name = TitleLabel(APP_NAME)
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet(f"color: {_FG}; font-size: 28px; font-weight: bold; background: transparent; border: none;")
        layout.addWidget(name)

        # ─── Version ───
        version = CaptionLabel(f"Version {APP_VERSION}")
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet(f"color: {_DIM}; font-size: 16px; background: transparent; border: none;")
        layout.addWidget(version)

        # ─── Description ───
        desc = BodyLabel(APP_DESCRIPTION)
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {_DIM}; font-size: 15px; background: transparent; border: none; padding: 0 60px;")
        layout.addWidget(desc)

        # ─── GitHub link ───
        github_btn = PushButton("GitHub Repository")
        github_btn.setFixedHeight(38)
        github_btn.setFixedWidth(180)
        github_btn.setStyleSheet(f"""
            PushButton {{
                color: {_ACCENT};
                background-color: rgba(74, 168, 255, 0.1);
                border: 1px solid rgba(74, 168, 255, 0.3);
                border-radius: 6px;
                font-weight: bold;
                padding: 0 20px;
                text-align: center;
            }}
            PushButton:hover {{
                background-color: rgba(74, 168, 255, 0.2);
                border: 1px solid rgba(74, 168, 255, 0.5);
            }}
        """)
        github_btn.clicked.connect(lambda: self._open_url(APP_REPO))
        layout.addWidget(github_btn, alignment=Qt.AlignCenter)

        # ─── Python version (small, bottom) ───
        py_ver = CaptionLabel(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
        py_ver.setAlignment(Qt.AlignCenter)
        py_ver.setStyleSheet(f"color: #777; font-size: 12px; background: transparent; border: none;")
        layout.addWidget(py_ver)

        layout.addStretch(2)

        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _open_url(self, url):
        import webbrowser
        webbrowser.open(url)
