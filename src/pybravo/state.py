from typing import Any, Dict, Optional, List
import logging
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import threading


class OperationStatus(Enum):
    """Enumeration of possible operation statuses"""

    IDLE = "idle"
    ASPIRATING = "aspirating"
    DISPENSING = "dispensing"
    MIXING = "mixing"
    WASHING = "washing"
    MOVING = "moving"
    PICKING = "picking"
    PLACING = "placing"
    PUMPING = "pumping"
    ERROR = "error"


class LabwareType(Enum):
    """Enumeration of common labware types"""

    MICROPLATE_96 = "microplate_96"
    MICROPLATE_384 = "microplate_384"
    DEEPWELL_96 = "deepwell_96"
    RESERVOIR = "reservoir"
    TIP_RACK = "tip_rack"
    EMPTY = "empty"
    UNKNOWN = "unknown"


@dataclass
class VolumeInfo:
    """Information about volume operations"""

    current_volume: float = 0.0
    aspirated_volume: float = 0.0
    dispensed_volume: float = 0.0
    last_operation_volume: float = 0.0
    total_aspirated: float = 0.0
    total_dispensed: float = 0.0

    def reset(self):
        """Reset all volume tracking"""
        self.__init__()


@dataclass
class TipInfo:
    """Information about tip status"""

    tips_loaded: bool = False
    tip_type: Optional[str] = None
    tip_volume: Optional[float] = None
    tip_count: int = 0
    last_tip_operation: Optional[str] = None

    def reset(self):
        """Reset tip information"""
        self.__init__()


@dataclass
class OperationInfo:
    """Information about current operation"""

    status: OperationStatus = OperationStatus.IDLE
    operation_details: Dict[str, Any] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    estimated_duration: Optional[float] = None
    progress: float = 0.0

    def start_operation(self, status: OperationStatus, details: Dict[str, Any] = None):
        """Start a new operation"""
        self.status = status
        self.operation_details = details or {}
        self.start_time = datetime.now()
        self.progress = 0.0

    def complete_operation(self):
        """Mark operation as complete"""
        self.status = OperationStatus.IDLE
        self.operation_details.clear()
        self.start_time = None
        self.progress = 100.0

    def update_progress(self, progress: float):
        """Update operation progress"""
        self.progress = max(0, min(100, progress))


