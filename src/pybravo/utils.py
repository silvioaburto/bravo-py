import ctypes
import sys
import os


def is_admin():
    try:
        # Check if we're on Windows
        if os.name != "nt":
            return False

        # Use ctypes to call Windows API
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        # If any error occurs, assume not admin
        return False
