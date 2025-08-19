"""
Velocity11 Labware Registry Manager - Complete Version
A utility to create, read, update, and delete labware entries in the Windows registry.
Based on actual Velocity11 registry structure.
"""

import winreg
import json
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict, field
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class LabwareEntry:
    """Complete data class representing a Velocity11 labware entry with all registry values"""

    # Basic identification
    name: str
    description: str = ""
    manufacturer_part_number: str = ""

    # Core properties - these appear to be the most critical
    base_class: int = 1  # 1=plate, 6=tip box, 7=lid
    number_of_wells: int = 96

    # Default value (empty string key in registry)
    default_value: int = 0

    # Tip and capacity settings
    third_party_tip_capacity: int = 60
    tip_capacity: int = 60
    tipbox_source: int = 1
    disposable_tip_length: float = 38.20000
    filter_tip_pin_tool_length: float = 0.00000
    z_tip_attach_offset: float = -1.00000

    # Plate orientation notches
    a1_notch: int = 0
    a12_notch: int = 0
    h1_notch: int = 0
    h12_notch: int = 0

    # Access2 robot settings
    access2_ignore_plate_sensor: int = 0
    access2_robot_gripper_offset: float = 6.00000
    access2_robot_lid_gripper_offset: float = 0.00000

    # BC (BioCell/Base Controller) gripper positions
    bc_error_correction_offset: float = 0.00000
    bc_gripper_holding_lidded_plate_position: float = 4.00000
    bc_gripper_holding_lid_position: float = 3.50000
    bc_gripper_holding_plate_position: float = 4.00000
    bc_gripper_holding_stack_position: float = 4.50000
    bc_gripper_open_position: float = 0.10000
    bc_gripper_pressure: str = ""
    bc_robot_gripper_offset: float = 8.00000
    bc_sensor_offset: float = 8.00000
    bc_stacker_gripper_offset: float = 0.00000

    # BC Rear gripper positions
    bc_r_error_correction_offset: float = 0.00000
    bc_r_gripper_holding_lidded_plate_position: float = 9.00000
    bc_r_gripper_holding_lid_position: float = 8.00000
    bc_r_gripper_holding_plate_position: float = 9.00000
    bc_r_gripper_holding_stack_position: float = 10.00000
    bc_r_gripper_insertion_offset: float = 11.00000
    bc_r_gripper_open_position: float = -1.00000
    bc_r_lid_gripper_offset: float = 0.00000
    bc_r_plate_presence_gain: float = 1.00000
    bc_r_plate_presence_threshold: int = 50
    bc_r_robot_gripper_offset: float = 8.00000
    bc_r_sensor_offset: float = 8.00000
    bc_r_stacker_gripper_offset: float = 6.00000
    bc_r_stack_holding_method: str = "Hold with stacker grippers"

    # BenchBot settings
    benchbot_grip_torque_percentage: int = 100
    benchbot_landscape_gripper_closed_width: float = 124.00000
    benchbot_landscape_gripper_offset_ranges: str = "0-10"
    benchbot_landscape_gripper_open_width: float = 132.00000
    benchbot_landscape_gripper_tolerance: float = 4.00000
    benchbot_portrait_gripper_closed_width: float = 84.00000
    benchbot_portrait_gripper_offset_ranges: str = "0-10"
    benchbot_portrait_gripper_open_width: float = 92.00000
    benchbot_portrait_gripper_tolerance: float = 4.00000

    # Bravo robot settings
    bravo_ignore_plate_sensor: int = 0
    bravo_robot_gripper_offset: float = 2.00000
    bravo_robot_lid_gripper_offset: float = 0.00000

    # Capabilities flags
    can_be_mounted: int = 0
    can_be_sealed: int = 0
    can_have_lid: int = 0
    can_mount: int = 0
    check_plate_orientation: int = 1

    # Lid properties
    lidded_stacking_thickness: float = 0.00000
    lidded_thickness: float = 0.00000
    lid_departure_height: float = 0.00000
    lid_resting_height: float = 0.00000
    mounted_lid_robot_gripper_offset: float = 3.00000

    # System settings
    lower_plate_at_vcode: int = 0
    presentation_offset: float = 0.00000
    requires_insert: str = "None"
    robot_gripper_offset: float = 0.00000
    robot_handling_speed: int = 0

    # Sealing properties
    sealed_stacking_thickness: float = 0.00000
    sealed_thickness: float = 0.00000

    # Sensor settings
    sensor_intensity: int = 50
    sensor_offset: float = 8.00000
    sensor_threshold: int = 50
    sensor_threshold_min: int = 0

    # Physical dimensions
    shim_thickness: float = 0.00000
    stacker_gripper_offset: float = 0.00000
    stacking_thickness: float = 0.00000
    thickness: float = 0.00000

    # Vacuum settings
    use_vacuum_clamp: int = 0

    # VRobot (Velocity Robot) settings
    vrobot_grip_torque_percentage: int = 50
    vrobot_ignore_plate_sensor: int = 0
    vrobot_landscape_gripper_offset_max: float = 10.00000
    vrobot_landscape_gripper_offset_min: float = 0.00000
    vrobot_landscape_gripper_offset_ranges: str = "0-10"
    vrobot_portrait_gripper_offset_max: float = 10.00000
    vrobot_portrait_gripper_offset_min: float = 0.00000
    vrobot_portrait_gripper_offset_ranges: str = "0-10"
    vrobot_robot_lid_gripper_offset_max: float = 0.00000
    vrobot_robot_lid_gripper_offset_min: float = 0.00000

    # Well geometry and positioning
    well_bottom_shape: int = 1
    well_depth: float = 0.00000
    well_diameter: float = 0.00000
    well_geometry: int = 1
    well_tip_volume: float = 0.00000
    x_teachpoint_to_well: float = 0.00000
    x_well_to_well: float = 9.00000
    y_teachpoint_to_well: float = 0.00000
    y_well_to_well: float = 9.00000

    # Optional image file
    image_filename: str = ""

    def to_registry_dict(self) -> Dict[str, Any]:
        """Convert the labware entry to registry format with proper key names"""
        data = asdict(self)
        name = data.pop("name")  # Remove name from data as it's used as the key

        # Map Python field names to registry key names
        registry_data = {}
        field_mapping = {
            "default_value": "",  # Empty string key
            "third_party_tip_capacity": "3RD_PARTY_TIP_CAPACITY",
            "a1_notch": "A1_NOTCH",
            "a12_notch": "A12_NOTCH",
            "h1_notch": "H1_NOTCH",
            "h12_notch": "H12_NOTCH",
            "access2_ignore_plate_sensor": "ACCESS2_IGNORE_PLATE_SENSOR",
            "access2_robot_gripper_offset": "ACCESS2_ROBOT_GRIPPER_OFFSET",
            "access2_robot_lid_gripper_offset": "ACCESS2_ROBOT_LID_GRIPPER_OFFSET",
            "base_class": "BASE_CLASS",
            "bc_error_correction_offset": "BC_ERROR_CORRECTION_OFFSET",
            "bc_gripper_holding_lidded_plate_position": "BC_GRIPPER_HOLDING_LIDDED_PLATE_POSITION",
            "bc_gripper_holding_lid_position": "BC_GRIPPER_HOLDING_LID_POSITION",
            "bc_gripper_holding_plate_position": "BC_GRIPPER_HOLDING_PLATE_POSITION",
            "bc_gripper_holding_stack_position": "BC_GRIPPER_HOLDING_STACK_POSITION",
            "bc_gripper_open_position": "BC_GRIPPER_OPEN_POSITION",
            "bc_gripper_pressure": "BC_GRIPPER_PRESSURE",
            "bc_robot_gripper_offset": "BC_ROBOT_GRIPPER_OFFSET",
            "bc_r_error_correction_offset": "BC_R_ERROR_CORRECTION_OFFSET",
            "bc_r_gripper_holding_lidded_plate_position": "BC_R_GRIPPER_HOLDING_LIDDED_PLATE_POSITION",
            "bc_r_gripper_holding_lid_position": "BC_R_GRIPPER_HOLDING_LID_POSITION",
            "bc_r_gripper_holding_plate_position": "BC_R_GRIPPER_HOLDING_PLATE_POSITION",
            "bc_r_gripper_holding_stack_position": "BC_R_GRIPPER_HOLDING_STACK_POSITION",
            "bc_r_gripper_insertion_offset": "BC_R_GRIPPER_INSERTION_OFFSET",
            "bc_r_gripper_open_position": "BC_R_GRIPPER_OPEN_POSITION",
            "bc_r_lid_gripper_offset": "BC_R_LID_GRIPPER_OFFSET",
            "bc_r_plate_presence_gain": "BC_R_PLATE_PRESENCE_GAIN",
            "bc_r_plate_presence_threshold": "BC_R_PLATE_PRESENCE_THRESHOLD",
            "bc_r_robot_gripper_offset": "BC_R_ROBOT_GRIPPER_OFFSET",
            "bc_r_sensor_offset": "BC_R_SENSOR_OFFSET",
            "bc_r_stacker_gripper_offset": "BC_R_STACKER_GRIPPER_OFFSET",
            "bc_r_stack_holding_method": "BC_R_STACK_HOLDING_METHOD",
            "bc_sensor_offset": "BC_SENSOR_OFFSET",
            "bc_stacker_gripper_offset": "BC_STACKER_GRIPPER_OFFSET",
            "benchbot_grip_torque_percentage": "BENCHBOT_GRIP_TORQUE_PERCENTAGE",
            "benchbot_landscape_gripper_closed_width": "BENCHBOT_LANDSCAPE_GRIPPER_CLOSED_WIDTH",
            "benchbot_landscape_gripper_offset_ranges": "BENCHBOT_LANDSCAPE_GRIPPER_OFFSET_RANGES",
            "benchbot_landscape_gripper_open_width": "BENCHBOT_LANDSCAPE_GRIPPER_OPEN_WIDTH",
            "benchbot_landscape_gripper_tolerance": "BENCHBOT_LANDSCAPE_GRIPPER_TOLERANCE",
            "benchbot_portrait_gripper_closed_width": "BENCHBOT_PORTRAIT_GRIPPER_CLOSED_WIDTH",
            "benchbot_portrait_gripper_offset_ranges": "BENCHBOT_PORTRAIT_GRIPPER_OFFSET_RANGES",
            "benchbot_portrait_gripper_open_width": "BENCHBOT_PORTRAIT_GRIPPER_OPEN_WIDTH",
            "benchbot_portrait_gripper_tolerance": "BENCHBOT_PORTRAIT_GRIPPER_TOLERANCE",
            "bravo_ignore_plate_sensor": "BRAVO_IGNORE_PLATE_SENSOR",
            "bravo_robot_gripper_offset": "BRAVO_ROBOT_GRIPPER_OFFSET",
            "bravo_robot_lid_gripper_offset": "BRAVO_ROBOT_LID_GRIPPER_OFFSET",
            "can_be_mounted": "CAN_BE_MOUNTED",
            "can_be_sealed": "CAN_BE_SEALED",
            "can_have_lid": "CAN_HAVE_LID",
            "can_mount": "CAN_MOUNT",
            "check_plate_orientation": "CHECK_PLATE_ORIENTATION",
            "description": "DESCRIPTION",
            "disposable_tip_length": "DISPOSABLE_TIP_LENGTH",
            "filter_tip_pin_tool_length": "FILTER_TIP_PIN_TOOL_LENGTH",
            "image_filename": "IMAGE_FILENAME",
            "lidded_stacking_thickness": "LIDDED_STACKING_THICKNESS",
            "lidded_thickness": "LIDDED_THICKNESS",
            "lid_departure_height": "LID_DEPARTURE_HEIGHT",
            "lid_resting_height": "LID_RESTING_HEIGHT",
            "lower_plate_at_vcode": "LOWER_PLATE_AT_VCODE",
            "manufacturer_part_number": "MANUFACTURER_PART_NUMBER",
            "mounted_lid_robot_gripper_offset": "MOUNTED_LID_ROBOT_GRIPPER_OFFSET",
            "number_of_wells": "NUMBER_OF_WELLS",
            "presentation_offset": "PRESENTATION_OFFSET",
            "requires_insert": "REQUIRES INSERT",
            "robot_gripper_offset": "ROBOT_GRIPPER_OFFSET",
            "robot_handling_speed": "ROBOT_HANDLING_SPEED",
            "sealed_stacking_thickness": "SEALED_STACKING_THICKNESS",
            "sealed_thickness": "SEALED_THICKNESS",
            "sensor_intensity": "SENSOR_INTENSITY",
            "sensor_offset": "SENSOR_OFFSET",
            "sensor_threshold": "SENSOR_THRESHOLD",
            "sensor_threshold_min": "SENSOR_THRESHOLD_MIN",
            "shim_thickness": "SHIM_THICKNESS",
            "stacker_gripper_offset": "STACKER_GRIPPER_OFFSET",
            "stacking_thickness": "STACKING_THICKNESS",
            "thickness": "THICKNESS",
            "tipbox_source": "TIPBOX_SOURCE",
            "tip_capacity": "TIP_CAPACITY",
            "use_vacuum_clamp": "USE_VACUUM_CLAMP",
            "vrobot_grip_torque_percentage": "VROBOT_GRIP_TORQUE_PERCENTAGE",
            "vrobot_ignore_plate_sensor": "VROBOT_IGNORE_PLATE_SENSOR",
            "vrobot_landscape_gripper_offset_max": "VROBOT_LANDSCAPE_GRIPPER_OFFSET_MAX",
            "vrobot_landscape_gripper_offset_min": "VROBOT_LANDSCAPE_GRIPPER_OFFSET_MIN",
            "vrobot_landscape_gripper_offset_ranges": "VROBOT_LANDSCAPE_GRIPPER_OFFSET_RANGES",
            "vrobot_portrait_gripper_offset_max": "VROBOT_PORTRAIT_GRIPPER_OFFSET_MAX",
            "vrobot_portrait_gripper_offset_min": "VROBOT_PORTRAIT_GRIPPER_OFFSET_MIN",
            "vrobot_portrait_gripper_offset_ranges": "VROBOT_PORTRAIT_GRIPPER_OFFSET_RANGES",
            "vrobot_robot_lid_gripper_offset_max": "VROBOT_ROBOT_LID_GRIPPER_OFFSET_MAX",
            "vrobot_robot_lid_gripper_offset_min": "VROBOT_ROBOT_LID_GRIPPER_OFFSET_MIN",
            "well_bottom_shape": "WELL_BOTTOM_SHAPE",
            "well_depth": "WELL_DEPTH",
            "well_diameter": "WELL_DIAMETER",
            "well_geometry": "WELL_GEOMETRY",
            "well_tip_volume": "WELL_TIP_VOLUME",
            "x_teachpoint_to_well": "X_TEACHPOINT_TO_WELL",
            "x_well_to_well": "X_WELL_TO_WELL",
            "y_teachpoint_to_well": "Y_TEACHPOINT_TO_WELL",
            "y_well_to_well": "Y_WELL_TO_WELL",
            "z_tip_attach_offset": "Z_TIP_ATTACH_OFFSET",
        }

        for python_field, registry_key in field_mapping.items():
            if python_field in data:
                value = data[python_field]
                registry_data[registry_key] = value

        # Add the NAME field
        registry_data["NAME"] = name

        return registry_data

    @classmethod
    def from_registry_dict(
        cls, name: str, registry_data: Dict[str, Any]
    ) -> "LabwareEntry":
        """Create a LabwareEntry from registry data"""
        # Reverse mapping from registry keys to Python field names
        reverse_mapping = {
            "": "default_value",
            "3RD_PARTY_TIP_CAPACITY": "third_party_tip_capacity",
            "A1_NOTCH": "a1_notch",
            "A12_NOTCH": "a12_notch",
            "H1_NOTCH": "h1_notch",
            "H12_NOTCH": "h12_notch",
            "ACCESS2_IGNORE_PLATE_SENSOR": "access2_ignore_plate_sensor",
            "ACCESS2_ROBOT_GRIPPER_OFFSET": "access2_robot_gripper_offset",
            "ACCESS2_ROBOT_LID_GRIPPER_OFFSET": "access2_robot_lid_gripper_offset",
            "BASE_CLASS": "base_class",
            "BC_ERROR_CORRECTION_OFFSET": "bc_error_correction_offset",
            "BC_GRIPPER_HOLDING_LIDDED_PLATE_POSITION": "bc_gripper_holding_lidded_plate_position",
            "BC_GRIPPER_HOLDING_LID_POSITION": "bc_gripper_holding_lid_position",
            "BC_GRIPPER_HOLDING_PLATE_POSITION": "bc_gripper_holding_plate_position",
            "BC_GRIPPER_HOLDING_STACK_POSITION": "bc_gripper_holding_stack_position",
            "BC_GRIPPER_OPEN_POSITION": "bc_gripper_open_position",
            "BC_GRIPPER_PRESSURE": "bc_gripper_pressure",
            "BC_ROBOT_GRIPPER_OFFSET": "bc_robot_gripper_offset",
            "BC_R_ERROR_CORRECTION_OFFSET": "bc_r_error_correction_offset",
            "BC_R_GRIPPER_HOLDING_LIDDED_PLATE_POSITION": "bc_r_gripper_holding_lidded_plate_position",
            "BC_R_GRIPPER_HOLDING_LID_POSITION": "bc_r_gripper_holding_lid_position",
            "BC_R_GRIPPER_HOLDING_PLATE_POSITION": "bc_r_gripper_holding_plate_position",
            "BC_R_GRIPPER_HOLDING_STACK_POSITION": "bc_r_gripper_holding_stack_position",
            "BC_R_GRIPPER_INSERTION_OFFSET": "bc_r_gripper_insertion_offset",
            "BC_R_GRIPPER_OPEN_POSITION": "bc_r_gripper_open_position",
            "BC_R_LID_GRIPPER_OFFSET": "bc_r_lid_gripper_offset",
            "BC_R_PLATE_PRESENCE_GAIN": "bc_r_plate_presence_gain",
            "BC_R_PLATE_PRESENCE_THRESHOLD": "bc_r_plate_presence_threshold",
            "BC_R_ROBOT_GRIPPER_OFFSET": "bc_r_robot_gripper_offset",
            "BC_R_SENSOR_OFFSET": "bc_r_sensor_offset",
            "BC_R_STACKER_GRIPPER_OFFSET": "bc_r_stacker_gripper_offset",
            "BC_R_STACK_HOLDING_METHOD": "bc_r_stack_holding_method",
            "BC_SENSOR_OFFSET": "bc_sensor_offset",
            "BC_STACKER_GRIPPER_OFFSET": "bc_stacker_gripper_offset",
            "BENCHBOT_GRIP_TORQUE_PERCENTAGE": "benchbot_grip_torque_percentage",
            "BENCHBOT_LANDSCAPE_GRIPPER_CLOSED_WIDTH": "benchbot_landscape_gripper_closed_width",
            "BENCHBOT_LANDSCAPE_GRIPPER_OFFSET_RANGES": "benchbot_landscape_gripper_offset_ranges",
            "BENCHBOT_LANDSCAPE_GRIPPER_OPEN_WIDTH": "benchbot_landscape_gripper_open_width",
            "BENCHBOT_LANDSCAPE_GRIPPER_TOLERANCE": "benchbot_landscape_gripper_tolerance",
            "BENCHBOT_PORTRAIT_GRIPPER_CLOSED_WIDTH": "benchbot_portrait_gripper_closed_width",
            "BENCHBOT_PORTRAIT_GRIPPER_OFFSET_RANGES": "benchbot_portrait_gripper_offset_ranges",
            "BENCHBOT_PORTRAIT_GRIPPER_OPEN_WIDTH": "benchbot_portrait_gripper_open_width",
            "BENCHBOT_PORTRAIT_GRIPPER_TOLERANCE": "benchbot_portrait_gripper_tolerance",
            "BRAVO_IGNORE_PLATE_SENSOR": "bravo_ignore_plate_sensor",
            "BRAVO_ROBOT_GRIPPER_OFFSET": "bravo_robot_gripper_offset",
            "BRAVO_ROBOT_LID_GRIPPER_OFFSET": "bravo_robot_lid_gripper_offset",
            "CAN_BE_MOUNTED": "can_be_mounted",
            "CAN_BE_SEALED": "can_be_sealed",
            "CAN_HAVE_LID": "can_have_lid",
            "CAN_MOUNT": "can_mount",
            "CHECK_PLATE_ORIENTATION": "check_plate_orientation",
            "DESCRIPTION": "description",
            "DISPOSABLE_TIP_LENGTH": "disposable_tip_length",
            "FILTER_TIP_PIN_TOOL_LENGTH": "filter_tip_pin_tool_length",
            "IMAGE_FILENAME": "image_filename",
            "LIDDED_STACKING_THICKNESS": "lidded_stacking_thickness",
            "LIDDED_THICKNESS": "lidded_thickness",
            "LID_DEPARTURE_HEIGHT": "lid_departure_height",
            "LID_RESTING_HEIGHT": "lid_resting_height",
            "LOWER_PLATE_AT_VCODE": "lower_plate_at_vcode",
            "MANUFACTURER_PART_NUMBER": "manufacturer_part_number",
            "MOUNTED_LID_ROBOT_GRIPPER_OFFSET": "mounted_lid_robot_gripper_offset",
            "NUMBER_OF_WELLS": "number_of_wells",
            "PRESENTATION_OFFSET": "presentation_offset",
            "REQUIRES INSERT": "requires_insert",
            "ROBOT_GRIPPER_OFFSET": "robot_gripper_offset",
            "ROBOT_HANDLING_SPEED": "robot_handling_speed",
            "SEALED_STACKING_THICKNESS": "sealed_stacking_thickness",
            "SEALED_THICKNESS": "sealed_thickness",
            "SENSOR_INTENSITY": "sensor_intensity",
            "SENSOR_OFFSET": "sensor_offset",
            "SENSOR_THRESHOLD": "sensor_threshold",
            "SENSOR_THRESHOLD_MIN": "sensor_threshold_min",
            "SHIM_THICKNESS": "shim_thickness",
            "STACKER_GRIPPER_OFFSET": "stacker_gripper_offset",
            "STACKING_THICKNESS": "stacking_thickness",
            "THICKNESS": "thickness",
            "TIPBOX_SOURCE": "tipbox_source",
            "TIP_CAPACITY": "tip_capacity",
            "USE_VACUUM_CLAMP": "use_vacuum_clamp",
            "VROBOT_GRIP_TORQUE_PERCENTAGE": "vrobot_grip_torque_percentage",
            "VROBOT_IGNORE_PLATE_SENSOR": "vrobot_ignore_plate_sensor",
            "VROBOT_LANDSCAPE_GRIPPER_OFFSET_MAX": "vrobot_landscape_gripper_offset_max",
            "VROBOT_LANDSCAPE_GRIPPER_OFFSET_MIN": "vrobot_landscape_gripper_offset_min",
            "VROBOT_LANDSCAPE_GRIPPER_OFFSET_RANGES": "vrobot_landscape_gripper_offset_ranges",
            "VROBOT_PORTRAIT_GRIPPER_OFFSET_MAX": "vrobot_portrait_gripper_offset_max",
            "VROBOT_PORTRAIT_GRIPPER_OFFSET_MIN": "vrobot_portrait_gripper_offset_min",
            "VROBOT_PORTRAIT_GRIPPER_OFFSET_RANGES": "vrobot_portrait_gripper_offset_ranges",
            "VROBOT_ROBOT_LID_GRIPPER_OFFSET_MAX": "vrobot_robot_lid_gripper_offset_max",
            "VROBOT_ROBOT_LID_GRIPPER_OFFSET_MIN": "vrobot_robot_lid_gripper_offset_min",
            "WELL_BOTTOM_SHAPE": "well_bottom_shape",
            "WELL_DEPTH": "well_depth",
            "WELL_DIAMETER": "well_diameter",
            "WELL_GEOMETRY": "well_geometry",
            "WELL_TIP_VOLUME": "well_tip_volume",
            "X_TEACHPOINT_TO_WELL": "x_teachpoint_to_well",
            "X_WELL_TO_WELL": "x_well_to_well",
            "Y_TEACHPOINT_TO_WELL": "y_teachpoint_to_well",
            "Y_WELL_TO_WELL": "y_well_to_well",
            "Z_TIP_ATTACH_OFFSET": "z_tip_attach_offset",
        }

        # Convert registry data to Python field names
        kwargs = {"name": name}
        for reg_key, value in registry_data.items():
            if reg_key in reverse_mapping:
                python_field = reverse_mapping[reg_key]
                # Convert string numbers to proper types, but be more careful
                if isinstance(value, str):
                    # Check if it's a pure number (handles negative and decimal)
                    try:
                        # Try integer first
                        if (
                            "." not in value
                            and "-" != value
                            and value.lstrip("-").isdigit()
                        ):
                            kwargs[python_field] = int(value)
                        # Try float for decimal numbers
                        elif (
                            value.replace(".", "").replace("-", "").isdigit()
                            and value.count(".") <= 1
                        ):
                            kwargs[python_field] = float(value)
                        else:
                            # Keep as string for things like "0-10", "Hold with shelf", etc.
                            kwargs[python_field] = value
                    except ValueError:
                        # If conversion fails, keep as string
                        kwargs[python_field] = value
                else:
                    kwargs[python_field] = value

        return cls(**kwargs)


