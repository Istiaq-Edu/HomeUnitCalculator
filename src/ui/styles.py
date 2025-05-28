import textwrap
import functools
from types import MappingProxyType
from typing import Mapping
# Import the resource_path function from the utils module
from src.core.utils import resource_path

# Populate a *temporary* dict and immediately freeze it so no
# mutable handle escapes the module's boundary.
_color_vars_tmp: dict[str, str] = {
    "bg_primary":      "#EFF6FF",
    "bg_secondary":    "#E0F2FE",
    "accent_primary":  "#3B82F6",
    "accent_secondary":"#93C5FD",
    "text_primary":    "#1E3A8A",
    "text_secondary":  "white",
    "tab_unselected":  "#DBEAFE",
    "hover_dark_blue": "#2563EB",
    "pressed_dark_blue": "#1D4ED8",
    "red_primary": "#EF4444",
    "red_darker": "#DC2626",
    "red_even_darker": "#B91C1C",
    "green_primary": "#059669",
    "green_darker": "#047857",
    "green_even_darker": "#065F46",
    "selected_light_blue": "#60A5FA",
    "disabled_bg": "#E5E7EB",
    "disabled_text": "#9CA3AF",
}

# Expose as immutable, mutation-proof mapping
COLOR_VARS: Mapping[str, str] = MappingProxyType(_color_vars_tmp.copy())

# Delete the temporary RW dict to avoid accidental use
del _color_vars_tmp

