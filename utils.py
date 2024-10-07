# Import the os module for file and path operations
import os
# Import the sys module for system-specific parameters and functions
import sys

# Define a function to get the absolute path to a resource
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # Try to get the base path from PyInstaller's temp folder
        base_path = sys._MEIPASS
    except Exception:
        # If not running as a PyInstaller executable, use the current directory
        base_path = os.path.abspath(".")

    # Join the base path with the relative path to get the full path
    full_path = os.path.join(base_path, relative_path)
    # Check if the full path exists
    if not os.path.exists(full_path):
        # If the path doesn't exist, print a warning message
        print(f"Warning: Resource not found: {full_path}")
    # Return the full path, regardless of whether it exists or not
    return full_path