class LabwareRegistryManager:
    """Manager class for Velocity11 labware registry operations"""

    BASE_KEY_PATH = r"SOFTWARE\WOW6432Node\Velocity11\Shared\Labware\Labware_Entries"

    def __init__(self):
        self.hkey = winreg.HKEY_LOCAL_MACHINE

    def list_labware_entries(self) -> List[str]:
        """List all existing labware entry names"""
        entries = []
        try:
            with winreg.OpenKey(
                self.hkey, self.BASE_KEY_PATH, 0, winreg.KEY_READ
            ) as key:
                i = 0
                while True:
                    try:
                        entry_name = winreg.EnumKey(key, i)
                        entries.append(entry_name)
                        i += 1
                    except WindowsError:
                        break
        except FileNotFoundError:
            logger.error(f"Registry path not found: {self.BASE_KEY_PATH}")
        except PermissionError:
            logger.error("Permission denied. Run as administrator.")

        return entries

    def read_labware_entry(self, entry_name: str) -> Dict[str, Any]:
        """Read all registry values for a specific labware entry"""
        entry_path = f"{self.BASE_KEY_PATH}\\{entry_name}"
        values = {}

        try:
            with winreg.OpenKey(self.hkey, entry_path, 0, winreg.KEY_READ) as key:
                i = 0
                while True:
                    try:
                        name, value, reg_type = winreg.EnumValue(key, i)
                        values[name] = value
                        i += 1
                    except WindowsError:
                        break
        except FileNotFoundError:
            logger.error(f"Labware entry not found: {entry_name}")
        except PermissionError:
            logger.error("Permission denied. Run as administrator.")

        return values

    def get_labware_entry_object(self, entry_name: str) -> Optional[LabwareEntry]:
        """Get a LabwareEntry object from the registry"""
        registry_data = self.read_labware_entry(entry_name)
        if not registry_data:
            return None
        return LabwareEntry.from_registry_dict(entry_name, registry_data)

    def create_labware_entry(self, labware: LabwareEntry) -> bool:
        """Create a new labware entry in the registry"""
        entry_path = f"{self.BASE_KEY_PATH}\\{labware.name}"

        try:
            with winreg.CreateKey(self.hkey, entry_path) as key:
                registry_data = labware.to_registry_dict()

                for name, value in registry_data.items():
                    if isinstance(value, str):
                        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
                    elif isinstance(value, int):
                        winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)
                    elif isinstance(value, float):
                        # Store floats as strings in REG_SZ format (as per Velocity11 convention)
                        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, f"{value:.5f}")

                logger.info(f"Successfully created labware entry: {labware.name}")
                return True

        except PermissionError:
            logger.error("Permission denied. Run as administrator.")
            return False
        except Exception as e:
            logger.error(f"Error creating labware entry: {e}")
            return False

    def update_labware_entry(self, entry_name: str, updates: Dict[str, Any]) -> bool:
        """Update specific values in an existing labware entry"""
        entry_path = f"{self.BASE_KEY_PATH}\\{entry_name}"

        try:
            with winreg.OpenKey(self.hkey, entry_path, 0, winreg.KEY_SET_VALUE) as key:
                for name, value in updates.items():
                    if isinstance(value, str):
                        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
                    elif isinstance(value, int):
                        winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)
                    elif isinstance(value, float):
                        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, f"{value:.5f}")

                logger.info(f"Successfully updated labware entry: {entry_name}")
                return True

        except FileNotFoundError:
            logger.error(f"Labware entry not found: {entry_name}")
            return False
        except PermissionError:
            logger.error("Permission denied. Run as administrator.")
            return False
        except Exception as e:
            logger.error(f"Error updating labware entry: {e}")
            return False

    def clone_labware_entry(
        self, source_name: str, new_name: str, modifications: Dict[str, Any] = None
    ) -> bool:
        """Clone an existing labware entry with optional modifications"""
        source_entry = self.get_labware_entry_object(source_name)
        if not source_entry:
            logger.error(f"Source labware entry not found: {source_name}")
            return False

        # Create new entry with modified name
        new_entry = LabwareEntry.from_registry_dict(
            new_name, source_entry.to_registry_dict()
        )
        new_entry.name = new_name

        # Apply modifications if provided
        if modifications:
            for field, value in modifications.items():
                if hasattr(new_entry, field):
                    setattr(new_entry, field, value)
                else:
                    logger.warning(f"Unknown field in modifications: {field}")

        return self.create_labware_entry(new_entry)

    def delete_labware_entry(self, entry_name: str) -> bool:
        """Delete a labware entry from the registry"""
        entry_path = f"{self.BASE_KEY_PATH}\\{entry_name}"

        try:
            winreg.DeleteKey(self.hkey, entry_path)
            logger.info(f"Successfully deleted labware entry: {entry_name}")
            return True
        except FileNotFoundError:
            logger.error(f"Labware entry not found: {entry_name}")
            return False
        except PermissionError:
            logger.error("Permission denied. Run as administrator.")
            return False
        except Exception as e:
            logger.error(f"Error deleting labware entry: {e}")
            return False

    def export_labware_to_json(self, entry_name: str, filepath: str) -> bool:
        """Export a labware entry to JSON file"""
        data = self.read_labware_entry(entry_name)
        if not data:
            return False

        try:
            with open(filepath, "w") as f:
                json.dump({entry_name: data}, f, indent=2)
            logger.info(f"Exported labware entry to: {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error exporting to JSON: {e}")
            return False

    def import_labware_from_json(self, filepath: str) -> bool:
        """Import labware entries from JSON file"""
        try:
            with open(filepath, "r") as f:
                data = json.load(f)

            for entry_name, values in data.items():
                entry_path = f"{self.BASE_KEY_PATH}\\{entry_name}"
                with winreg.CreateKey(self.hkey, entry_path) as key:
                    for name, value in values.items():
                        if isinstance(value, str):
                            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
                        elif isinstance(value, int):
                            winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)
                        elif isinstance(value, float):
                            winreg.SetValueEx(
                                key, name, 0, winreg.REG_SZ, f"{value:.5f}"
                            )

            logger.info(f"Successfully imported labware entries from: {filepath}")
            return True

        except Exception as e:
            logger.error(f"Error importing from JSON: {e}")
            return False