@functools.lru_cache(maxsize=None)
def get_stylesheet():
    tpl = textwrap.dedent("""\
        /* Set the background color and text color for the main window and widgets */
        QMainWindow, QWidget {{
            background-color: {bg_primary};  /* Very light blue background */
            color: {text_primary};  /* Dark blue text color */
        }}

        /* Style the pane of the tab widget */
        QTabWidget::pane {{
            border: none;  /* Remove border */
            background-color: {bg_primary};  /* Very light blue background */
            border-radius: 0px;  /* No rounded corners */
        }}

        /* Style individual tabs */
        QTabBar::tab {{
            background-color: {tab_unselected};  /* Light blue for unselected tabs */
            color: {text_primary};  /* Dark blue text */
            padding: 8px 15px;  /* Reduced padding */
            border: none;  /* No border */
            border-top-left-radius: 8px;  /* Rounded top-left corner */
            border-top-right-radius: 8px;  /* Rounded top-right corner */
            font-size: 14px;  /* Text size */
            font-weight: bold;  /* Bold text */
            min-width: 150px;  /* Minimum width of tabs */
            max-width: none;  /* No maximum width */
        }}

        /* Style for the selected tab */
        QTabBar::tab:selected {{
            background-color: {text_secondary};  /* White background for selected tab */
            color: {accent_primary};  /* Medium blue text for selected tab */
        }}

        /* Style for unselected tabs */
        QTabBar::tab:!selected {{
            margin-top: 2px;  /* Small top margin for unselected tabs */
            background-color: {bg_primary};  /* Same as main background */
        }}

        /* Align the tab bar to the left */
        QTabWidget::tab-bar {{
            alignment: left;
        }}

        /* Style for line edits and spin boxes */
        QLineEdit, QSpinBox {{
            border: 1px solid {accent_secondary};  /* Lighter medium blue border */
            border-radius: 4px;  /* Slightly rounded corners */
            padding: 8px;  /* Internal padding */
            background-color: {bg_secondary};  /* Light blue variant background */
            font-size: 13px;  /* Text size */
        }}

        /* Style for focused line edits and spin boxes */
        QLineEdit:focus, QSpinBox:focus {{
            border: 2px solid {accent_primary};  /* Thicker, medium blue border when focused */
            background-color: {text_secondary};  /* White background when focused */
        }}

        /* Basic style for push buttons - detailed styling should use get_button_style() */
        QPushButton {{
            border-radius: 4px;  /* Rounded corners */
            padding: 10px;  /* Default padding */
        }}

        /* Specific button styles */
        QPushButton#savePdfButton {{
            background-color: {red_primary}; /* Red */
            color: {text_secondary};  /* White text */
            border: none;  /* No border */
            font-weight: bold;  /* Bold text */
            font-size: 14px;  /* Text size */
        }}
        QPushButton#savePdfButton:hover {{
            background-color: {red_darker}; /* Darker Red */
        }}
        QPushButton#savePdfButton:pressed {{
            background-color: {red_even_darker}; /* Even Darker Red */
        }}

        QPushButton#saveCsvButton {{
            background-color: {accent_primary}; /* Blue */
            color: {text_secondary};  /* White text */
            border: none;  /* No border */
            font-weight: bold;  /* Bold text */
            font-size: 14px;  /* Text size */
        }}
        QPushButton#saveCsvButton:hover {{
            background-color: {hover_dark_blue}; /* Darker Blue */
        }}
        QPushButton#saveCsvButton:pressed {{
            background-color: {pressed_dark_blue}; /* Even Darker Blue */
        }}

        QPushButton#saveCloudButton {{
            background-color: {green_primary}; /* Green */
            color: {text_secondary};  /* White text */
            border: none;  /* No border */
            font-weight: bold;  /* Bold text */
            font-size: 14px;  /* Text size */
        }}
        QPushButton#saveCloudButton:hover {{
            background-color: {green_darker}; /* Darker Green */
        }}
        QPushButton#saveCloudButton:pressed {{
            background-color: {green_even_darker}; /* Even Darker Green */
        }}

        /* Style for group boxes */
        QGroupBox {{
            background-color: {bg_secondary};  /* Light blue variant background */
            border: 1px solid {accent_secondary};  /* Lighter medium blue border */
            border-radius: 4px;  /* Rounded corners */
            margin-top: 10px;  /* Reduced top margin */
            font-weight: bold;  /* Bold text */
            padding: 10px;  /* Reduced internal padding */
            font-size: 14px;  /* Text size */
        }}

        /* Style for group box titles */
        QGroupBox::title {{
            subcontrol-origin: margin;  /* Position relative to the margin */
            left: 10px;  /* Left position */
            padding: 0 5px 0 5px;  /* Horizontal padding */
            font-size: 16px;  /* Title text size */
            color: {text_primary};  /* Dark blue text */
            font-weight: bold;  /* Bold text */
        }}

        /* Style for labels */
        QLabel {{
            color: {text_primary};  /* Dark blue text */
            font-size: 13px;  /* Text size */
            font-weight: bold;  /* Bold text */
        }}

        /* Style for scroll areas */
        QScrollArea, QScrollArea > QWidget > QWidget {{
            background-color: transparent;  /* Transparent background */
            border: none;  /* No border */
        }}

        /* Style for combo boxes */
        QComboBox {{
            border: 1px solid {accent_secondary};  /* Lighter medium blue border */
            border-radius: 4px;  /* Rounded corners */
            padding: 8px;  /* Internal padding */
            background-color: {bg_secondary};  /* Light blue variant background */
            font-size: 13px;  /* Text size */
        }}

        /* Style for combo box drop-down button */
        QComboBox::drop-down {{
            subcontrol-origin: padding;  /* Position relative to padding */
            subcontrol-position: top right;  /* Position at top right */
            width: 15px;  /* Width of drop-down button */
            border-left-width: 1px;  /* Left border width */
            border-left-color: {accent_secondary};  /* Left border color */
            border-left-style: solid;  /* Solid left border */
        }}

        /* Modernized scrollbar styles */
        QScrollBar:vertical {{
            border: none;
            background: {bg_secondary}; /* Light blue variant */
            width: 10px;
            margin: 0px 0px 0px 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {accent_secondary}; /* Lighter medium blue */
            min-height: 20px;
            border-radius: 5px;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}

        QScrollBar:horizontal {{
            border: none;
            background: {bg_secondary}; /* Light blue variant */
            height: 10px;
            margin: 0px 0px 0px 0px;
        }}
        QScrollBar::handle:horizontal {{
            background: {accent_secondary}; /* Lighter medium blue */
            min-width: 20px;
            border-radius: 5px;
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}
        """)
    return tpl.format(**COLOR_VARS)

@functools.lru_cache(maxsize=None)
def get_header_style():
    tpl = textwrap.dedent("""\
        background-color: {accent_primary};  /* Medium blue background */
        color: {text_secondary};  /* Set the text color to white for contrast */
        padding: 15px;  /* Reduced padding from 20px */
        font-size: 24px;  /* Reduced font size from 28px */
        font-weight: bold;  /* Make the text bold */
        border-radius: 0px;  /* Remove any rounded corners */
        qproperty-alignment: AlignCenter;  /* Qt specific alignment */
        margin-bottom: 10px;  /* Add 10 pixels of margin at the bottom */
        """)
    return tpl.format(**COLOR_VARS)

