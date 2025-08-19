"""
Custom exceptions for PyBravo
"""


class BravoError(Exception):
    """Base exception for PyBravo"""

    pass


class BravoConnectionError(BravoError):
    """Raised when connection to device fails"""

    pass


class BravoCommandError(BravoError):
    """Raised when a command to the device fails"""

    pass
