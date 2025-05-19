# Import the resource_path function from the utils module
from utils import resource_path

def get_stylesheet():
    # Return a multi-line string containing CSS-like styling for the application
    return """
        /* Set the background color and text color for the main window and widgets */
        QMainWindow, QWidget {
            background-color: #EFF6FF;  /* Very light blue background */
            color: #1E3A8A;  /* Dark blue text color */
        }
        
        /* Style the pane of the tab widget */
        QTabWidget::pane {
            border: none;  /* Remove border */
            background-color: #EFF6FF;  /* Very light blue background */
            border-radius: 0px;  /* No rounded corners */
        }
        
        /* Style individual tabs */
        QTabBar::tab {
            background-color: #DBEAFE;  /* Light blue for unselected tabs */
            color: #1E3A8A;  /* Dark blue text */
            padding: 8px 15px;  /* Reduced padding */
            border: none;  /* No border */
            border-top-left-radius: 8px;  /* Rounded top-left corner */
            border-top-right-radius: 8px;  /* Rounded top-right corner */
            font-size: 14px;  /* Text size */
            font-weight: bold;  /* Bold text */
            min-width: 150px;  /* Minimum width of tabs */
            max-width: none;  /* No maximum width */
        }
        
        /* Style for the selected tab */
        QTabBar::tab:selected {
            background-color: white;  /* White background for selected tab */
            color: #3B82F6;  /* Medium blue text for selected tab */
        }
        
        /* Style for unselected tabs */
        QTabBar::tab:!selected {
            margin-top: 2px;  /* Small top margin for unselected tabs */
            background-color: #EFF6FF;  /* Same as main background */
        }
        
        /* Align the tab bar to the left */
        QTabWidget::tab-bar {
            alignment: left;
        }
        
        /* Style for line edits and spin boxes */
        QLineEdit, QSpinBox {
            border: 1px solid #93C5FD;  /* Lighter medium blue border */
            border-radius: 4px;  /* Slightly rounded corners */
            padding: 8px;  /* Internal padding */
            background-color: #E0F2FE;  /* Light blue variant background */
            font-size: 13px;  /* Text size */
        }
        
        /* Style for focused line edits and spin boxes */
        QLineEdit:focus, QSpinBox:focus {
            border: 2px solid #3B82F6;  /* Thicker, medium blue border when focused */
            background-color: white;  /* White background when focused */
        }
        
        /* Default style for push buttons */
        QPushButton {
            background-color: #3B82F6;  /* Medium blue background */
            color: white;  /* White text */
            border: none;  /* No border */
            border-radius: 4px;  /* Rounded corners */
            padding: 10px;  /* Reduced internal padding */
            font-weight: bold;  /* Bold text */
            font-size: 14px;  /* Text size */
        }
        
        /* Style for hovered push buttons */
        QPushButton:hover {
            background-color: #2563EB;  /* Darker medium blue on hover */
        }
        
        /* Style for pressed push buttons */
        QPushButton:pressed {
            background-color: #1D4ED8;  /* Even darker blue when pressed */
        }

        /* Specific button styles */
        QPushButton#savePdfButton {
            background-color: #EF4444; /* Red */
        }
        QPushButton#savePdfButton:hover {
            background-color: #DC2626; /* Darker Red */
        }
        QPushButton#savePdfButton:pressed {
            background-color: #B91C1C; /* Even Darker Red */
        }

        QPushButton#saveCsvButton {
            background-color: #3B82F6; /* Blue (already default, but explicit) */
        }
        QPushButton#saveCsvButton:hover {
            background-color: #2563EB; /* Darker Blue */
        }
        QPushButton#saveCsvButton:pressed {
            background-color: #1D4ED8; /* Even Darker Blue */
        }

        QPushButton#saveCloudButton {
            background-color: #059669; /* Green */
        }
        QPushButton#saveCloudButton:hover {
            background-color: #047857; /* Darker Green */
        }
        QPushButton#saveCloudButton:pressed {
            background-color: #065F46; /* Even Darker Green */
        }
        
        /* Style for group boxes */
        QGroupBox {
            background-color: #E0F2FE;  /* Light blue variant background */
            border: 1px solid #93C5FD;  /* Lighter medium blue border */
            border-radius: 4px;  /* Rounded corners */
            margin-top: 10px;  /* Reduced top margin */
            font-weight: bold;  /* Bold text */
            padding: 10px;  /* Reduced internal padding */
            font-size: 14px;  /* Text size */
        }
        
        /* Style for group box titles */
        QGroupBox::title {
            subcontrol-origin: margin;  /* Position relative to the margin */
            left: 10px;  /* Left position */
            padding: 0 5px 0 5px;  /* Horizontal padding */
            font-size: 16px;  /* Title text size */
            color: #1E3A8A;  /* Dark blue text */
            font-weight: bold;  /* Bold text */
        }
        
        /* Style for labels */
        QLabel {
            color: #1E3A8A;  /* Dark blue text */
            font-size: 13px;  /* Text size */
            font-weight: bold;  /* Bold text */
        }
        
        /* Style for scroll areas */
        QScrollArea, QScrollArea > QWidget > QWidget {
            background-color: transparent;  /* Transparent background */
            border: none;  /* No border */
        }
        
        /* Style for combo boxes */
        QComboBox {
            border: 1px solid #93C5FD;  /* Lighter medium blue border */
            border-radius: 4px;  /* Rounded corners */
            padding: 8px;  /* Internal padding */
            background-color: #E0F2FE;  /* Light blue variant background */
            font-size: 13px;  /* Text size */
        }
        
        /* Style for combo box drop-down button */
        QComboBox::drop-down {
            subcontrol-origin: padding;  /* Position relative to padding */
            subcontrol-position: top right;  /* Position at top right */
            width: 15px;  /* Width of drop-down button */
            border-left-width: 1px;  /* Left border width */
            border-left-color: #93C5FD;  /* Left border color */
            border-left-style: solid;  /* Solid left border */
        }
        
        /* Modernized scrollbar styles */
        QScrollBar:vertical {
            border: none;
            background: #E0F2FE; /* Light blue variant */
            width: 10px;
            margin: 0px 0px 0px 0px;
        }
        QScrollBar::handle:vertical {
            background: #93C5FD; /* Lighter medium blue */
            min-height: 20px;
            border-radius: 5px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
            background: none;
        }
        
        QScrollBar:horizontal {
            border: none;
            background: #E0F2FE; /* Light blue variant */
            height: 10px;
            margin: 0px 0px 0px 0px;
        }
        QScrollBar::handle:horizontal {
            background: #93C5FD; /* Lighter medium blue */
            min-width: 20px;
            border-radius: 5px;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
            background: none;
        }
    """