@functools.lru_cache(maxsize=None)
def get_group_box_style():
    tpl = textwrap.dedent("""\
        QGroupBox {{
            border: 1px solid {accent_secondary};  /* Lighter medium blue border */
            border-radius: 4px;  /* Round the corners with a 4-pixel radius */
            margin-top: 10px;  /* Reduced margin at the top */
            font-weight: bold;  /* Make the text bold */
            padding: 10px;  /* Reduced padding inside the group box */
            font-size: 14px;  /* Set the font size to 14 pixels */
            background-color: {bg_secondary};  /* Light blue variant background */
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;  /* Position the title relative to the margin */
            left: 10px;  /* Move the title 10 pixels from the left */
            padding: 0 5px 0 5px;  /* Add horizontal padding to the title */
            font-size: 16px;  /* Set the title font size to 16 pixels */
            color: {text_primary};  /* Dark blue text */
            font-weight: bold;  /* Make the title text bold */
        }}
        QLabel {{
            border: none;  /* Remove any border from labels */
            background-color: transparent;  /* Make the label background transparent */
            padding: 0;  /* Remove any padding from labels */
            color: {text_primary};  /* Dark blue text */
            font-size: 13px;  /* Set the label font size to 13 pixels */
            font-weight: bold;  /* Make the label text bold */
        }}
        """)
    return tpl.format(**COLOR_VARS)

@functools.lru_cache(maxsize=None)
def get_month_info_style():
    # Get the file paths for the down and up arrow icons, replacing backslashes with forward slashes
    down_arrow_path = resource_path('icons/down_arrow.png').replace('\\', '/')
    up_arrow_path = resource_path('icons/up_arrow.png').replace('\\', '/')
    
    # Use direct f-string with COLOR_VARS instead of calling .format()
    return textwrap.dedent(f"""\
        /* Style for when hovering over items in the QComboBox dropdown */
        QComboBox QAbstractItemView::item:hover {{
            background-color: {COLOR_VARS["tab_unselected"]};  /* Light blue background on hover */
            color: {COLOR_VARS["accent_primary"]};  /* Medium blue text on hover */
        }}

        /* Base styles for QComboBox and QSpinBox */
        QComboBox, QSpinBox {{
            border: 1px solid {COLOR_VARS["accent_primary"]};  /* Medium blue border */
            border-radius: 4px;  /* Rounded corners */
            padding: 5px 25px 5px 5px;  /* Padding: top right bottom left */
            background-color: {COLOR_VARS["text_secondary"]};  /* White background */
            font-size: 13px;  /* Font size */
            min-width: 120px;  /* Reduced minimum width from 150px */
            color: {COLOR_VARS["text_primary"]};  /* Dark blue text color */
        }}

        /* Styles for QComboBox and QSpinBox when focused */
        QComboBox:focus, QSpinBox:focus {{
            border: 2px solid {COLOR_VARS["accent_primary"]};  /* Thicker medium blue border when focused */
        }}

        /* Styles for QComboBox and QSpinBox on hover */
        QComboBox:hover, QSpinBox:hover {{
            background-color: {COLOR_VARS["bg_secondary"]};  /* Light blue variant background on hover */
        }}

        /* Styles for the dropdown button in QComboBox */
        QComboBox::drop-down {{
            subcontrol-origin: padding;  /* Position relative to padding */
            subcontrol-position: top right;  /* Position at top right */
            width: 20px;  /* Width of dropdown button */
            border-left: 1px solid {COLOR_VARS["accent_primary"]};  /* Left border of dropdown button */
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
            border: 1px solid {COLOR_VARS["accent_primary"]};  /* Medium blue border for dropdown */
            background-color: {COLOR_VARS["text_secondary"]};  /* White background for dropdown */
            selection-background-color: {COLOR_VARS["selected_light_blue"]};  /* Lighter medium blue for selected item */
        }}

        /* Styles for items in the QComboBox dropdown */
        QComboBox QAbstractItemView::item {{
            padding: 5px;  /* Padding for dropdown items */
            color: {COLOR_VARS["text_primary"]};  /* Dark blue text for dropdown items */
        }}

        /* Styles for selected items in the QComboBox dropdown */
        QComboBox QAbstractItemView::item:selected {{
            background-color: {COLOR_VARS["accent_primary"]};  /* Medium blue background for selected item */
            color: {COLOR_VARS["text_secondary"]};  /* White text for selected item */
        }}

        /* Styles for QLabel */
        QLabel {{
            border: none;  /* No border for labels */
            background-color: transparent;  /* Transparent background */
            padding: 0;  /* No padding */
            color: {COLOR_VARS["text_primary"]};  /* Dark blue text color */
        }}

        /* Styles for up and down buttons in QSpinBox */
        QSpinBox::up-button, QSpinBox::down-button {{
            width: 16px;  /* Width of up/down buttons */
            border-left: 1px solid {COLOR_VARS["accent_primary"]};  /* Left border for buttons */
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
        """)

