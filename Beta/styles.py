def get_stylesheet():
    return """
        QMainWindow, QWidget {
            background-color: #ECFDF5;
            color: #065F46;
        }
        QTabWidget::pane {
            border: none;
            background-color: white;
            border-radius: 8px;
        }
        QTabBar::tab {
            background-color: #D1FAE5;
            color: #065F46;
            padding: 8px 16px;
            border: none;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        }
        QTabBar::tab:selected {
            background-color: white;
            color: #047857;
        }
        QLineEdit, QSpinBox {
            border: 1px solid #A7F3D0;
            border-radius: 4px;
            padding: 8px;
            background-color: white;
        }
        QLineEdit:focus, QSpinBox:focus {
            border-color: #059669;
        }
        QPushButton {
            background-color: #059669;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 10px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #047857;
        }
        QGroupBox {
            background-color: #F0FDF9;
            border: 1px solid #A7F3D0;
            border-radius: 4px;
            margin-top: 10px;
            font-weight: bold;
            padding: 10px;
        }
        QLabel {
            color: #065F46;
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
        padding: 16px;
        font-size: 24px;
        font-weight: bold;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    """

def get_group_box_style():
    return """
        QGroupBox {
            border: 1px solid #cccccc;
            border-radius: 5px;
            margin-top: 10px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 3px 0 3px;
        }
    """

def get_line_edit_style():
    return """
        QLineEdit {
            border: 1px solid #cccccc;
            border-radius: 3px;
            padding: 5px;
        }
    """

def get_button_style():
    return """
        background-color: #059669;
        color: white;
        border: none;
        border-radius: 4px;
        padding: 10px;
        font-weight: bold;
    """

def get_results_group_style():
    return """
        background-color: #F0FDF9;
        border: 1px solid #A7F3D0;
        border-radius: 4px;
        padding: 10px;
    """

def get_room_group_style():
    return """
        background-color: #F0FDF9;
        border: 1px solid #A7F3D0;
        border-radius: 4px;
        margin: 5px;
        padding: 10px;
    """