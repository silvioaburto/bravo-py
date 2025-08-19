#!/usr/bin/env python3
"""
Enhanced BravoDriver with integrated state management and visualization
Usage: Replace your BravoDriver import with this enhanced version
"""

import asyncio
import json
import threading
import time
import logging
from typing import Optional, Dict, Any
from functools import wraps

# Import your original BravoDriver and state classes
from .core import BravoDriver
from .state import BravoDeckState, LabwareType, OperationStatus

logger = logging.getLogger(__name__)

try:
    import websockets

    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False


class VisualizerMixin:
    """Enhanced mixin to add visualization capabilities with state management integration"""

    def __init__(self, *args, with_visualizer=False, visualizer_port=8765, **kwargs):
        # Call original __init__
        super().__init__(*args, **kwargs)

        # Add visualizer attributes
        self.with_visualizer = with_visualizer and HAS_WEBSOCKETS
        self.visualizer_port = visualizer_port
        self._ws_client = None
        self._ws_loop = None
        self._ws_thread = None

        if self.with_visualizer:
            self._start_visualizer_connection()

    def _start_visualizer_connection(self):
        """Start WebSocket client in background thread"""

        def run_client():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._ws_loop = loop
            loop.run_until_complete(self._connect_to_visualizer())

        self._ws_thread = threading.Thread(target=run_client, daemon=True)
        self._ws_thread.start()
        time.sleep(2)  # Give more time for connection to establish

    async def _connect_to_visualizer(self):
        """Connect to visualizer server"""
        max_retries = 10
        retry_count = 0

        while retry_count < max_retries:
            try:
                uri = f"ws://localhost:{self.visualizer_port}"
                logger.info(
                    f"Attempting to connect to visualizer at {uri} (attempt {retry_count + 1})"
                )

                async with websockets.connect(uri, ping_interval=None) as websocket:
                    self._ws_client = websocket
                    logger.info("✅ Connected to visualizer")

                    # Send initial state sync
                    await self._sync_state_to_visualizer()

                    # Keep connection alive
                    try:
                        async for message in websocket:
                            # Handle any incoming messages from visualizer
                            await self._handle_visualizer_message(message)
                    except websockets.exceptions.ConnectionClosed:
                        logger.info("Visualizer connection closed")
                        break

            except (ConnectionRefusedError, OSError) as e:
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(
                        f"Visualizer not ready, retrying in 2s... ({retry_count}/{max_retries})"
                    )
                    await asyncio.sleep(2)
                else:
                    logger.warning(
                        "Could not connect to visualizer - continuing without visualization"
                    )
                    break
            except Exception as e:
                logger.error(f"Visualizer connection error: {e}")
                break

    async def _handle_visualizer_message(self, message: str):
        """Handle incoming messages from visualizer"""
        try:
            data = json.loads(message)
            # Handle any commands from the visualizer if needed
            logger.debug(f"Received from visualizer: {data}")
        except Exception as e:
            logger.error(f"Error handling visualizer message: {e}")

    async def _sync_state_to_visualizer(self):
        """Sync current deck state to visualizer"""
        if not self.deck_state:
            return

        try:
            # Send deck state sync
            deck_summary = self.deck_state.get_deck_summary()

            sync_message = {
                "command": "sync_deck_state",
                "deck_state": deck_summary,
                "timestamp": time.time(),
            }

            await self._ws_client.send(json.dumps(sync_message))
            logger.info("Synced deck state to visualizer")

        except Exception as e:
            logger.error(f"Error syncing state to visualizer: {e}")

    def _send_to_visualizer(
        self,
        operation: str,
        position: int,
        volume: float = 0,
        labware_type: str = None,
        **kwargs,
    ):
        """Send operation to visualizer with enhanced state information"""
        if not self.with_visualizer or not self._ws_client or not self._ws_loop:
            return

        # Get current nest state for additional context
        nest_state = None
        if hasattr(self, "deck_state") and self.deck_state:
            nest = self.deck_state.get_nest(position)
            if nest:
                nest_state = {
                    "labware_type": nest.labware_type.value,
                    "labware_name": nest.labware_name,
                    "current_volume": nest.volume_info.current_volume,
                    "tips_loaded": nest.tip_info.tips_loaded,
                    "operation_status": nest.operation_info.status.value,
                }

        message = {
            "command": "simulate_operation",
            "operation": operation,
            "position": position,
            "volume": volume,
            "nest_state": nest_state,
            "timestamp": time.time(),
        }

        if labware_type:
            message["labware_type"] = labware_type

        # Add any additional kwargs
        message.update(kwargs)

        try:
            future = asyncio.run_coroutine_threadsafe(
                self._ws_client.send(json.dumps(message)), self._ws_loop
            )
            future.result(timeout=0.5)  # Slightly longer timeout
        except Exception as e:
            logger.debug(f"Failed to send to visualizer: {e}")


