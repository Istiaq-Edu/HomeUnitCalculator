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
    
    # 1) Nuitka onefile sets this environment variable to the temp unpack dir
    nuitka_parent = os.environ.get("NUITKA_ONEFILE_PARENT")
    if nuitka_parent:
        base_path_candidate = os.path.join(nuitka_parent, relative_path)
        if os.path.exists(base_path_candidate):
            return base_path_candidate

    try:
        # 2) PyInstaller onefile sets sys._MEIPASS
        base_path = sys._MEIPASS  # type: ignore
    except AttributeError:
        # 3) Fallback: walk up from current file looking for project root marker
        current_file = os.path.abspath(__file__)
        base_path = current_file
        while base_path != os.path.dirname(base_path):  # Stop at filesystem root
            base_path = os.path.dirname(base_path)
            if os.path.exists(os.path.join(base_path, 'requirements.txt')):
                break
            # If we find the 'icons' folder at this level, treat it as root
            if os.path.isdir(os.path.join(base_path, 'icons')):
                break
        else:
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