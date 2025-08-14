#!/usr/bin/env python3
"""
Enhanced BravoDriver with optional visualization
Usage: Just import BravoDriverWithVisualizer instead of BravoDriver
"""

import asyncio
import json
import threading
import time
import logging
from typing import Optional
from functools import wraps

# Import your original BravoDriver
from .core import BravoDriver

logger = logging.getLogger(__name__)

try:
    import websockets

    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False


class VisualizerMixin:
    """Mixin to add visualization capabilities with minimal changes"""

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
        time.sleep(1.5)  # Give more time for connection to establish

    async def _connect_to_visualizer(self):
        """Connect to visualizer server"""
        max_retries = 5  # More retries
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

                    # Keep connection alive
                    try:
                        async for message in websocket:
                            pass  # Just keep connection alive
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

    def _send_to_visualizer(
        self, operation: str, position: int, volume: float = 0, labware_type: str = None
    ):
        """Send operation to visualizer"""
        if not self.with_visualizer or not self._ws_client or not self._ws_loop:
            return

        message = {
            "command": "simulate_operation",
            "operation": operation,
            "position": position,
            "volume": volume,
        }

        if labware_type:
            message["labware_type"] = labware_type

        try:
            future = asyncio.run_coroutine_threadsafe(
                self._ws_client.send(json.dumps(message)), self._ws_loop
            )
            future.result(timeout=0.1)  # Quick timeout
        except Exception:
            pass  # Fail silently


def visualizer_method(operation_name: str):
    """Decorator to add visualization to BravoDriver methods"""

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # Extract plate_location and volume from kwargs/args
            if hasattr(self, "with_visualizer") and self.with_visualizer:
                try:
                    # Try to get plate_location from different argument positions
                    plate_location = None
                    volume = 0
                    labware_type = None

                    if operation_name in ["aspirate", "dispense"]:
                        if len(args) >= 2:
                            volume = args[0]
                            plate_location = args[1]
                        else:
                            volume = kwargs.get("volume", 0)
                            plate_location = kwargs.get("plate_location", 1)
                    elif operation_name in ["tips_on", "tips_off", "move_to_location"]:
                        if len(args) >= 1:
                            plate_location = args[0]
                        else:
                            plate_location = kwargs.get("plate_location", 1)
                    elif operation_name == "set_labware":
                        if len(args) >= 2:
                            plate_location = args[0]
                            labware_type = args[1]
                        else:
                            plate_location = kwargs.get("plate_location", 1)
                            labware_type = kwargs.get("labware_type", "empty")

                    if plate_location is not None:
                        if operation_name == "set_labware":
                            # Special handling for set_labware
                            self._send_to_visualizer(
                                "set_labware",
                                plate_location,
                                0,
                                labware_type=labware_type,
                            )
                        else:
                            self._send_to_visualizer(
                                operation_name, plate_location, volume
                            )

                except Exception:
                    pass  # Fail silently if visualization fails

            # Call original method
            return func(self, *args, **kwargs)

        return wrapper

    return decorator


class BravoDriverWithVisualizer(VisualizerMixin, BravoDriver):
    """
    Enhanced BravoDriver with optional visualization

    Usage:
        # Normal use (no visualization)
        driver = BravoDriverWithVisualizer(simulation_mode=True)

        # With visualization
        driver = BravoDriverWithVisualizer(simulation_mode=True, with_visualizer=True)
    """

    # Add visualizer decorators to key methods
    @visualizer_method("aspirate")
    def aspirate(self, *args, **kwargs):
        return super().aspirate(*args, **kwargs)

    @visualizer_method("dispense")
    def dispense(self, *args, **kwargs):
        return super().dispense(*args, **kwargs)

    @visualizer_method("tips_on")
    def tips_on(self, *args, **kwargs):
        return super().tips_on(*args, **kwargs)

    @visualizer_method("tips_off")
    def tips_off(self, *args, **kwargs):
        return super().tips_off(*args, **kwargs)

    @visualizer_method("move_to_location")
    def move_to_location(self, *args, **kwargs):
        return super().move_to_location(*args, **kwargs)

    @visualizer_method("set_labware")
    def set_labware_at_location(self, *args, **kwargs):
        return super().set_labware_at_location(*args, **kwargs)


def start_visualizer_server(demo=False, port=8765, http_port=8080):
    """Helper to start visualizer server"""
    try:
        from .deck_visualizer.visualizer_server import BravoDeckVisualizer

        def run_server():
            visualizer = BravoDeckVisualizer(port=port)
            asyncio.run(
                visualizer.start(run_demo=demo, serve_files=True, http_port=http_port)
            )

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()

        # Give server more time to start properly
        logger.info("🚀 Starting visualizer server...")
        time.sleep(3)
        logger.info("🌐 Visualizer server started - check your browser!")
        logger.info(f"📡 WebSocket server: ws://localhost:{port}")
        logger.info(f"🌍 Web interface: http://localhost:{http_port}")
        return True

    except Exception as e:
        logger.warning(f"Could not start visualizer server: {e}")
        return False
