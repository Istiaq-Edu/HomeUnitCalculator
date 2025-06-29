import sys
import os
# Add the project root to the sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import json
from datetime import datetime as dt_class

import functools
import logging
from PyQt5.QtCore import Qt, QRegExp, QEvent, QPoint, QSize
from PyQt5.QtGui import QFont, QRegExpValidator, QIcon, QColor, QCursor, QKeySequence, QPixmap, QPainter
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QGridLayout, QGroupBox, QFormLayout, QFileDialog,
    QMessageBox, QSpinBox, QScrollArea, QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QShortcut,
    QAbstractSpinBox, QStyleOptionSpinBox, QStyle, QDesktopWidget, QSizePolicy, QDialog, QAbstractItemView
)
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
import csv
import os
import traceback
from postgrest.exceptions import APIError
from datetime import datetime
from src.core.db_manager import DBManager
from src.core.encryption_utils import EncryptionUtil
from src.core.key_manager import get_or_create_key
from src.core.supabase_manager import SupabaseManager # New import
from src.core.utils import resource_path
from src.ui.custom_widgets import CustomLineEdit, AutoScrollArea
from src.ui.tabs.main_tab import MainTab
from src.ui.tabs.rooms_tab import RoomsTab
from src.ui.tabs.history_tab import HistoryTab, EditRecordDialog # EditRecordDialog is imported from history_tab
from src.ui.tabs.supabase_config_tab import SupabaseConfigTab
from src.ui.tabs.rental_info_tab import RentalInfoTab
from src.ui.tabs.archived_info_tab import ArchivedInfoTab
from qfluentwidgets import (
    InfoBar, InfoBarPosition,
    NavigationInterface, NavigationItemPosition, setThemeColor,
    FluentIcon, setTheme, Theme, isDarkTheme,
    stacked_widget, ComboBox, PushButton, FluentWindow
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
        super().__init__()
        self.setWindowTitle("Home Unit Calculator")
        self.setGeometry(100, 100, 1300, 860)

        # Set dark theme and accent color
        setTheme(Theme.DARK)
        setThemeColor('#0078D4')

        # Patch CardWidget colours to improve dark-theme consistency
        self._patch_cardwidget_dark_style()

        # Apply global dark stylesheet (dialogs, cards, scroll areas, etc.)
        self._apply_global_dark_styles()

        # Force Qt file dialogs to use the non-native variant so QSS styling applies
        self._patch_file_dialog_options()

        # Use Fluent icon as window icon for consistency with Fluent design
        self.setWindowIcon(FluentIcon.EDIT.icon())
        

        # Ensure the data/images directory exists
        self.image_storage_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'data', 'images')
        os.makedirs(self.image_storage_dir, exist_ok=True)
        
        self.db_manager = DBManager()
        self.encryption_util = EncryptionUtil()
        self.supabase_manager = SupabaseManager() # Initialize SupabaseManager
        
        self.load_info_source_combo = ComboBox()
        self.load_info_source_combo.addItems(["Load from PC (CSV)", "Load from Cloud"])
        self.load_info_source_combo.setItemIcon(0, FluentIcon.DOCUMENT.icon())
        self.load_info_source_combo.setItemIcon(1, FluentIcon.CLOUD.icon())
        self.load_info_source_combo.setIconSize(QSize(16, 16))
        # Apply custom delegate so icon also appears when combo is closed
        
        
        self.load_history_source_combo = ComboBox()
        self.load_history_source_combo.addItems(["Load from PC (CSV)", "Load from Cloud"])
        self.load_history_source_combo.setItemIcon(0, FluentIcon.DOCUMENT.icon())
        self.load_history_source_combo.setItemIcon(1, FluentIcon.CLOUD.icon())
        self.load_history_source_combo.setIconSize(QSize(16, 16))
        

        self.main_tab_instance = MainTab(self)
        self.rooms_tab_instance = RoomsTab(self.main_tab_instance, self)
        self.history_tab_instance = HistoryTab(self)
        self.supabase_config_tab_instance = SupabaseConfigTab(self)
        self.rental_info_tab_instance = RentalInfoTab(self)
        self.archived_info_tab_instance = ArchivedInfoTab(self)
        
        self._initialize_supabase_client()
        






















        self.init_navigation()
        self.setup_navigation()
        self.center_window()
        self.refresh_all_rental_tabs()

        # Global keyboard shortcuts
        try:
            from src.ui.keyboard_navigation import KeyboardNavigationManager

            self._kb_nav_manager = KeyboardNavigationManager(self)
        except Exception as nav_exc:  # pragma: no cover – keep UI alive even if navigation fails
            print(f"Keyboard navigation failed to initialise: {nav_exc}")

    def _apply_global_dark_styles(self):
        """Apply a single dark stylesheet to the entire QApplication so that
        *all* widgets – including top-level dialogs such as QFileDialog and
        custom QDialog subclasses – inherit a consistent dark appearance.
        """
        from PyQt5.QtWidgets import QApplication

        dark_css = """
        /* Card-like panels */
        CardWidget {
            background-color: #2b2b2b;
            border: 1px solid #3d3d3d;
            border-radius: 8px;
        }

        /* Scroll areas should be transparent so underlying card shows */
        ScrollArea {
            background: transparent;
        }

        /* Dialogs / file dialogs */
        QDialog, QFileDialog {
            background-color: #2b2b2b;
            color: #ffffff;
        }

        /* Ensure text in dialogs is visible */
        QDialog QLabel, QFileDialog QLabel {
            color: #ffffff;
        }

        /* QLabels default to white for better contrast */
        QLabel {
            color: #ffffff;
        }

        /* Tooltips */
        QToolTip {
            background-color: #3d3d3d;
            color: #ffffff;
            border: 1px solid #5a5a5a;
}

/* Modern input controls */
QLineEdit::placeholder {
    color: transparent; /* hide placeholders */
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #2f2f2f;
    border: 1px solid #555555;
    border-radius: 6px;
    padding: 4px;
    color: #ffffff;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #0078D4;
}
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

        for _m in ("getOpenFileName", "getOpenFileNames", "getSaveFileName", "getExistingDirectory"):
            if hasattr(QFileDialog, _m):
                _wrap_static(_m)

        QFileDialog.__hmc_patched__ = True

    # ----------------------------------------------------------------------
    #                       CARDWIDGET COLOUR PATCHING
    # ----------------------------------------------------------------------
    def _patch_cardwidget_dark_style(self):
        """Globally monkey-patch CardWidget colours for dark theme.

        The default CardWidget background is a semi-transparent white overlay which appears
        too bright against the dark window background. We override the internal colour
        helpers so that every CardWidget (existing and future) uses solid dark greys that
        match the rest of the UI. This avoids the need to call setStyleSheet or iterate
        through all card instances manually.
        """
        try:
            from PyQt5.QtGui import QColor
            from qfluentwidgets.components.widgets.card_widget import CardWidget, SimpleCardWidget, ElevatedCardWidget

            # Avoid double-patching in case the window is reinstantiated
            if getattr(CardWidget, '__hmc_dark_patched__', False):
                return

            def _normal(self):
                return QColor(43, 43, 43)  # main card fill

            def _hover(self):
                return QColor(54, 54, 54)  # slightly lighter on hover

            def _pressed(self):
                return QColor(37, 37, 37)  # slightly darker on press

            for _cls in (CardWidget, SimpleCardWidget, ElevatedCardWidget):
                _cls._normalBackgroundColor = _normal  # type: ignore[assignment]
                _cls._hoverBackgroundColor = _hover    # type: ignore[assignment]
                _cls._pressedBackgroundColor = _pressed  # type: ignore[assignment]
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
        # Re-create the SupabaseManager so that it (re)initializes its client
        # internally. This avoids calling its protected methods directly and
        # keeps the encapsulation boundary intact.

        self.supabase_manager = SupabaseManager()
        
        if self.supabase_manager.is_client_initialized():
            # Set default load source to Cloud if Supabase is configured
            self.load_history_source_combo.setCurrentText("Load from Cloud")
        else:
            print("Supabase client not initialized. Cloud features disabled.")
            # If Supabase fails to initialize, ensure source is PC (CSV)
            self.load_history_source_combo.setCurrentText("Load from PC (CSV)")


    def init_navigation(self):
        self.main_tab_instance.setObjectName("MainId")
        self.rooms_tab_instance.setObjectName("RoomsId")
        self.history_tab_instance.setObjectName("HistoryId")
        self.rental_info_tab_instance.setObjectName("RentalId")
        self.archived_info_tab_instance.setObjectName("ArchivedId")
        self.supabase_config_tab_instance.setObjectName("SupabaseId")

        self.addSubInterface(self.main_tab_instance, FluentIcon.HOME, 'Home')
        self.addSubInterface(self.rooms_tab_instance, FluentIcon.APPLICATION, 'Room Calculations')
        self.addSubInterface(self.history_tab_instance, FluentIcon.HISTORY, 'Calculation History')
        self.addSubInterface(self.rental_info_tab_instance, FluentIcon.PEOPLE, 'Rental Info')
        self.addSubInterface(self.archived_info_tab_instance, FluentIcon.DOCUMENT, 'Archived Info')
        self.addSubInterface(self.supabase_config_tab_instance, FluentIcon.SETTING, 'Supabase Config', position=NavigationItemPosition.BOTTOM)
        
        self.stackedWidget.currentChanged.connect(self.on_current_interface_changed)
        self.navigationInterface.setCurrentItem(self.main_tab_instance.objectName())


    def on_current_interface_changed(self, index):
        """Handle tab change: set focus appropriately."""
        current_widget = self.stackedWidget.widget(index)
        if hasattr(current_widget, 'set_focus_on_tab_change'):
            current_widget.set_focus_on_tab_change()


    def save_to_pdf(self):
        month_name = self.main_tab_instance.month_combo.currentText()
        year_value = self.main_tab_instance.year_spinbox.value()
        default_filename = f"MeterCalculation_{month_name}_{year_value}.pdf"
        
        def try_save_pdf(path):
            try:
                self.generate_pdf(path)
                QMessageBox.information(self, "PDF Saved", f"Report saved to {path}")
                return True
            except PermissionError:
                QMessageBox.warning(self, "Permission Denied",
                                  f"Cannot save to {path}\n\nThe file may be open in another program or you don't have write permission to this location. Please close any programs using this file and try again or select a different location.")
                return False
            except Exception as e:
                QMessageBox.critical(self, "PDF Save Error", f"Failed to save PDF: {e}\n{traceback.format_exc()}")
                return False
        
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save PDF", default_filename, "PDF Files (*.pdf);;All Files (*)", options=options)
        if file_path:
            try_save_pdf(file_path)

    def generate_pdf(self, file_path):
        doc = SimpleDocTemplate(file_path, pagesize=letter, topMargin=0.3*inch, bottomMargin=0.3*inch, leftMargin=0.3*inch, rightMargin=0.3*inch)
        elements = []
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.darkblue, spaceAfter=10, alignment=TA_CENTER)
        header_style = ParagraphStyle('HeaderStyle', parent=styles['Heading2'], fontSize=14, textColor=colors.darkblue, spaceAfter=5, alignment=TA_CENTER)
        normal_style = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontSize=10, textColor=colors.black, spaceAfter=2)
        label_style = ParagraphStyle('LabelStyle', parent=styles['Normal'], fontSize=9, textColor=colors.grey, spaceAfter=1)
        bold_number_style = ParagraphStyle('BoldNumberStyle', parent=styles['Normal'], fontSize=12, textColor=colors.black, spaceAfter=2, fontName='Helvetica-Bold')

        def create_cell(content, bgcolor=colors.lightsteelblue, textcolor=colors.black, style=normal_style, height=0.2*inch):
            if isinstance(content, str): content = Paragraph(content, style)
            return Table([[content]], colWidths=[7.5*inch], rowHeights=[height], style=TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), bgcolor), ('BOX', (0,0), (-1,-1), 1, colors.darkblue),
                ('TEXTCOLOR', (0,0), (-1,-1), textcolor), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'), ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6), ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2)]))

        elements.append(Paragraph("Meter Calculation Report", title_style))
        elements.append(Spacer(1, 0.1*inch))
        month_year = f"{self.main_tab_instance.month_combo.currentText()} {self.main_tab_instance.year_spinbox.value()}"
        elements.append(create_cell(Paragraph(f"Month: <font color='red'>{month_year}</font>", header_style), bgcolor=colors.lightsteelblue, height=0.3*inch))
        elements.append(Spacer(1, 0.05*inch))
        elements.append(create_cell("Main Meter Info", bgcolor=colors.lightsteelblue, textcolor=colors.darkblue, style=header_style, height=0.3*inch))
        
        meter_info_left_data = []
        for i in range(len(self.main_tab_instance.meter_entries)):
            meter_info_left_data.append(
                [Paragraph(f"Meter-{i+1} Unit:", normal_style), Paragraph(self.main_tab_instance.meter_entries[i].text() or '0', normal_style)]
            )
        meter_info_left_data.append(
            [Paragraph("Total Difference:", normal_style), Paragraph(f"{self.main_tab_instance.total_diff_value_label.text() or 'N/A'}", normal_style)]
        )
        
        meter_info_right_data = [
            [Paragraph("Per Unit Cost:", normal_style), Paragraph(f"{self.main_tab_instance.per_unit_cost_value_label.text() or 'N/A'}", bold_number_style)],
            [Paragraph("Total Unit Cost:", normal_style), Paragraph(f"{self.main_tab_instance.total_unit_value_label.text() or 'N/A'} TK", bold_number_style)],
            [Paragraph("Added Amount:", normal_style), Paragraph(f"{self.main_tab_instance.additional_amount_value_label.text() or 'N/A'}", normal_style)],
            [Paragraph("In Total Amount:", normal_style), Paragraph(f"{self.main_tab_instance.in_total_value_label.text() or 'N/A'}", bold_number_style)],
        ]

        max_rows = max(len(meter_info_left_data), len(meter_info_right_data))
        while len(meter_info_left_data) < max_rows: meter_info_left_data.append([Paragraph("", normal_style), Paragraph("", normal_style)])
        while len(meter_info_right_data) < max_rows: meter_info_right_data.append([Paragraph("", normal_style), Paragraph("", normal_style)])
        
        main_meter_table_data = [meter_info_left_data[i] + meter_info_right_data[i] for i in range(max_rows)]
        main_meter_table = Table(main_meter_table_data, colWidths=[2.5*inch, 1.25*inch, 2.5*inch, 1.25*inch], rowHeights=[0.2*inch] * max_rows)
        main_meter_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.white), ('BOX', (0,0), (-1,-1), 1, colors.darkblue),
            ('LINEABOVE', (0,0), (-1,-1), 1, colors.lightgrey), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'), ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6), ('TOPPADDING', (0,0), (-1,-1), 2),
            ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ]))
        elements.append(main_meter_table)
        elements.append(Spacer(1, 0.1*inch))

        elements.append(create_cell("Room Information", bgcolor=colors.lightsteelblue, textcolor=colors.darkblue, style=header_style, height=0.3*inch))
        
        room_pdf_data = []
        if self.rooms_tab_instance.room_entries:
            for i in range(0, len(self.rooms_tab_instance.room_entries), 2):
                row = []
                for j in range(2):
                    if i + j < len(self.rooms_tab_instance.room_entries):
                        room_data = self.rooms_tab_instance.room_entries[i+j]
                        
                        real_unit_label = room_data['real_unit_label']
                        unit_bill_label = room_data['unit_bill_label']
                        gas_bill_entry = room_data['gas_bill_entry']
                        water_bill_entry = room_data['water_bill_entry']
                        house_rent_entry = room_data['house_rent_entry']
                        grand_total_label = room_data['grand_total_label']

                        room_group_widget = self.rooms_tab_instance.rooms_scroll_layout.itemAtPosition((i+j)//3, (i+j)%3).widget()
                        room_name = room_group_widget.title() if isinstance(room_group_widget, QGroupBox) else f"Room {i+j+1}"
                        month_idx = self.main_tab_instance.month_combo.currentIndex()
                        next_month_name = self.main_tab_instance.month_combo.itemText((month_idx + 1) % 12)
                        
                        room_header_style_pdf = ParagraphStyle('RoomHeaderStylePdf', parent=styles['Normal'], fontSize=10, textColor=colors.darkblue, spaceAfter=2, fontName='Helvetica-Bold')
                        bold_unit_bill_style_pdf = ParagraphStyle('BoldUnitBillStylePdf', parent=styles['Normal'], fontSize=11, textColor=colors.black, spaceAfter=2, fontName='Helvetica-Bold')
                        header_style_left_pdf = ParagraphStyle('HeaderStyleLeftPdf', parent=room_header_style_pdf, alignment=0)
                        header_style_right_gray_pdf = ParagraphStyle('HeaderStyleRightGrayPdf', parent=room_header_style_pdf, alignment=2, textColor=colors.gray)
 
                        header_row_pdf = [Paragraph(f"{room_name}", header_style_left_pdf), Paragraph(f"Created: {next_month_name}", header_style_right_gray_pdf)]

                        room_info_data = [ header_row_pdf,
                            [Paragraph("Month:", label_style), Paragraph(month_year, normal_style)],
                            [Paragraph("Per-Unit Cost:", label_style), Paragraph(self.main_tab_instance.per_unit_cost_value_label.text() or 'N/A', normal_style)],
                            [Paragraph("Unit:", label_style), Paragraph(real_unit_label.text() or 'N/A', normal_style)],
                            [Paragraph("Unit Bill:", label_style), Paragraph(unit_bill_label.text() or 'N/A', bold_unit_bill_style_pdf)],
                            [Paragraph("Gas Bill:", label_style), Paragraph(gas_bill_entry.text() or '0.00', normal_style)],
                            [Paragraph("Water Bill:", label_style), Paragraph(water_bill_entry.text() or '0.00', normal_style)],
                            [Paragraph("House Rent:", label_style), Paragraph(house_rent_entry.text() or '0.00', normal_style)],
                            [Paragraph("Grand Total:", label_style), Paragraph(grand_total_label.text() or 'N/A', bold_unit_bill_style_pdf)]]
                        room_table_pdf = Table(room_info_data, colWidths=[1.5*inch, 2.15*inch], rowHeights=[0.3*inch] + [0.2*inch]*8)
                        room_table_pdf.setStyle(TableStyle([
                            ('BACKGROUND', (0,0), (-1,0), colors.lightsteelblue), ('BACKGROUND', (0,1), (-1,-1), colors.white),
                            ('BOX', (0,0), (-1,-1), 1, colors.darkblue), ('LINEBELOW', (0,0), (-1,0), 1, colors.darkblue),
                            ('LINEBELOW', (0,4), (-1,4), 2, colors.darkblue), # Thick line below Unit Bill (row 4, 0-indexed)
                            ('LINEABOVE', (0,1), (-1,-1), 1, colors.lightgrey), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                            ('ALIGN', (0,0), (-1,-1), 'LEFT'), ('LEFTPADDING', (0,0), (-1,-1), 6),
                            ('RIGHTPADDING', (0,0), (-1,-1), 6), ('TOPPADDING', (0,0), (-1,-1), 2),
                            ('BOTTOMPADDING', (0,0), (-1,-1), 2)]))
                        row.append(room_table_pdf)
                    else: row.append("")
                room_pdf_data.append(row)
        if room_pdf_data:
            room_table_main = Table(room_pdf_data, colWidths=[3.85*inch, 3.85*inch], spaceBefore=0.05*inch)
            room_table_main.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
            elements.append(room_table_main)
        
        # Add summary section for all room bills
        if self.rooms_tab_instance.room_entries:
            room_bill_totals = self.rooms_tab_instance.get_all_room_bill_totals()
            
            elements.append(Spacer(1, 0.1*inch))
            elements.append(create_cell("Total Room Bills Summary", bgcolor=colors.lightsteelblue, textcolor=colors.darkblue, style=header_style, height=0.3*inch))
            
            summary_data = [
                [Paragraph("Total House Rent:", normal_style), Paragraph(f"{room_bill_totals['total_house_rent']:.2f} TK", normal_style)],
                [Paragraph("Total Water Bill:", normal_style), Paragraph(f"{room_bill_totals['total_water_bill']:.2f} TK", normal_style)],
                [Paragraph("Total Gas Bill:", normal_style), Paragraph(f"{room_bill_totals['total_gas_bill']:.2f} TK", normal_style)],
                [Paragraph("Total Room Unit Bill:", normal_style), Paragraph(f"{room_bill_totals['total_room_unit_bill']:.2f} TK", normal_style)],
            ]
            summary_table = Table(summary_data, colWidths=[2.5*inch, 2.5*inch], rowHeights=[0.2*inch]*4)
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.white), ('BOX', (0,0), (-1,-1), 1, colors.darkblue),
                ('LINEABOVE', (0,0), (-1,-1), 1, colors.lightgrey), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'), ('LEFTPADDING', (0,0), (-1,-1), 6),
                ('RIGHTPADDING', (0,0), (-1,-1), 6), ('TOPPADDING', (0,0), (-1,-1), 2),
                ('BOTTOMPADDING', (0,0), (-1,-1), 2),
            ]))
            elements.append(summary_table)

        doc.build(elements)

    def save_calculation_to_csv(self):
        month_name = f"{self.main_tab_instance.month_combo.currentText()} {self.main_tab_instance.year_spinbox.value()}"
        filename = "meter_calculation_history.csv"
        meter_texts = [me.text() for me in self.main_tab_instance.meter_entries]
        diff_texts = [de.text() for de in self.main_tab_instance.diff_entries]
        if all(not text for text in meter_texts) and all(not text for text in diff_texts):
             QMessageBox.warning(self, "Empty Data", "Cannot save empty calculation data.")
             return
        try:
            file_exists = os.path.isfile(filename)
            with open(filename, mode='a', newline='') as file:
                writer = csv.writer(file)
                if not file_exists or os.path.getsize(filename) == 0:
                    header = ["Month"] + [f"Meter-{i+1}" for i in range(10)] + \
                                [f"Diff-{i+1}" for i in range(10)] + \
                                ["Total-Unit-Cost", "Total-Diffs", "Per-Unit-Cost", "Added-Amount", "Grand-Total"]
                    writer.writerow(header)
                
                row_data = [month_name] + meter_texts + diff_texts + \
                           [self.main_tab_instance.total_unit_value_label.text(), self.main_tab_instance.total_diff_value_label.text(), 
                            self.main_tab_instance.per_unit_cost_value_label.text(), self.main_tab_instance.additional_amount_value_label.text(), 
                            self.main_tab_instance.in_total_value_label.text()]
                writer.writerow(row_data)

            QMessageBox.information(self, "CSV Saved", f"Calculation history saved to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "CSV Save Error", f"Failed to save CSV: {e}\n{traceback.format_exc()}")

    def save_calculation_to_supabase(self):
        if not self.supabase_manager.is_client_initialized() or not self.check_internet_connectivity():
            QMessageBox.warning(self, "Supabase Not Configured", "Please configure Supabase client in settings or check internet connection.")
            return
        
        try:
            month = f"{self.main_tab_instance.month_combo.currentText()} {self.main_tab_instance.year_spinbox.value()}"
            
            # Check for existing record
            if self.supabase_manager.record_exists('calculations', month):
                reply = QMessageBox.question(self, 'Record Exists', 
                                             f"A record for {month} already exists. Do you want to overwrite it?",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.No:
                    return

            # Main calculation data
            main_data = {
                'month': month,
                'meter_readings': {f'meter_{i+1}': float(self.main_tab_instance.meter_entries[i].text() or 0) for i in range(len(self.main_tab_instance.meter_entries))},
                'diff_readings': {f'diff_{i+1}': float(self.main_tab_instance.diff_entries[i].text() or 0) for i in range(len(self.main_tab_instance.diff_entries))},
                'total_unit_cost': float(self.main_tab_instance.total_unit_value_label.text() or 0),
                'total_diffs': float(self.main_tab_instance.total_diff_value_label.text() or 0),
                'per_unit_cost': float(self.main_tab_instance.per_unit_cost_value_label.text() or 0),
                'added_amount': float(self.main_tab_instance.additional_amount_value_label.text() or 0),
                'grand_total': float(self.main_tab_instance.in_total_value_label.text() or 0)
            }

            if self.supabase_manager.record_exists('calculations', month):
                self.supabase_manager.update_record('calculations', month, main_data)
            else:
                self.supabase_manager.insert_record('calculations', main_data)

            # Room calculation data
            if self.rooms_tab_instance.room_entries:
                for i, room_data in enumerate(self.rooms_tab_instance.room_entries):
                    room_name = f"Room {i+1}"
                    room_record = {
                        'month': month,
                        'room_number': room_name,
                        'present_reading': float(room_data['present_entry'].text() or 0),
                        'previous_reading': float(room_data['previous_entry'].text() or 0),
                        'real_unit': float(room_data['real_unit_label'].text() or 0),
                        'unit_bill': float(room_data['unit_bill_label'].text() or 0),
                        'gas_bill': float(room_data['gas_bill_entry'].text() or 0),
                        'water_bill': float(room_data['water_bill_entry'].text() or 0),
                        'house_rent': float(room_data['house_rent_entry'].text() or 0),
                        'grand_total': float(room_data['grand_total_label'].text() or 0)
                    }

                    if self.supabase_manager.record_exists('rooms', month, room_name):
                        self.supabase_manager.update_room_record('rooms', month, room_name, room_record)
                    else:
                        self.supabase_manager.insert_record('rooms', room_record)

            QMessageBox.information(self, "Cloud Save", "Data saved to Supabase successfully.")

        except APIError as e:
            QMessageBox.critical(self, "Supabase API Error", f"An API error occurred: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Cloud Save Error", f"Failed to save data to Supabase: {e}\n{traceback.format_exc()}")

    def setup_navigation(self):
        # Connect stacked widget change to focus-management helper
        self.stackedWidget.currentChanged.connect(self.set_focus_on_tab_change)

        # Initialise focus for the first interface
        self.set_focus_on_tab_change(self.stackedWidget.currentIndex())

    def set_focus_on_tab_change(self, index):
        current_tab = self.stackedWidget.widget(index)
        if isinstance(current_tab, MainTab):
            self.main_tab_instance.meter_entries[0].setFocus()
        elif isinstance(current_tab, RoomsTab):
            if self.rooms_tab_instance.room_entries:
                self.rooms_tab_instance.room_entries[0]['present_entry'].setFocus()
        elif isinstance(current_tab, HistoryTab):
            self.history_tab_instance.main_history_table.setFocus()
        elif isinstance(current_tab, SupabaseConfigTab):
            self.supabase_config_tab_instance.supabase_url_input.setFocus()
        elif isinstance(current_tab, RentalInfoTab):
            self.rental_info_tab_instance.rental_records_table.setFocus()
        elif isinstance(current_tab, ArchivedInfoTab):
            self.archived_info_tab_instance.archived_records_table.setFocus()

    def center_window(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def refresh_all_rental_tabs(self):
        # This method will be called when rental info is updated
        # It should trigger a refresh in all tabs that display rental info
        # For now, it only refreshes the HistoryTab
        try:
            self.rental_info_tab_instance.load_rental_records()
            self.archived_info_tab_instance.load_archived_records()
        except Exception as e:
            logging.error(f"Error refreshing rental tabs: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Set application style for better aesthetics
    app.setStyle("Fusion") 
    ex = MeterCalculationApp()
    ex.show()
    sys.exit(app.exec_())