@functools.lru_cache(maxsize=None)
def get_line_edit_style():
    # Define and return a string containing CSS-like styling for QLineEdit and QSpinBox widgets
    tpl = textwrap.dedent("""\
        QLineEdit, QSpinBox {{
            border: none;  /* Remove default border */
            border-bottom: 1px solid {accent_secondary};  /* Add a lighter medium blue bottom border */
            border-radius: 0;  /* Remove border radius for a flat look */
            padding: 8px;  /* Add padding inside the widget */
            background-color: {text_secondary};  /* Set background color to white */
            font-size: 13px;  /* Set font size to 13 pixels */
            color: {text_primary};  /* Set text color to dark blue */
        }}
        QLineEdit:focus, QSpinBox:focus {{
            border-bottom: 2px solid {accent_primary};  /* Thicken and darken bottom border when focused */
        }}
        QLineEdit:hover, QSpinBox:hover {{
            background-color: {bg_secondary};  /* Change background color on hover for visual feedback */
        }}
        QLineEdit:disabled, QSpinBox:disabled {{
            background-color: {disabled_bg};  /* Set a light gray background for disabled state */
            color: {disabled_text};  /* Set a lighter text color for disabled state */
        }}
        """)
    return tpl.format(**COLOR_VARS)

@functools.lru_cache(maxsize=None)
def get_button_style():
    # Define and return a string containing CSS-like styling for QPushButton widgets
    tpl = textwrap.dedent("""\
        QPushButton {{
            background-color: {accent_primary};  /* Set button background to medium blue */
            color: {text_secondary};  /* Set text color to white */
            border: none;  /* Remove default border */
            border-radius: 4px;  /* Add slight rounding to corners */
            padding: 10px;  /* Reduced padding inside the button */
            font-weight: bold;  /* Make text bold */
            font-size: 14px;  /* Set font size to 14 pixels */
        }}
        QPushButton:hover {{
            background-color: {hover_dark_blue};  /* Darken background color on hover */
        }}
        QPushButton:pressed {{
            background-color: {pressed_dark_blue};  /* Further darken background when button is pressed */
        }}
        QPushButton:disabled {{
            background-color: {accent_secondary};  /* Use a lighter blue for disabled state */
            color: {tab_unselected};  /* Use a very light blue for text in disabled state */
        }}
        """)
    return tpl.format(**COLOR_VARS)

@functools.lru_cache(maxsize=None)
def get_results_group_style():
    # Define and return a string containing CSS-like styling for QGroupBox widgets used in results display
    tpl = textwrap.dedent("""\
        QGroupBox {{
            background-color: {bg_secondary};  /* Set a light blue variant background */
            border: 1px solid {accent_secondary};  /* Add a lighter medium blue border */
            border-radius: 4px;  /* Slightly round the corners */
            padding: 15px;  /* Add padding inside the group box */
            font-size: 14px;  /* Set font size for content */
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;  /* Position the title in the margin */
            left: 10px;  /* Move title slightly to the right */
            padding: 0 5px 0 5px;  /* Add horizontal padding to title */
            border: none;  /* Remove border from title */
            color: {text_primary};  /* Set title color to dark blue */
            font-weight: bold;  /* Make title text bold */
        }}
        QLabel {{
            border: none;  /* Remove border from labels */
            background-color: transparent;  /* Make label background transparent */
            padding: 5px;  /* Add padding to labels */
            color: {text_primary};  /* Set label text color to dark blue */
            font-size: 14px;  /* Set font size for labels */
        }}
        /* Give the title label an objectName="resultTitle" in code instead */
        QLabel#resultTitle {{
            font-weight: bold;  /* Make the title label bold */
            font-size: 16px;  /* Increase font size for the title label */
        }}
        """)
    return tpl.format(**COLOR_VARS)