def visualizer_method(operation_name: str):
    """Enhanced decorator to add visualization with state awareness"""

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Extract parameters before calling the method
            operation_params = extract_operation_params(operation_name, args, kwargs)

            # Call original method first
            result = func(self, *args, **kwargs)

            # Send to visualizer after successful execution
            if hasattr(self, "with_visualizer") and self.with_visualizer:
                try:
                    if operation_params:
                        self._send_to_visualizer(**operation_params)
                except Exception as e:
                    logger.debug(f"Visualization failed for {operation_name}: {e}")

            return result

        return wrapper

    return decorator


def extract_operation_params(
    operation_name: str, args: tuple, kwargs: dict
) -> Optional[Dict[str, Any]]:
    """Extract operation parameters for visualization"""
    try:
        if operation_name in ["aspirate", "dispense"]:
            volume = args[0] if len(args) > 0 else kwargs.get("volume", 0)
            position = args[1] if len(args) > 1 else kwargs.get("plate_location", 1)
            return {"operation": operation_name, "position": position, "volume": volume}
        elif operation_name in ["tips_on", "tips_off", "move_to_location"]:
            position = args[0] if len(args) > 0 else kwargs.get("plate_location", 1)
            tip_type = (
                kwargs.get("tip_type", "standard")
                if operation_name == "tips_on"
                else None
            )
            params = {"operation": operation_name, "position": position, "volume": 0}
            if tip_type:
                params["tip_type"] = tip_type
            return params
        elif operation_name == "set_labware_at_location":
            position = args[0] if len(args) > 0 else kwargs.get("plate_location", 1)
            labware_type = (
                args[1] if len(args) > 1 else kwargs.get("labware_type", "empty")
            )
            return {
                "operation": "set_labware",
                "position": position,
                "volume": 0,
                "labware_type": labware_type,
            }
        elif operation_name in ["mix", "wash"]:
            volume = args[0] if len(args) > 0 else kwargs.get("volume", 0)
            position = None
            # For mix and wash, position might be in different argument positions
            for i, arg in enumerate(args):
                if isinstance(arg, int) and 1 <= arg <= 9:
                    position = arg
                    break
            if position is None:
                position = kwargs.get("plate_location", 1)

            return {"operation": operation_name, "position": position, "volume": volume}
    except Exception as e:
        logger.debug(f"Error extracting params for {operation_name}: {e}")

    return None


class BravoDriverWithVisualization(VisualizerMixin, BravoDriver):
    """
    Enhanced BravoDriver with integrated state management and visualization

    Usage:
        # Normal use (no visualization)
        driver = BravoDriverWithVisualization(simulation_mode=True)

        # With visualization
        driver = BravoDriverWithVisualization(simulation_mode=True, with_visualizer=True)

        # With custom visualizer port
        driver = BravoDriverWithVisualization(
            simulation_mode=True,
            with_visualizer=True,
            visualizer_port=8766
        )
    """

    def __init__(self, *args, **kwargs):
        # Ensure state tracking is enabled when using visualizer
        if kwargs.get("with_visualizer", False):
            kwargs.setdefault("enable_state_tracking", True)

        super().__init__(*args, **kwargs)

        # Enhanced state synchronization
        if self.with_visualizer and self.deck_state:
            logger.info(
                "Enhanced BravoDriver with visualization and state tracking initialized"
            )

    # Enhanced method decorators with better state integration
    @visualizer_method("aspirate")
    def aspirate(self, *args, **kwargs):
        return super().aspirate(*args, **kwargs)

    @visualizer_method("dispense")
    def dispense(self, *args, **kwargs):
        return super().dispense(*args, **kwargs)

    @visualizer_method("mix")
    def mix(self, *args, **kwargs):
        return super().mix(*args, **kwargs)

    @visualizer_method("wash")
    def wash(self, *args, **kwargs):
        return super().wash(*args, **kwargs)

    @visualizer_method("tips_on")
    def tips_on(self, *args, **kwargs):
        return super().tips_on(*args, **kwargs)

    @visualizer_method("tips_off")
    def tips_off(self, *args, **kwargs):
        return super().tips_off(*args, **kwargs)

    @visualizer_method("move_to_location")
    def move_to_location(self, *args, **kwargs):
        return super().move_to_location(*args, **kwargs)

    @visualizer_method("set_labware_at_location")
    def set_labware_at_location(self, *args, **kwargs):
        return super().set_labware_at_location(*args, **kwargs)

    @visualizer_method("pick_and_place")
    def pick_and_place(self, *args, **kwargs):
        return super().pick_and_place(*args, **kwargs)

    def sync_visualizer_state(self):
        """Manually sync current state to visualizer"""
        if self.with_visualizer and self._ws_client and self._ws_loop:
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self._sync_state_to_visualizer(), self._ws_loop
                )
                future.result(timeout=1.0)
                logger.info("Manual state sync to visualizer completed")
            except Exception as e:
                logger.error(f"Manual state sync failed: {e}")

    def set_labware_with_visualization(
        self, nest_id: int, labware_type: str, labware_name: str = None
    ):
        """Enhanced labware setting with immediate visualization update"""
        # Update state first
        success = self.set_labware_at_nest(nest_id, labware_type, labware_name)

        if success and self.with_visualizer:
            # Send immediate update to visualizer
            self._send_to_visualizer(
                "set_labware",
                nest_id,
                labware_type=labware_type,
                labware_name=labware_name,
            )

        return success

    def get_visualization_status(self) -> Dict[str, Any]:
        """Get current visualization connection status"""
        return {
            "visualizer_enabled": self.with_visualizer,
            "visualizer_connected": self._ws_client is not None,
            "visualizer_port": self.visualizer_port,
            "state_tracking_enabled": self.deck_state is not None,
            "thread_active": self._ws_thread is not None and self._ws_thread.is_alive(),
        }


