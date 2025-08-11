import os
import logging
import threading
from typing import Optional, Dict, Any, Callable, TypeVar
from functools import wraps
import pythoncom
import clr

# Handle imports
try:
    from .exceptions import BravoConnectionError, BravoCommandError
except ImportError:

    class BravoConnectionError(Exception):
        pass

    class BravoCommandError(Exception):
        pass


SDK_DLL = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "DLLs",
    "AxInterop.HomewoodLib.dll",
)

if not os.path.exists(SDK_DLL):
    raise FileNotFoundError(f"Bravo SDK DLL not found at {SDK_DLL}")

print(f"Loading Bravo SDK from {SDK_DLL}")
clr.AddReference(SDK_DLL)

from AxHomewoodLib import AxHomewood  # type: ignore

T = TypeVar("T")


class STAComManager:
    """Context manager for STA COM operations"""

    def __enter__(self):
        pythoncom.CoInitialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pythoncom.CoUninitialize()


def sta_com_method(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to ensure COM method runs in STA context"""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with STAComManager():
            return func(self, *args, **kwargs)

    return wrapper


class BravoDriver:
    def __init__(
        self, profile: Optional[str] = None, simulation_mode: bool = False
    ) -> None:
        self.profile = profile
        self.simulation_mode = simulation_mode
        self._connected = False
        self.client = None

    @sta_com_method
    def connect(self) -> bool:
        """Connect to Bravo device"""
        try:
            self.client = AxHomewood()
            self.client.CreateControl()
            self.client.Blocking = True
            self._connected = True
            logging.info("Connected to Bravo device")
            return True
        except Exception as e:
            raise BravoConnectionError(f"Failed to connect: {e}")

    @sta_com_method
    def disconnect(self) -> None:
        """Disconnect from Bravo device"""
        if self.client:
            try:
                # Add any cleanup calls here
                self.client = None
                self._connected = False
                logging.info("Disconnected from Bravo device")
            except Exception as e:
                logging.warning(f"Error during disconnect: {e}")

    def is_connected(self) -> bool:
        """Check connection status"""
        return self._connected and self.client is not None

    @sta_com_method
    def home(self) -> None:
        try:
            if not self.is_connected():
                raise BravoCommandError("Device not connected")
            logging.info("Homing operation started")
            self.client.HomeW()
        except Exception as e:
            raise BravoCommandError(f"Failed to home device: {e}")

    def show_diagnostics(self) -> None:
        """Show diagnostics information"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            self.client.ShowDiagsDialog(True, 1)
        except Exception as e:
            raise BravoCommandError(f"Failed to get diagnostics: {e}")

    def execute_com_operation(self, operation: Callable[[], T]) -> T:
        """Execute any COM operation in STA context"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        with STAComManager():
            return operation()

    def __enter__(self):
        """Context manager support"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.disconnect()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        with BravoDriver() as driver:
            # driver.show_diagnostics()
            driver.home()

    except Exception as e:
        logging.error(f"Error: {e}")