def get_header_style():
    return """
        background-color: #3B82F6;  /* Medium blue background */
        color: white;  /* Set the text color to white for contrast */
        padding: 15px;  /* Reduced padding from 20px */
        font-size: 24px;  /* Reduced font size from 28px */
        font-weight: bold;  /* Make the text bold */
        border-radius: 0px;  /* Remove any rounded corners */
        text-align: center;  /* Center-align the text */
        margin-bottom: 10px;  /* Add 10 pixels of margin at the bottom */
    """

def get_group_box_style():
    return """
        QGroupBox {
            border: 1px solid #93C5FD;  /* Lighter medium blue border */
            border-radius: 4px;  /* Round the corners with a 4-pixel radius */
            margin-top: 10px;  /* Reduced margin at the top */
            font-weight: bold;  /* Make the text bold */
            padding: 10px;  /* Reduced padding inside the group box */
            font-size: 14px;  /* Set the font size to 14 pixels */
            background-color: #E0F2FE;  /* Light blue variant background */
        }
        QGroupBox::title {
            subcontrol-origin: margin;  /* Position the title relative to the margin */
            left: 10px;  /* Move the title 10 pixels from the left */
            padding: 0 5px 0 5px;  /* Add horizontal padding to the title */
            font-size: 16px;  /* Set the title font size to 16 pixels */
            color: #1E3A8A;  /* Dark blue text */
            font-weight: bold;  /* Make the title text bold */
        }
        QLabel {
            border: none;  /* Remove any border from labels */
            background-color: transparent;  /* Make the label background transparent */
            padding: 0;  /* Remove any padding from labels */
            color: #1E3A8A;  /* Dark blue text */
            font-size: 13px;  /* Set the label font size to 13 pixels */
            font-weight: bold;  /* Make the label text bold */
        }
    """

