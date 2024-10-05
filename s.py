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
            margin-top: 0px;
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
    """

def get_header_style():
    return """
        background-color: #059669;
        color: white;
        padding: 20px;
        font-size: 28px;
        font-weight: bold;
        border-radius: 0px;
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
        }
    """

def get_month_info_style():
    return """
        QComboBox QAbstractItemView::item:hover {
            background-color: #E6F7F2;
            color: #059669;  /* Green color for text on hover */
        }
        QComboBox, QSpinBox {
            border: 1px solid #059669;
            border-radius: 4px;
            padding: 5px 25px 5px 5px;
            background-color: white;
            font-size: 13px;
            min-width: 150px;
            color: #065F46;
        }
        QComboBox:focus, QSpinBox:focus {
            border: 2px solid #059669;
        }
        QComboBox:hover, QSpinBox:hover {
            background-color: #F0FDF9;
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left: 1px solid #059669;
            border-top-right-radius: 4px;
            border-bottom-right-radius: 4px;
        }
        QComboBox::down-arrow {
            image: url(down_arrow.png);  /* Add this line for custom dropdown arrow */
            width: 12px;  /* Adjust the width of the arrow */
            height: 12px;  /* Adjust the height of the arrow */
        }
        QComboBox QAbstractItemView {
            border: 1px solid #059669;
            background-color: white;
            selection-background-color: #10B981;
        }
        QComboBox QAbstractItemView::item {
            padding: 5px;
            color: #065F46;
        }
        QComboBox QAbstractItemView::item:selected {
            background-color: #059669;
            color: white;
        }
        QLabel {
            border: none;
            background-color: transparent;
            padding: 0;
            color: #065F46;
        }
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
        }
        QLineEdit:focus, QSpinBox:focus {
            border-bottom: 2px solid #059669;
        }
    """

def get_button_style():
    return """
        background-color: #059669;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 12px;
        font-weight: bold;
        font-size: 14px;
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
            padding: 0;
            color: #065F46;
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
        }
        QLabel {
            border: none;
            background-color: transparent;
            padding: 0;
            color: #065F46;
        }
    """