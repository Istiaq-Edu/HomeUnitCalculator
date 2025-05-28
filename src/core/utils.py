import logging
import os
import sys
from pathlib import Path

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ValueError("relative_path must be a non-empty string")
    
    relative_path = relative_path.strip()
    
    # Validate input to prevent directory traversal
    if (".." in relative_path or
        os.path.isabs(relative_path) or
        any(char in relative_path for char in ['\\', ':', '*', '?', '"', '<', '>', '|'])):
        raise ValueError(f"Invalid relative path: {relative_path}")
    
    try:
        # Try to get the base path from PyInstaller's temp folder
        base_path = sys._MEIPASS
    except AttributeError:
        # If not running as a PyInstaller executable, use the script directory
        # Get the project root more robustly
        current_file = os.path.abspath(__file__)
        # Look for a marker file to identify project root (requirements.txt, .git, etc.)
        base_path = current_file
        while base_path != os.path.dirname(base_path):  # Stop at filesystem root
            base_path = os.path.dirname(base_path)
            if os.path.exists(os.path.join(base_path, 'requirements.txt')):
                break
        else:
            # Fallback to the directory containing this utils.py file
            base_path = os.path.dirname(current_file)
            logging.warning(f"Could not find project root marker, using fallback: {base_path}")

    # Join the base path with the relative path to get the full path
    full_path = os.path.join(base_path, relative_path)
    # Check if the full path exists
    if not os.path.exists(full_path):
        # If the path doesn't exist, raise an exception
        raise FileNotFoundError(f"Resource not found: {full_path}")
    return full_path

def _clear_layout(layout):
    """
    Recursively clears all widgets and layouts from a given layout.
    Useful for dynamically updating UI elements.
    """
    if layout is not None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
            elif item.layout() is not None:
                _clear_layout(item.layout()) # Recursively clear sub-layouts