# Predefined labware templates based on common configurations
class LabwareTemplates:
    """Predefined templates for common labware types"""

    @staticmethod
    def plate_96_well(
        name: str, well_volume: float = 200.0, manufacturer_part: str = ""
    ) -> LabwareEntry:
        """Template for standard 96-well plate"""
        return LabwareEntry(
            name=name,
            base_class=1,  # Plate
            number_of_wells=96,
            manufacturer_part_number=manufacturer_part,
            well_tip_volume=well_volume,
            can_be_sealed=1,
            can_have_lid=1,
            x_well_to_well=9.00000,
            y_well_to_well=9.00000,
            check_plate_orientation=1,
        )

    @staticmethod
    def plate_384_well(
        name: str, well_volume: float = 50.0, manufacturer_part: str = ""
    ) -> LabwareEntry:
        """Template for 384-well plate"""
        return LabwareEntry(
            name=name,
            base_class=1,  # Plate
            number_of_wells=384,
            manufacturer_part_number=manufacturer_part,
            well_tip_volume=well_volume,
            can_be_sealed=1,
            can_have_lid=1,
            x_well_to_well=4.50000,
            y_well_to_well=4.50000,
            check_plate_orientation=1,
            # 384-well specific adjustments
            bc_gripper_holding_plate_position=4.25000,
            bc_r_gripper_holding_plate_position=8.25000,
        )

    @staticmethod
    def plate_1536_well(name: str, manufacturer_part: str = "") -> LabwareEntry:
        """Template for 1536-well plate (like the Greiner example)"""
        return LabwareEntry(
            name=name,
            base_class=1,  # Plate
            number_of_wells=1536,
            manufacturer_part_number=manufacturer_part,
            a1_notch=1,
            h1_notch=1,
            well_tip_volume=0.00000,  # Typically very small volume
            can_be_sealed=0,
            can_have_lid=0,
            x_well_to_well=2.25000,  # Typical for 1536-well
            y_well_to_well=2.25000,
            check_plate_orientation=1,
            robot_handling_speed=2,  # Slower handling for precision
            disposable_tip_length=20.00000,
            # Adjusted gripper positions for smaller pitch
            bc_r_robot_gripper_offset=5.00000,
            bc_r_sensor_offset=7.00000,
            bc_sensor_offset=4.00000,
        )

    @staticmethod
    def tip_box_96(
        name: str, tip_capacity: int = 300, manufacturer_part: str = ""
    ) -> LabwareEntry:
        """Template for 96-tip box"""
        return LabwareEntry(
            name=name,
            base_class=6,  # Tip box
            number_of_wells=96,
            manufacturer_part_number=manufacturer_part,
            tip_capacity=tip_capacity,
            third_party_tip_capacity=tip_capacity,
            tipbox_source=1,
            x_well_to_well=9.00000,
            y_well_to_well=9.00000,
            disposable_tip_length=38.20000,
            z_tip_attach_offset=-1.00000,
        )

    @staticmethod
    def tip_box_384(
        name: str, tip_capacity: int = 60, manufacturer_part: str = ""
    ) -> LabwareEntry:
        """Template for 384-tip box"""
        return LabwareEntry(
            name=name,
            base_class=6,  # Tip box
            number_of_wells=384,
            manufacturer_part_number=manufacturer_part,
            tip_capacity=tip_capacity,
            third_party_tip_capacity=tip_capacity,
            tipbox_source=1,
            x_well_to_well=4.50000,
            y_well_to_well=4.50000,
            disposable_tip_length=38.20000,
            z_tip_attach_offset=-1.00000,
            # 384 tip box specific settings
            bc_gripper_holding_plate_position=4.25000,
            bc_gripper_holding_stack_position=4.50000,
            bc_r_gripper_holding_plate_position=8.25000,
            bc_r_gripper_holding_stack_position=8.50000,
        )

    @staticmethod
    def lid(name: str, compatible_plate_class: str = "96-well") -> LabwareEntry:
        """Template for plate lid"""
        return LabwareEntry(
            name=name,
            base_class=7,  # Lid
            number_of_wells=96 if "96" in compatible_plate_class else 384,
            can_be_mounted=0,
            can_be_sealed=0,
            can_have_lid=0,
            can_mount=0,
            # Lid-specific gripper positions
            bc_gripper_holding_lid_position=3.50000,
            bc_r_gripper_holding_lid_position=8.00000,
            mounted_lid_robot_gripper_offset=3.00000,
        )