@functools.lru_cache(maxsize=None)
def get_room_group_style():
    # Define and return a string containing CSS-like styling for QGroupBox widgets used in room displays
    tpl = textwrap.dedent("""\
        QGroupBox {{
            background-color: {bg_secondary};  /* Set a light blue variant background */
            border: 1px solid {accent_secondary};  /* Add a lighter medium blue border */
            border-radius: 4px;  /* Slightly round the corners */
            margin: 5px;  /* Add margin around the group box */
            padding: 10px;  /* Add padding inside the group box */
            font-size: 14px;  /* Set font size for content */
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;  /* Position the title in the margin */
            left: 10px;  /* Move title slightly to the right */
            padding: 0 5px 0 5px;  /* Add horizontal padding to title */
            color: {text_primary};  /* Set title color to dark blue */
            font-weight: bold;  /* Make title text bold */
        }}
        QLabel {{
            border: none;  /* Remove border from labels */
            background-color: transparent;  /* Make label background transparent */
            padding: 2px;  /* Add small padding to labels */
            color: {text_primary};  /* Set label text color to dark blue */
            font-size: 13px;  /* Set font size for labels */
        }}
        QLineEdit, QSpinBox {{  /* Styles for input widgets within the group box */
            border: 1px solid {accent_secondary};  /* Add a lighter medium blue border */
            border-radius: 3px;  /* Slightly round the corners */
            padding: 4px;  /* Add padding inside the input widgets */
            background-color: {text_secondary};  /* Set background to white */
        }}
        QLineEdit:focus, QSpinBox:focus {{
            border-color: {accent_primary};  /* Change border color when focused */
        }}
        """)
    return tpl.format(**COLOR_VARS)

@functools.lru_cache(maxsize=None)
def get_table_style():
    # Define and return a string containing CSS-like styling for QTableWidget
    tpl = textwrap.dedent("""\
        QTableWidget {{
            gridline-color: {accent_secondary};  /* Set color of grid lines to lighter medium blue */
            selection-background-color: {selected_light_blue};  /* Set background color of selected cells */
            border: 1px solid {accent_secondary};  /* Add a lighter medium blue border around the table */
            border-radius: 4px;  /* Slightly round the corners of the table */
        }}
        QHeaderView::section {{
            background-color: {accent_primary};  /* Set header background to medium blue */
            color: {text_secondary};  /* Set header text color to white */
            font-weight: bold;  /* Make header text bold */
            border: none;  /* Remove borders from header sections */
            padding: 8px;  /* Add padding to header sections */
        }}
        QTableWidget::item {{
            padding: 4px;  /* Add padding to table cells */
        }}
        QTableWidget::item:selected {{
            background-color: {selected_light_blue};  /* Set background color of selected items */
            color: {text_primary};  /* Set text color of selected items */
        }}
        """)
    return tpl.format(**COLOR_VARS)

@functools.lru_cache(maxsize=None)
def get_label_style():
    # Define and return a string containing CSS-like styling for QLabel widgets
    tpl = textwrap.dedent("""\
        QLabel {{
            color: {text_primary};  /* Set text color to dark blue */
            font-size: 13px;  /* Set font size to 13 pixels */
            font-weight: bold;  /* Make text bold */
            background-color: transparent;  /* Make background transparent */
            padding: 0;  /* Remove padding */
        }}
        """)
    return tpl.format(**COLOR_VARS)