def start_enhanced_visualizer_server(
    demo=False, port=8765, http_port=8080, bravo_driver=None
):
    """Helper to start enhanced visualizer server with state integration"""
    try:
        from .enhanced_visualizer_server import BravoDeckVisualizerWithState

        def run_server():
            visualizer = BravoDeckVisualizerWithState(
                port=port, bravo_driver=bravo_driver
            )
            asyncio.run(
                visualizer.start(run_demo=demo, serve_files=True, http_port=http_port)
            )

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # Give server more time to start properly
        logger.info("🚀 Starting enhanced visualizer server with state integration...")
        time.sleep(3)
        logger.info("🌐 Enhanced visualizer server started - check your browser!")
        logger.info(f"📡 WebSocket server: ws://localhost:{port}")
        logger.info(f"🌐 Web interface: http://localhost:{http_port}")
        logger.info("🔄 State synchronization enabled")
        return True

    except Exception as e:
        logger.warning(f"Could not start enhanced visualizer server: {e}")
        return False


# Example usage and demo functions
def demo_enhanced_integration():
    """Demonstrate the enhanced integration between driver, state, and visualizer"""

    # Start the enhanced visualizer server
    logger.info("Starting enhanced visualizer server...")
    start_enhanced_visualizer_server(demo=False, port=8765, http_port=8080)

    # Give server time to start
    time.sleep(3)

    # Create driver with visualization
    logger.info("Creating enhanced driver with visualization...")
    with BravoDriverWithVisualization(
        simulation_mode=True, with_visualizer=True, enable_state_tracking=True
    ) as bravo:

        # Give connection time to establish
        time.sleep(2)

        logger.info("Setting up labware...")
        # Set up labware with visualization
        bravo.set_labware_with_visualization(1, "tip_rack", "200µL Tips")
        bravo.set_labware_with_visualization(2, "microplate_96", "Source Plate")
        bravo.set_labware_with_visualization(3, "microplate_96", "Destination Plate")
        bravo.set_labware_with_visualization(4, "reservoir", "Wash Buffer")

        time.sleep(1)

        # Perform operations
        logger.info("Performing liquid handling operations...")
        bravo.tips_on(1, tip_type="200µL")
        time.sleep(1)

        bravo.aspirate(volume=100.0, plate_location=2)
        time.sleep(1)

        bravo.dispense(volume=100.0, plate_location=3)
        time.sleep(1)

        bravo.wash(
            volume=200.0,
            empty_tips=False,
            pre_aspirate_volume=0.0,
            blow_out_volume=50.0,
            cycles=3,
            plate_location=4,
        )
        time.sleep(1)

        bravo.tips_off(1)
        time.sleep(1)

        # Show final state
        logger.info("Final deck state:")
        deck_summary = bravo.get_deck_summary()
        logger.info(
            f"Total operations: {deck_summary['deck_info']['global_operation_count']}"
        )
        logger.info(f"Labware count: {len(bravo.get_nests_with_labware())}")

        # Show visualization status
        vis_status = bravo.get_visualization_status()
        logger.info(f"Visualization status: {vis_status}")

        logger.info("Demo complete! Check the web interface for visual updates.")

        # Keep running for a bit to see the results
        time.sleep(5)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # Run the demo
    demo_enhanced_integration()