def main():
    """Example usage with the complete Velocity11 labware registry manager"""
    manager = LabwareRegistryManager()

    print("=== Velocity11 Labware Registry Manager ===\n")

    # List existing entries
    print("Existing labware entries:")
    entries = manager.list_labware_entries()
    for i, entry in enumerate(entries, 1):
        print(f"  {i:2d}. {entry}")

    if not entries:
        print("  No entries found. Make sure you're running as administrator.")
        return

    # Example 1: Read an existing entry as an object
    print(f"\n--- Example 1: Reading '{entries[0]}' as LabwareEntry object ---")
    labware_obj = manager.get_labware_entry_object(entries[0])
    if labware_obj:
        print(f"Name: {labware_obj.name}")
        print(f"Base Class: {labware_obj.base_class}")
        print(f"Number of Wells: {labware_obj.number_of_wells}")
        print(f"Manufacturer Part: {labware_obj.manufacturer_part_number}")
        print(f"Well Volume: {labware_obj.well_tip_volume}")

    # Example 2: Create a new labware using templates
    print("\n--- Example 2: Creating new labware from templates ---")

    # Create a custom 96-well plate
    new_plate = LabwareTemplates.plate_96_well(
        name="Custom 96-Well Deep Well",
        well_volume=2000.0,
        manufacturer_part="CUSTOM-96-DW",
    )
    new_plate.description = "Custom deep well plate for high volume applications"

    print(f"Creating: {new_plate.name}")
    if manager.create_labware_entry(new_plate):
        print("✓ Successfully created!")

    # Create a custom tip box
    new_tipbox = LabwareTemplates.tip_box_384(
        name="Custom 384 Tip Box High Volume",
        tip_capacity=200,
        manufacturer_part="CUSTOM-384-TIP",
    )

    print(f"Creating: {new_tipbox.name}")
    if manager.create_labware_entry(new_tipbox):
        print("✓ Successfully created!")

    # Example 3: Clone an existing entry with modifications
    if len(entries) > 0:
        print(f"\n--- Example 3: Cloning '{entries[0]}' with modifications ---")
        clone_name = f"{entries[0]} - Modified Clone"
        modifications = {
            "description": "Cloned and modified entry",
            "robot_handling_speed": 1,
            "well_tip_volume": 500.0,
        }

        if manager.clone_labware_entry(entries[0], clone_name, modifications):
            print(f"✓ Successfully cloned to: {clone_name}")

    # Example 4: Export to JSON for backup
    print(f"\n--- Example 4: Exporting to JSON ---")
    if entries:
        json_file = f"{entries[0].replace(' ', '_')}_backup.json"
        if manager.export_labware_to_json(entries[0], json_file):
            print(f"✓ Exported to: {json_file}")

    print(f"\n--- Example 5: Updated entries list ---")
    updated_entries = manager.list_labware_entries()
    new_entries = [e for e in updated_entries if e not in entries]
    if new_entries:
        print("Newly created entries:")
        for entry in new_entries:
            print(f"  + {entry}")
    else:
        print("No new entries were created (check permissions)")


if __name__ == "__main__":
    main()