@functools.lru_cache(maxsize=None)
def get_custom_spinbox_style():
    # Define and return a string containing CSS-like styling for QSpinBox widgets with custom arrows
    # Get the file paths for the down and up arrow icons, replacing backslashes with forward slashes
    down_arrow_path = resource_path('icons/down_arrow.png').replace('\\', '/')
    up_arrow_path = resource_path('icons/up_arrow.png').replace('\\', '/')
    
    # Use direct f-string with COLOR_VARS like in get_month_info_style
    return textwrap.dedent(f"""\
        QSpinBox {{
            border: 1px solid {COLOR_VARS["accent_secondary"]};  /* Add a lighter medium blue border */
            border-radius: 4px;  /* Slightly round the corners */
            padding: 5px;  /* Add padding inside the spin box */
            background-color: {COLOR_VARS["bg_secondary"]};  /* Set background to light blue variant */
            font-size: 13px;  /* Set font size to 13 pixels */
            color: {COLOR_VARS["text_primary"]};  /* Set text color to dark blue */
        }}
        QSpinBox::up-button {{
            subcontrol-origin: border;  /* Position button relative to border */
            subcontrol-position: top right;  /* Position button at top right */
            width: 16px;  /* Set width of up button */
            border-left: 1px solid {COLOR_VARS["accent_secondary"]};  /* Add a left border to the button */
            border-top-right-radius: 4px;  /* Round top-right corner */
        }}
        QSpinBox::down-button {{
            subcontrol-origin: border;  /* Position button relative to border */
            subcontrol-position: bottom right;  /* Position button at bottom right */
            width: 16px;  /* Set width of down button */
            border-left: 1px solid {COLOR_VARS["accent_secondary"]};  /* Add a left border to the button */
            border-bottom-right-radius: 4px;  /* Round bottom-right corner */
        }}
        QSpinBox::up-arrow {{
            image: url("{up_arrow_path}");  /* Use custom up arrow icon */
            width: 12px;  /* Set width of up arrow icon */
            height: 12px;  /* Set height of up arrow icon */
        }}
        QSpinBox::down-arrow {{
            image: url("{down_arrow_path}");  /* Use custom down arrow icon */
            width: 12px;  /* Set width of down arrow icon */
            height: 12px;  /* Set height of down arrow icon */
        }}
        """)

@functools.lru_cache(maxsize=None)
def get_room_selection_style():
    # Define and return a string containing CSS-like styling for QComboBox widgets used in room selection
    # Get the file path for the down arrow icon, replacing backslashes with forward slashes
    down_arrow_path = resource_path('icons/down_arrow.png').replace('\\', '/')
    
    return textwrap.dedent(f"""\
        QComboBox {{
            border: 1px solid {COLOR_VARS["accent_secondary"]};  /* Add a lighter medium blue border */
            border-radius: 4px;  /* Slightly round the corners */
            padding: 5px;  /* Add padding inside the combo box */
            background-color: {COLOR_VARS["bg_secondary"]};  /* Set background to light blue variant */
            font-size: 13px;  /* Set font size to 13 pixels */
            color: {COLOR_VARS["text_primary"]};  /* Set text color to dark blue */
        }}
        QComboBox::drop-down {{
            subcontrol-origin: padding;  /* Position dropdown relative to padding */
            subcontrol-position: top right;  /* Position dropdown at top right */
            width: 15px;  /* Set width of dropdown button */
            border-left: 1px solid {COLOR_VARS["accent_secondary"]};  /* Add a left border to the dropdown button */
            border-top-right-radius: 4px;  /* Round top-right corner */
            border-bottom-right-radius: 4px;  /* Round bottom-right corner */
        }}
        QComboBox::down-arrow {{
            image: url("{down_arrow_path}");  /* Use custom down arrow icon */
            width: 12px;  /* Set width of down arrow icon */
            height: 12px;  /* Set height of down arrow icon */
        }}
        QComboBox QAbstractItemView {{
            border: 1px solid {COLOR_VARS["accent_secondary"]};  /* Add a lighter medium blue border to the dropdown view */
            background-color: {COLOR_VARS["bg_secondary"]};  /* Set background of dropdown view to light blue variant */
            selection-background-color: {COLOR_VARS["selected_light_blue"]};  /* Set background of selected items in dropdown */
        }}
        """)

@functools.lru_cache(maxsize=None)
def get_result_title_style():
    # Define and return a string containing CSS-like styling for QLabel widgets used as result titles
    tpl = textwrap.dedent("""\
        QLabel {{
            font-size: 16px;  /* Set font size to 16 pixels */
            font-weight: bold;  /* Make text bold */
            color: {text_primary};  /* Set text color to dark blue */
            padding: 5px 0;  /* Add vertical padding */
            qproperty-alignment: AlignCenter;  /* Center-align the text to match value labels */
        }}
        """)
    return tpl.format(**COLOR_VARS)

@functools.lru_cache(maxsize=None)
def get_result_value_style():
    # Define and return a string containing CSS-like styling for QLabel widgets used as result values
    tpl = textwrap.dedent("""\
        QLabel {{
            font-size: 26px;  /* Increased font size to 26px for maximum visibility */
            font-weight: bold;  /* Make the text bold */
            color: {text_primary};  /* Set text color to dark blue */
            padding: 2px 0;  /* Add vertical padding */
            qproperty-alignment: AlignCenter;  /* Qt-specific property for center alignment */
        }}
        """)
    return tpl.format(**COLOR_VARS)