def get_month_info_style():
    # Get the file paths for the down and up arrow icons, replacing backslashes with forward slashes
    down_arrow_path = resource_path('icons/down_arrow.png').replace('\\', '/')
    up_arrow_path = resource_path('icons/up_arrow.png').replace('\\', '/')
    
    return f"""
        /* Style for when hovering over items in the QComboBox dropdown */
        QComboBox QAbstractItemView::item:hover {{
            background-color: #DBEAFE;  /* Light blue background on hover */
            color: #3B82F6;  /* Medium blue text on hover */
        }}
        
        /* Base styles for QComboBox and QSpinBox */
        QComboBox, QSpinBox {{
            border: 1px solid #3B82F6;  /* Medium blue border */
            border-radius: 4px;  /* Rounded corners */
            padding: 5px 25px 5px 5px;  /* Padding: top right bottom left */
            background-color: white;  /* White background */
            font-size: 13px;  /* Font size */
            min-width: 120px;  /* Reduced minimum width from 150px */
            color: #1E3A8A;  /* Dark blue text color */
        }}
        
        /* Styles for QComboBox and QSpinBox when focused */
        QComboBox:focus, QSpinBox:focus {{
            border: 2px solid #3B82F6;  /* Thicker medium blue border when focused */
        }}
        
        /* Styles for QComboBox and QSpinBox on hover */
        QComboBox:hover, QSpinBox:hover {{
            background-color: #E0F2FE;  /* Light blue variant background on hover */
        }}
        
        /* Styles for the dropdown button in QComboBox */
        QComboBox::drop-down {{
            subcontrol-origin: padding;  /* Position relative to padding */
            subcontrol-position: top right;  /* Position at top right */
            width: 20px;  /* Width of dropdown button */
            border-left: 1px solid #3B82F6;  /* Left border of dropdown button */
            border-top-right-radius: 4px;  /* Round top-right corner */
            border-bottom-right-radius: 4px;  /* Round bottom-right corner */
        }}
        
        /* Styles for the down arrow in QComboBox */
        QComboBox::down-arrow {{
            image: url("{down_arrow_path}");  /* Use custom down arrow image */
            width: 20px;  /* Width of arrow image */
            height: 20px;  /* Height of arrow image */
        }}
        
        /* Styles for the dropdown view in QComboBox */
        QComboBox QAbstractItemView {{
            border: 1px solid #3B82F6;  /* Medium blue border for dropdown */
            background-color: white;  /* White background for dropdown */
            selection-background-color: #60A5FA;  /* Lighter medium blue for selected item */
        }}
        
        /* Styles for items in the QComboBox dropdown */
        QComboBox QAbstractItemView::item {{
            padding: 5px;  /* Padding for dropdown items */
            color: #1E3A8A;  /* Dark blue text for dropdown items */
        }}
        
        /* Styles for selected items in the QComboBox dropdown */
        QComboBox QAbstractItemView::item:selected {{
            background-color: #3B82F6;  /* Medium blue background for selected item */
            color: white;  /* White text for selected item */
        }}
        
        /* Styles for QLabel */
        QLabel {{
            border: none;  /* No border for labels */
            background-color: transparent;  /* Transparent background */
            padding: 0;  /* No padding */
            color: #1E3A8A;  /* Dark blue text color */
        }}
        
        /* Styles for up and down buttons in QSpinBox */
        QSpinBox::up-button, QSpinBox::down-button {{
            width: 16px;  /* Width of up/down buttons */
            border-left: 1px solid #3B82F6;  /* Left border for buttons */
        }}
        
        /* Styles for up and down arrows in QSpinBox */
        QSpinBox::up-arrow, QSpinBox::down-arrow {{
            width: 12px;  /* Width of arrow images */
            height: 12px;  /* Height of arrow images */
        }}
        
        /* Style for up arrow in QSpinBox */
        QSpinBox::up-arrow {{
            image: url("{up_arrow_path}");  /* Use custom up arrow image */
        }}
        
        /* Style for down arrow in QSpinBox */
        QSpinBox::down-arrow {{
            image: url("{down_arrow_path}");  /* Use custom down arrow image */
        }}
    """