@dataclass
class Nest:
    """Represents a single nest position on the Bravo deck"""

    nest_id: int
    labware_type: LabwareType = LabwareType.EMPTY
    labware_name: Optional[str] = None
    volume_info: VolumeInfo = field(default_factory=VolumeInfo)
    tip_info: TipInfo = field(default_factory=TipInfo)
    operation_info: OperationInfo = field(default_factory=OperationInfo)
    custom_properties: Dict[str, Any] = field(default_factory=dict)
    last_accessed: Optional[datetime] = None

    def __post_init__(self):
        """Initialize after dataclass creation"""
        if self.volume_info is None:
            self.volume_info = VolumeInfo()
        if self.tip_info is None:
            self.tip_info = TipInfo()
        if self.operation_info is None:
            self.operation_info = OperationInfo()

    def set_labware(
        self, labware_type: LabwareType, labware_name: Optional[str] = None
    ):
        """Set the labware for this nest"""
        self.labware_type = labware_type
        self.labware_name = labware_name
        self.last_accessed = datetime.now()
        logging.info(f"Nest {self.nest_id}: Set labware to {labware_type.value}")

    def start_operation(
        self, operation: OperationStatus, details: Dict[str, Any] = None
    ):
        """Start an operation on this nest"""
        self.operation_info.start_operation(operation, details)
        self.last_accessed = datetime.now()
        logging.info(f"Nest {self.nest_id}: Started {operation.value} operation")

    def complete_operation(self):
        """Complete the current operation"""
        operation = self.operation_info.status
        self.operation_info.complete_operation()
        self.last_accessed = datetime.now()
        logging.info(f"Nest {self.nest_id}: Completed {operation.value} operation")

    def update_volume(self, aspirated: float = 0, dispensed: float = 0):
        """Update volume information"""
        self.volume_info.aspirated_volume += aspirated
        self.volume_info.dispensed_volume += dispensed
        self.volume_info.total_aspirated += aspirated
        self.volume_info.total_dispensed += dispensed
        self.volume_info.current_volume += aspirated - dispensed
        self.volume_info.last_operation_volume = max(aspirated, dispensed)
        self.last_accessed = datetime.now()

    def update_tips(
        self, tips_on: bool = False, tip_type: str = None, tip_count: int = 0
    ):
        """Update tip information"""
        self.tip_info.tips_loaded = tips_on
        if tip_type:
            self.tip_info.tip_type = tip_type
        if tip_count > 0:
            self.tip_info.tip_count = tip_count
        self.tip_info.last_tip_operation = "tips_on" if tips_on else "tips_off"
        self.last_accessed = datetime.now()

    def reset_nest(self):
        """Reset nest to empty state"""
        self.labware_type = LabwareType.EMPTY
        self.labware_name = None
        self.volume_info.reset()
        self.tip_info.reset()
        self.operation_info.complete_operation()
        self.custom_properties.clear()
        self.last_accessed = datetime.now()

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the nest state"""
        return {
            "nest_id": self.nest_id,
            "labware_type": self.labware_type.value,
            "labware_name": self.labware_name,
            "operation_status": self.operation_info.status.value,
            "current_volume": self.volume_info.current_volume,
            "tips_loaded": self.tip_info.tips_loaded,
            "last_accessed": (
                self.last_accessed.isoformat() if self.last_accessed else None
            ),
        }


class BravoDeckState:
    """State machine for tracking the entire Bravo deck state"""

    def __init__(self, num_nests: int = 9):
        self.num_nests = num_nests
        self.nests: Dict[int, Nest] = {}
        self._lock = threading.RLock()  # Thread-safe operations
        self._initialize_nests()

        # Global state tracking
        self.global_operation_count = 0
        self.error_count = 0
        self.last_error: Optional[str] = None
        self.initialization_time = datetime.now()

        logging.info(f"BravoDeckState initialized with {num_nests} nests")

    def _initialize_nests(self):
        """Initialize all nests"""
        with self._lock:
            for i in range(1, self.num_nests + 1):
                self.nests[i] = Nest(nest_id=i)

    def get_nest(self, nest_id: int) -> Optional[Nest]:
        """Get a specific nest by ID"""
        if not (1 <= nest_id <= self.num_nests):
            logging.error(f"Invalid nest ID: {nest_id}")
            return None
        return self.nests.get(nest_id)

    def set_labware_at_nest(
        self, nest_id: int, labware_type: str, labware_name: str = None
    ):
        """Set labware at a specific nest"""
        with self._lock:
            nest = self.get_nest(nest_id)
            if nest:
                # Convert string to enum
                try:
                    labware_enum = LabwareType(labware_type.lower())
                except ValueError:
                    labware_enum = LabwareType.UNKNOWN
                    logging.warning(
                        f"Unknown labware type: {labware_type}, using UNKNOWN"
                    )

                nest.set_labware(labware_enum, labware_name)
                return True
            return False

    def start_operation_at_nest(
        self, nest_id: int, operation: str, details: Dict[str, Any] = None
    ):
        """Start an operation at a specific nest"""
        with self._lock:
            nest = self.get_nest(nest_id)
            if nest:
                try:
                    operation_enum = OperationStatus(operation.lower())
                    nest.start_operation(operation_enum, details or {})
                    self.global_operation_count += 1
                    return True
                except ValueError:
                    logging.error(f"Unknown operation: {operation}")
                    return False
            return False

    def complete_operation_at_nest(self, nest_id: int):
        """Complete operation at a specific nest"""
        with self._lock:
            nest = self.get_nest(nest_id)
            if nest:
                nest.complete_operation()
                return True
            return False

    def update_volume_at_nest(
        self, nest_id: int, aspirated: float = 0, dispensed: float = 0
    ):
        """Update volume at a specific nest"""
        with self._lock:
            nest = self.get_nest(nest_id)
            if nest:
                nest.update_volume(aspirated, dispensed)
                return True
            return False

    def update_tips_at_nest(self, nest_id: int, tips_on: bool, tip_type: str = None):
        """Update tip status at a specific nest"""
        with self._lock:
            nest = self.get_nest(nest_id)
            if nest:
                nest.update_tips(tips_on, tip_type)
                return True
            return False

    def get_active_operations(self) -> List[Dict[str, Any]]:
        """Get all nests with active operations"""
        with self._lock:
            active_ops = []
            for nest in self.nests.values():
                if nest.operation_info.status != OperationStatus.IDLE:
                    active_ops.append(
                        {
                            "nest_id": nest.nest_id,
                            "operation": nest.operation_info.status.value,
                            "details": nest.operation_info.operation_details,
                            "progress": nest.operation_info.progress,
                            "start_time": nest.operation_info.start_time,
                        }
                    )
            return active_ops

    def get_nests_with_labware(self) -> List[Dict[str, Any]]:
        """Get all nests that have labware"""
        with self._lock:
            labware_nests = []
            for nest in self.nests.values():
                if nest.labware_type != LabwareType.EMPTY:
                    labware_nests.append(
                        {
                            "nest_id": nest.nest_id,
                            "labware_type": nest.labware_type.value,
                            "labware_name": nest.labware_name,
                        }
                    )
            return labware_nests

    def get_nests_with_tips(self) -> List[int]:
        """Get all nest IDs that have tips loaded"""
        with self._lock:
            return [
                nest.nest_id
                for nest in self.nests.values()
                if nest.tip_info.tips_loaded
            ]

    def get_deck_summary(self) -> Dict[str, Any]:
        """Get a complete summary of the deck state"""
        with self._lock:
            return {
                "deck_info": {
                    "num_nests": self.num_nests,
                    "initialization_time": self.initialization_time.isoformat(),
                    "global_operation_count": self.global_operation_count,
                    "error_count": self.error_count,
                    "last_error": self.last_error,
                },
                "active_operations": len(self.get_active_operations()),
                "nests_with_labware": len(self.get_nests_with_labware()),
                "nests_with_tips": len(self.get_nests_with_tips()),
                "nests": {
                    nest_id: nest.get_summary() for nest_id, nest in self.nests.items()
                },
            }

    def reset_all_nests(self):
        """Reset all nests to empty state"""
        with self._lock:
            for nest in self.nests.values():
                nest.reset_nest()
            self.global_operation_count = 0
            self.error_count = 0
            self.last_error = None
            logging.info("All nests reset to empty state")

    def log_error(self, error_message: str, nest_id: int = None):
        """Log an error and update error tracking"""
        with self._lock:
            self.error_count += 1
            self.last_error = error_message

            if nest_id and self.get_nest(nest_id):
                self.nests[nest_id].operation_info.status = OperationStatus.ERROR
                self.nests[nest_id].operation_info.operation_details[
                    "error"
                ] = error_message

            logging.error(
                f"Deck Error: {error_message}"
                + (f" (Nest {nest_id})" if nest_id else "")
            )

    def export_state_to_dict(self) -> Dict[str, Any]:
        """Export complete state for serialization"""
        with self._lock:
            return {
                "deck_state": self.get_deck_summary(),
                "timestamp": datetime.now().isoformat(),
                "version": "1.0",
            }

    def find_empty_nests(self) -> List[int]:
        """Find all empty nest positions"""
        with self._lock:
            return [
                nest.nest_id
                for nest in self.nests.values()
                if nest.labware_type == LabwareType.EMPTY
            ]

    def find_nests_by_labware_type(self, labware_type: str) -> List[int]:
        """Find nests containing specific labware type"""
        with self._lock:
            try:
                target_type = LabwareType(labware_type.lower())
                return [
                    nest.nest_id
                    for nest in self.nests.values()
                    if nest.labware_type == target_type
                ]
            except ValueError:
                logging.error(f"Unknown labware type: {labware_type}")
                return []
