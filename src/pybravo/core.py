import os
import logging
import threading
from typing import Optional, Dict, Any, Callable, TypeVar, List
from functools import wraps
import pythoncom
import clr
from .utils import is_admin

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

        if is_admin():
            logging.warning(
                "Running without admin privileges may limit driver's functionality. "
            )

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
        return self._connected and self.client is not None

    @sta_com_method
    def home_w(self) -> None:
        try:
            if not self.is_connected():
                raise BravoCommandError("Device not connected")
            logging.info("Homing operation started")
            self.client.HomeW()
        except Exception as e:
            raise BravoCommandError(f"Failed to home device: {e}")

    @sta_com_method
    def home_xyz(self) -> None:
        try:
            if not self.is_connected():
                raise BravoCommandError("Device not connected")
            logging.info("Homing XYZ operation started")
            self.client.HomeXYZ()
        except Exception as e:
            raise BravoCommandError(f"Failed to home XYZ: {e}")

    @sta_com_method
    def show_about_box(self) -> None:
        """Show the About box"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            self.client.ShowAboutBox()
        except Exception as e:
            raise BravoCommandError(f"Failed to show About box: {e}")

    @sta_com_method
    def aspirate(
        self,
        volume: float,
        plate_location: int,
        distance_from_well_bottom: float = 0.0,
        pre_aspirate_volume: float = 0.0,
        post_aspirate_volume: float = 0.0,
        retract_distance_per_microliter: float = 0.0,
    ) -> None:
        """Aspirate a specified volume from a well"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            logging.info(f"Aspirating {volume} uL from plate location {plate_location}")
            self.client.Aspirate(
                volume,
                pre_aspirate_volume,
                post_aspirate_volume,
                plate_location,
                distance_from_well_bottom,
                retract_distance_per_microliter,
            )
        except Exception as e:
            raise BravoCommandError(f"Failed to aspirate: {e}")

    def show_about(self) -> None:
        """Show the About dialog"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            self.client.ShowAboutDialog()
        except Exception as e:
            raise BravoCommandError(f"Failed to show About dialog: {e}")

    def abort(self) -> None:
        """Abort the current operation"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            logging.info("Aborting current operation")
            self.client.Abort()
        except Exception as e:
            raise BravoCommandError(f"Failed to abort operation: {e}")

    def dispense(
        self,
        volume: float,
        empty_tips: bool = False,
        blow_out_volume: float = 0.0,
        plate_location: int = 0,
        distance_from_well_bottom: float = 0.0,
        retract_distance_per_microliter: float = 0.0,
    ) -> None:
        """Dispense a specified volume into a well"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")
        try:
            logging.info(f"Dispensing {volume} uL into plate location {plate_location}")
            self.client.Dispense(
                volume,
                empty_tips,
                blow_out_volume,
                plate_location,
                distance_from_well_bottom,
                retract_distance_per_microliter,
            )
        except Exception as e:
            raise BravoCommandError(f"Failed to dispense: {e}")

    def enumerate_profiles(self) -> List[str]:
        """Enumerate available profiles"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            profiles = self.client.GetProfiles()
            logging.info(f"Available profiles: {profiles}")
            return profiles
        except Exception as e:
            raise BravoCommandError(f"Failed to enumerate profiles: {e}")

    def get_activex_version(self) -> str:
        """Get the ActiveX version of the Bravo SDK"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            version = self.client.GetActiveXVersion()
            logging.info(f"ActiveX Version: {version}")
            return version
        except Exception as e:
            raise BravoCommandError(f"Failed to get ActiveX version: {e}")

    def get_device_configuration(self, configuration_file: str) -> Dict[str, Any]:
        """Get the current device configuration"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")
        try:
            config = self.client.GetDeviceConfiguration(configuration_file)
            logging.info(f"Device Configuration: {config}")
            return config
        except Exception as e:
            raise BravoCommandError(f"Failed to get device configuration: {e}")

    def get_firmware_version(self) -> str:
        """Get the firmware version of the Bravo device"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            firmware_version = self.client.GetFirmwareVersion()
            logging.info(f"Firmware Version: {firmware_version}")
            return firmware_version
        except Exception as e:
            raise BravoCommandError(f"Failed to get firmware version: {e}")

    def get_hardware_version(self) -> str:
        """Get the hardware version of the Bravo device"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            hardware_version = self.client.GetHardwareVersion()
            logging.info(f"Hardware Version: {hardware_version}")
            return hardware_version
        except Exception as e:
            raise BravoCommandError(f"Failed to get hardware version: {e}")

    def get_labware_at_location(self, plate_location: int, labware_name: str) -> int:
        """Get the labware type at a specific plate location"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            labware = self.client.GetLabwareAtLocation(plate_location, labware_name)
            logging.info(f"Labware at location {plate_location}: {labware}")
            return labware
        except Exception as e:
            raise BravoCommandError(f"Failed to get labware at location: {e}")

    def get_last_error(self) -> str:
        """Get the last error message from the Bravo device"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            last_error = self.client.GetLastError()
            logging.info(f"Last Error: {last_error}")
            return last_error
        except Exception as e:
            raise BravoCommandError(f"Failed to get last error: {e}")

    def home_w(self) -> None:
        """Home the Bravo device"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            logging.info("Homing Bravo device")
            self.client.HomeW()
        except Exception as e:
            raise BravoCommandError(f"Failed to home device: {e}")

    def home_xyz(self) -> None:
        """Home the Bravo device in XYZ"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            logging.info("Homing Bravo device in XYZ")
            self.client.HomeXYZ()
        except Exception as e:
            raise BravoCommandError(f"Failed to home XYZ: {e}")

    def initialize(self, profile) -> None:
        """Initialize the Bravo device with a specific profile"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            logging.info(f"Initializing Bravo device with profile: {profile}")
            self.client.Initialize(profile)
        except Exception as e:
            raise BravoCommandError(f"Failed to initialize device: {e}")

    def mix(
        self,
        volume: float,
        pre_aspirate_volume: float,
        blow_out_volume: float,
        cycles: int,
        plate_location: int,
        distance_from_well_bottom: float,
        retract_distance_per_microliter: float,
    ) -> None:
        """Mix a specified volume in a well"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            logging.info(
                f"Mixing {volume} uL in plate location {plate_location} for {cycles} cycles"
            )
            self.client.Mix(
                volume,
                pre_aspirate_volume,
                blow_out_volume,
                cycles,
                plate_location,
                distance_from_well_bottom,
                retract_distance_per_microliter,
            )
        except Exception as e:
            raise BravoCommandError(f"Failed to mix: {e}")

    def move_to_location(self, plate_location: int, only_z: bool = False) -> None:
        """Move to a specific plate location"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            logging.info(f"Moving to plate location {plate_location}, only_z={only_z}")
            self.client.MoveToLocation(plate_location, only_z)
        except Exception as e:
            raise BravoCommandError(f"Failed to move to location: {e}")

    def move_to_position(
        self, axis: int, position: float, velocity: float, acceleration: float
    ) -> None:
        if not self.is_connected():
            raise BravoCommandError("Device not connected")
        try:
            logging.info(
                f"Moving axis {axis} to position {position} with velocity {velocity} and acceleration {acceleration}"
            )
            self.client.MoveToPosition(axis, position, velocity, acceleration)

        except Exception as e:
            raise BravoCommandError(f"Failed to move to position: {e}")

    def pick_and_place(
        self,
        start_location: int,
        end_location: int,
        gripper_offset: float,
        labware_thickness: float,
    ) -> None:
        """Perform a pick and place operation"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            logging.info(
                f"Picking from location {start_location} and placing at {end_location} with gripper offset {gripper_offset}"
            )
            self.client.PickAndPlace(start_location, end_location, gripper_offset)
        except Exception as e:
            raise BravoCommandError(f"Failed to pick and place: {e}")

    def pump_reagent(
        self,
        plate_location: int,
        fill_reservoir: bool,
        pump_speed: float,
        pump_time: float,
    ) -> None:
        if not self.is_connected():
            raise BravoCommandError("Device not connected")
        try:
            logging.info(
                f"Pumping reagent at plate location {plate_location}, fill_reservoir={fill_reservoir}, pump_speed={pump_speed}, pump_time={pump_time}"
            )
            self.client.PumpReagent(
                plate_location, fill_reservoir, pump_speed, pump_time
            )
        except Exception as e:
            raise BravoCommandError(f"Failed to pump reagent: {e}")

    def set_head_mode(self, mode: int) -> None:
        if not self.is_connected():
            raise BravoCommandError("Device not connected")
        try:
            logging.info(f"Setting head mode to {mode}")
            self.client.SetHeadMode(mode)
        except Exception as e:
            raise BravoCommandError(f"Failed to set head mode: {e}")

    def set_labware_at_location(self, plate_location: int, labware_type: str) -> None:
        """Set the labware type at a specific plate location"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            logging.info(f"Setting labware {labware_type} at location {plate_location}")
            self.client.SetLabwareAtLocation(plate_location, labware_type)
        except Exception as e:
            raise BravoCommandError(f"Failed to set labware at location: {e}")

    def set_liquid_class(self, liquid_class: str) -> None:
        """Set the liquid class for operations"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            logging.info(f"Setting liquid class to {liquid_class}")
            self.client.SetLiquidClass(liquid_class)
        except Exception as e:
            raise BravoCommandError(f"Failed to set liquid class: {e}")

    def set_tip_touch(
        self, number_of_side: int, retract_distance: float, horizontal_offset: float
    ) -> None:
        """Set the tip touch parameters"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            logging.info(
                f"Setting tip touch with number_of_side={number_of_side}, retract_distance={retract_distance}, horizontal_offset={horizontal_offset}"
            )
            self.client.SetTipTouch(number_of_side, retract_distance, horizontal_offset)
        except Exception as e:
            raise BravoCommandError(f"Failed to set tip touch: {e}")

    def show_diagnostics(self) -> None:
        """Show diagnostics information"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            self.client.ShowDiagsDialog(True, 1)
        except Exception as e:
            raise BravoCommandError(f"Failed to get diagnostics: {e}")

    def show_labware_editor(self) -> None:
        """Show the labware editor dialog"""
        try:
            # Setting visibility mask to 1 always.
            self.client.ShowLabwareEditor(1)
        except Exception as e:
            raise BravoCommandError(f"Failed to show labware editor: {e}")

    def show_liquid_library_editor(self) -> None:
        """Show the liquid library editor dialog"""
        try:
            self.client.ShowLiquidLibraryEditor()
        except Exception as e:
            raise BravoCommandError(f"Failed to show liquid library editor: {e}")

    def tips_off(self, plate_location: int) -> None:
        """Turn off tips at a specific plate location"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            logging.info(f"Turning off tips at plate location {plate_location}")
            self.client.TipsOff(plate_location)
        except Exception as e:
            raise BravoCommandError(f"Failed to turn off tips: {e}")

    def tips_on(self, plate_location: int) -> None:
        """Turn on tips at a specific plate location"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")

        try:
            logging.info(f"Turning on tips at plate location {plate_location}")
            self.client.TipsOn(plate_location)
        except Exception as e:
            raise BravoCommandError(f"Failed to turn on tips: {e}")

    def wash(
        self,
        volume: float,
        empty_tips: bool,
        pre_aspirate_volume: float,
        blow_out_volume: float,
        cycles: int,
        plate_location: int,
        distance_from_well_bottom: float = 0.0,
        retract_distance_per_microliter: float = 0.0,
        pump_in_flow_speed: float = 0.0,
        pump_out_flow_speed: float = 0.0,
    ) -> None:
        """Wash a specified volume in a well"""
        if not self.is_connected():
            raise BravoCommandError("Device not connected")
        try:
            logging.info(
                f"Washing {volume} uL in plate location {plate_location} for {cycles} cycles"
            )
            self.client.Wash(
                volume,
                empty_tips,
                pre_aspirate_volume,
                blow_out_volume,
                cycles,
                plate_location,
                distance_from_well_bottom,
                retract_distance_per_microliter,
                pump_in_flow_speed,
                pump_out_flow_speed,
            )
        except Exception as e:
            raise BravoCommandError(f"Failed to wash: {e}")

    def __enter__(self):
        """Context manager support"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.disconnect()


