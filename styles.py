from utils import resource_path

def get_stylesheet():
    return """
        QMainWindow, QWidget {
            background-color: #ECFDF5;
            color: #065F46;
        }
        QTabWidget::pane {
            border: none;
            background-color: #ECFDF5;
            border-radius: 0px;
        }
        QTabBar::tab {
            background-color: #D1FAE5;
            color: #065F46;
            padding: 10px 18px;
            border: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            font-size: 14px;
            font-weight: bold;
            min-width: 150px;
            max-width: none;
        }
        QTabBar::tab:selected {
            background-color: white;
            color: #059669;
        }
        QTabBar::tab:!selected {
            margin-top: 2px;  /* Adjusted for better visual separation */
            background-color: #ECFDF5;
        }
        QTabWidget::tab-bar {
            alignment: left;
        }
        QLineEdit, QSpinBox {
            border: 1px solid #A7F3D0;
            border-radius: 4px;
            padding: 8px;
            background-color: #F0FDF9;
            font-size: 13px;
        }
        QLineEdit:focus, QSpinBox:focus {
            border: 2px solid #059669;
            background-color: white;
        }
        QPushButton {
            background-color: #059669;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 12px;
            font-weight: bold;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #047857;
        }
        QPushButton:pressed {
            background-color: #065F46;  /* Added pressed state */
        }
        QGroupBox {
            background-color: #F0FDF9;
            border: 1px solid #A7F3D0;
            border-radius: 4px;
            margin-top: 15px;
            font-weight: bold;
            padding: 15px;
            font-size: 14px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            font-size: 16px;
            color: #065F46;
            font-weight: bold;
        }
        QLabel {
            color: #065F46;
            font-size: 13px;
            font-weight: bold;
        }
        QScrollArea, QScrollArea > QWidget > QWidget {
            background-color: transparent;
            border: none;
        }
        QComboBox {
            border: 1px solid #A7F3D0;
            border-radius: 4px;
            padding: 8px;
            background-color: #F0FDF9;
            font-size: 13px;
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 15px;
            border-left-width: 1px;
            border-left-color: #A7F3D0;
            border-left-style: solid;
        }
    """

def get_header_style():
    return """
        background-color: #059669;
        color: white;
        padding: 20px;
        font-size: 28px;
        font-weight: bold;
        border-radius: 0px;
        text-align: center;
        margin-bottom: 10px;
    """

def get_group_box_style():
    return """
        QGroupBox {
            border: 1px solid #A7F3D0;
            border-radius: 4px;
            margin-top: 15px;
            font-weight: bold;
            padding: 15px;
            font-size: 14px;
            background-color: #F0FDF9;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            font-size: 16px;
            color: #065F46;
            font-weight: bold;
        }
        QLabel {
            border: none;
            background-color: transparent;
            padding: 0;
            color: #065F46;
            font-size: 13px;
            font-weight: bold;
        }
    """

def get_month_info_style():
    down_arrow_path = resource_path('icons/down_arrow.png').replace('\\', '/')
    up_arrow_path = resource_path('icons/up_arrow.png').replace('\\', '/')
    return f"""
        QComboBox QAbstractItemView::item:hover {{
            background-color: #E6F7F2;
            color: #059669;
        }}
        QComboBox, QSpinBox {{
            border: 1px solid #059669;
            border-radius: 4px;
            padding: 5px 25px 5px 5px;
            background-color: white;
            font-size: 13px;
            min-width: 150px;
            color: #065F46;
        }}
        QComboBox:focus, QSpinBox:focus {{
            border: 2px solid #059669;
        }}
        QComboBox:hover, QSpinBox:hover {{
            background-color: #F0FDF9;
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left: 1px solid #059669;
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
        }}
        QComboBox::down-arrow {{
            image: url("{down_arrow_path}");
            width: 20px;
            height: 20px;
        }}
        QComboBox QAbstractItemView {{
            border: 1px solid #059669;
            background-color: white;
            selection-background-color: #10B981;
        }}
        QComboBox QAbstractItemView::item {{
            padding: 5px;
            color: #065F46;
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: #059669;
            color: white;
        }}
        QLabel {{
            border: none;
            background-color: transparent;
            padding: 0;
            color: #065F46;
        }}
        QSpinBox::up-button, QSpinBox::down-button {{
            width: 16px;
            border-left: 1px solid #059669;
        }}
        QSpinBox::up-arrow, QSpinBox::down-arrow {{
            width: 12px;
            height: 12px;
        }}
        QSpinBox::up-arrow {{
            image: url("{up_arrow_path}");
        }}
        QSpinBox::down-arrow {{
            image: url("{down_arrow_path}");
        }}
    """