def get_line_edit_style():
    # Define and return a string containing CSS-like styling for QLineEdit and QSpinBox widgets
    return """
        QLineEdit, QSpinBox {
            border: none;  /* Remove default border */
            border-bottom: 1px solid #93C5FD;  /* Add a lighter medium blue bottom border */
            border-radius: 0;  /* Remove border radius for a flat look */
            padding: 8px;  /* Add padding inside the widget */
            background-color: white;  /* Set background color to white */
            font-size: 13px;  /* Set font size to 13 pixels */
            color: #1E3A8A;  /* Set text color to dark blue */
        }
        QLineEdit:focus, QSpinBox:focus {
            border-bottom: 2px solid #3B82F6;  /* Thicken and darken bottom border when focused */
        }
        QLineEdit:hover, QSpinBox:hover {
            background-color: #E0F2FE;  /* Change background color on hover for visual feedback */
        }
        QLineEdit:disabled, QSpinBox:disabled {
            background-color: #E5E7EB;  /* Set a light gray background for disabled state */
            color: #9CA3AF;  /* Set a lighter text color for disabled state */
        }
    """

def get_button_style():
    # Define and return a string containing CSS-like styling for QPushButton widgets
    return """
        QPushButton {
            background-color: #3B82F6;  /* Set button background to medium blue */
            color: white;  /* Set text color to white */
            border: none;  /* Remove default border */
            border-radius: 4px;  /* Add slight rounding to corners */
            padding: 10px;  /* Reduced padding inside the button */
            font-weight: bold;  /* Make text bold */
            font-size: 14px;  /* Set font size to 14 pixels */
        }
        QPushButton:hover {
            background-color: #2563EB;  /* Darken background color on hover */
        }
        QPushButton:pressed {
            background-color: #1D4ED8;  /* Further darken background when button is pressed */
        }
        QPushButton:disabled {
            background-color: #93C5FD;  /* Use a lighter blue for disabled state */
            color: #DBEAFE;  /* Use a very light blue for text in disabled state */
        }
    """

def get_results_group_style():
    # Define and return a string containing CSS-like styling for QGroupBox widgets used in results display
    return """
        QGroupBox {
            background-color: #E0F2FE;  /* Set a light blue variant background */
            border: 1px solid #93C5FD;  /* Add a lighter medium blue border */
            border-radius: 4px;  /* Slightly round the corners */
            padding: 15px;  /* Add padding inside the group box */
            font-size: 14px;  /* Set font size for content */
        }
        QGroupBox::title {
            subcontrol-origin: margin;  /* Position the title in the margin */
            left: 10px;  /* Move title slightly to the right */
            padding: 0 5px 0 5px;  /* Add horizontal padding to title */
            border: none;  /* Remove border from title */
            color: #1E3A8A;  /* Set title color to dark blue */
            font-weight: bold;  /* Make title text bold */
        }
        QLabel {
            border: none;  /* Remove border from labels */
            background-color: transparent;  /* Make label background transparent */
            padding: 5px;  /* Add padding to labels */
            color: #1E3A8A;  /* Set label text color to dark blue */
            font-size: 14px;  /* Set font size for labels */
        }
        QLabel:first-child {
            font-weight: bold;  /* Make the first label (usually a title) bold */
            font-size: 16px;  /* Increase font size for the first label */
        }
    """

def get_room_group_style():
    # Define and return a string containing CSS-like styling for QGroupBox widgets used in room displays
    return """
        QGroupBox {
            background-color: #E0F2FE;  /* Set a light blue variant background */
            border: 1px solid #93C5FD;  /* Add a lighter medium blue border */
            border-radius: 4px;  /* Slightly round the corners */
            margin: 5px;  /* Add margin around the group box */
            padding: 10px;  /* Add padding inside the group box */
            font-size: 14px;  /* Set font size for content */
        }
        QGroupBox::title {
            subcontrol-origin: margin;  /* Position the title in the margin */
            left: 10px;  /* Move title slightly to the right */
            padding: 0 5px 0 5px;  /* Add horizontal padding to title */
            color: #1E3A8A;  /* Set title color to dark blue */
            font-weight: bold;  /* Make title text bold */
        }
        QLabel {
            border: none;  /* Remove border from labels */
            background-color: transparent;  /* Make label background transparent */
            padding: 2px;  /* Add small padding to labels */
            color: #1E3A8A;  /* Set label text color to dark blue */
            font-size: 13px;  /* Set font size for labels */
        }
        QLineEdit, QSpinBox {  /* Styles for input widgets within the group box */
            border: 1px solid #93C5FD;  /* Add a lighter medium blue border */
            border-radius: 3px;  /* Slightly round the corners */
            padding: 4px;  /* Add padding inside the input widgets */
            background-color: white;  /* Set background to white */
        }
        QLineEdit:focus, QSpinBox:focus {
            border-color: #3B82F6;  /* Change border color when focused */
        }
    """

def get_table_style():
    # Define and return a string containing CSS-like styling for QTableWidget
    return """
        QTableWidget {
            gridline-color: #93C5FD;  /* Set color of grid lines to lighter medium blue */
            selection-background-color: #60A5FA;  /* Set background color of selected cells */
            border: 1px solid #93C5FD;  /* Add a lighter medium blue border around the table */
            border-radius: 4px;  /* Slightly round the corners of the table */
        }
        QHeaderView::section {
            background-color: #3B82F6;  /* Set header background to medium blue */
            color: white;  /* Set header text color to white */
            font-weight: bold;  /* Make header text bold */
            border: none;  /* Remove borders from header sections */
            padding: 8px;  /* Add padding to header sections */
        }
        QTableWidget::item {
            padding: 4px;  /* Add padding to table cells */
        }
        QTableWidget::item:selected {
            color: #FFFFFF;  /* Set text color of selected items to white */
            background-color: #60A5FA;  /* Set background color of selected items */
        }
    """

def get_label_style():
    # Define and return a string containing CSS-like styling for QLabel widgets
    return """
        QLabel {
            color: #1E3A8A;  /* Set text color to dark blue */
            font-size: 13px;  /* Set font size to 13 pixels */
            font-weight: bold;  /* Make text bold */
            background-color: transparent;  /* Make background transparent */
            border: none;  /* Remove any border */
            padding: 0;  /* Remove padding */
            margin: 2px 0;  /* Add small vertical margin for spacing */
        }
        QLabel:disabled {
            color: #6B7280;  /* Set a gray color for disabled state */
        }
    """

def get_custom_spinbox_style():
    return """
        QSpinBox {
            border: 1px solid #93C5FD;
            border-radius: 4px;
            padding: 5px 25px 5px 5px;
            background-color: white;
            font-size: 13px;
            min-height: 10px;  /* Set minimum height */
            color: #1E3A8A;
        }
        QSpinBox:focus {
            border: 2px solid #3B82F6;
        }
        QSpinBox:hover {
            background-color: #E0F2FE;
        }
        QSpinBox::up-button, QSpinBox::down-button {
            border-left: 20px solid #93C5FD;
            width: 25px;
            background-color: #DBEAFE;
        }
    """

def get_room_selection_style():
    return """
        QGroupBox {
            background-color: #E0F2FE;
            border: 1px solid #93C5FD;
            border-radius: 4px;
        }
        QLabel {
            color: #1E3A8A;  /* Set text color to dark blue */
            font-size: 13px;  /* Set font size to 13 pixels */
            font-weight: bold;  /* Make text bold */
            background-color: transparent;  /* Make background transparent */
            border: none;  /* Remove any border */
            padding: 0;  /* Remove padding */
            margin: 2px 0;  /* Add small vertical margin for spacing */
        }
        QLabel:disabled {
            color: #6B7280;  /* Set a gray color for disabled state */
        }
    """

def get_result_title_style():
    # Style for the title labels in the Results section
    return """
        QLabel {
            color: #1E3A8A;  /* Dark blue text */
            font-size: 16pt; /* Large font size */
            font-weight: normal; /* Normal weight, underline provides emphasis */
            text-decoration: underline; /* Underline the title */
            qproperty-alignment: 'AlignCenter'; /* Center align text */
            padding-bottom: 2px; /* Add a little space below the underline */
            border: none;
            background-color: transparent;
        }
    """

def get_result_value_style():
    # Style for the value labels in the Results section
    return """
        QLabel {
            color: #1E3A8A;  /* Dark blue text */
            font-size: 20pt; /* Very large font size */
            font-weight: bold; /* Bold weight */
            qproperty-alignment: 'AlignCenter'; /* Center align text */
            padding-top: 2px; /* Add a little space above the value */
            border: none;
            background-color: transparent;
        }
    """