def get_line_edit_style():
    return """
        QLineEdit, QSpinBox {
            border: none;
            border-bottom: 1px solid #A7F3D0;
            border-radius: 0;
            padding: 8px;
            background-color: white;
            font-size: 13px;
            color: #065F46;  /* Added to match text color with other elements */
        }
        QLineEdit:focus, QSpinBox:focus {
            border-bottom: 2px solid #059669;
        }
        QLineEdit:hover, QSpinBox:hover {
            background-color: #F0FDF9;  /* Added for consistency with other hover effects */
        }
        QLineEdit:disabled, QSpinBox:disabled {
            background-color: #E5E7EB;  /* Added disabled state */
            color: #9CA3AF;
        }
    """

def get_button_style():
    return """
        QPushButton {
            background-color: #059669;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 12px;
            font-weight: bold;
            font-size: 14px;
        }
        QPushButton:hover {
            background-color: #047857;
        }
        QPushButton:pressed {
            background-color: #065F46;
        }
        QPushButton:disabled {
            background-color: #A7F3D0;
            color: #D1FAE5;
        }
    """

def get_results_group_style():
    return """
        QGroupBox {
            background-color: #F0FDF9;
            border: 1px solid #A7F3D0;
            border-radius: 4px;
            padding: 15px;
            font-size: 14px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            border: none;
            color: #065F46;
            font-weight: bold;
        }
        QLabel {
            border: none;
            background-color: transparent;
            padding: 5px;
            color: #065F46;
            font-size: 14px;
        }
        QLabel:first-child {
            font-weight: bold;
            font-size: 16px;
        }
    """

def get_room_group_style():
    return """
        QGroupBox {
            background-color: #F0FDF9;
            border: 1px solid #A7F3D0;
            border-radius: 4px;
            margin: 5px;
            padding: 10px;
            font-size: 14px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #065F46;  /* Added color for consistency */
            font-weight: bold;  /* Added for emphasis */
        }
        QLabel {
            border: none;
            background-color: transparent;
            padding: 2px;  /* Added small padding for better readability */
            color: #065F46;
            font-size: 13px;  /* Added for consistency with other styles */
        }
        QLineEdit, QSpinBox {  /* Added styles for input widgets */
            border: 1px solid #A7F3D0;
            border-radius: 3px;
            padding: 4px;
            background-color: white;
        }
        QLineEdit:focus, QSpinBox:focus {
            border-color: #059669;
        }
    """

def get_table_style():
    return """
        QTableWidget {
            gridline-color: #A7F3D0;
            selection-background-color: #34D399;
            border: 1px solid #A7F3D0;
            border-radius: 4px;
        }
        QHeaderView::section {
            background-color: #059669;
            color: white;
            font-weight: bold;
            border: none;
            padding: 8px;
        }
        QTableWidget::item {
            padding: 4px;
        }
        QTableWidget::item:selected {
            color: #FFFFFF;
            background-color: #10B981;
        }
    """

def get_label_style():
    return """
        QLabel {
            color: #065F46;
            font-size: 13px;
            font-weight: bold;
            background-color: transparent;
            border: none;
            padding: 0;
            margin: 2px 0;  /* Add some vertical margin for better spacing */
        }
        QLabel:disabled {
            color: #65A30D;  /* Lighter color for disabled state */
        }
    """