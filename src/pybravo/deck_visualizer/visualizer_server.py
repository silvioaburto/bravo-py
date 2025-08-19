#!/usr/bin/env python3

import asyncio
import websockets
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import threading
import webbrowser
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver
from pathlib import Path

# Import the state management classes
from .state import BravoDeckState, OperationStatus, LabwareType

# Try to import BravoDriver from the correct location
try:
    from ..core import BravoDriver
except ImportError:
    try:
        from pybravo.core import BravoDriver
    except ImportError:
        # Fallback mock for standalone usage
        class BravoDriver:
            def __init__(self, simulation_mode=True):
                self.simulation_mode = simulation_mode
                print(f"Mock BravoDriver created (simulation_mode={simulation_mode})")


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuietHTTPRequestHandler(SimpleHTTPRequestHandler):
    """HTTP handler that doesn't log every request and handles template injection"""

    def __init__(self, *args, ws_port=8765, **kwargs):
        self.ws_port = ws_port
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        # Only log errors
        if args[1] != "200":
            super().log_message(format, *args)

    def do_GET(self):
        # Handle root path and inject WebSocket info
        if self.path == "/" or self.path == "/index.html":
            try:
                # Find index.html in the current directory
                html_path = os.path.join(os.getcwd(), "index.html")
                if os.path.exists(html_path):
                    with open(html_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Replace WebSocket URL in the HTML
                    content = content.replace(
                        "ws://localhost:8765", f"ws://localhost:{self.ws_port}"
                    )

                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.send_header("Cache-Control", "no-cache")
                    self.end_headers()
                    self.wfile.write(content.encode("utf-8"))
                    return
                else:
                    # If no index.html, show a helpful message
                    content = f"""
                    <!DOCTYPE html>
                    <html>
                    <head><title>Bravo Visualizer</title></head>
                    <body>
                        <h1>Bravo Deck Visualizer</h1>
                        <p>Please save your HTML file as 'index.html' in the same directory as the server.</p>
                        <p>WebSocket server running on: ws://localhost:{self.ws_port}</p>
                    </body>
                    </html>
                    """
                    self.send_response(200)
                    self.send_header("Content-type", "text/html")
                    self.end_headers()
                    self.wfile.write(content.encode("utf-8"))
                    return
            except Exception as e:
                logger.error(f"Error serving index.html: {e}")

        # For all other requests, use default handler
        super().do_GET()


def find_free_port(start_port: int) -> int:
    """Find a free port starting from start_port"""
    import socket

    port = start_port
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("localhost", port))
                return port
        except OSError:
            port += 1
            if port > start_port + 100:  # Prevent infinite loop
                raise RuntimeError(
                    f"Could not find free port starting from {start_port}"
                )


def start_file_server(directory: str, ws_port: int, http_port: int = 8080):
    """Start a simple HTTP file server in a separate thread"""
    original_dir = os.getcwd()

    try:
        # Change to the specified directory
        os.chdir(directory)

        # Find a free port
        free_port = find_free_port(http_port)

        # Create handler with WebSocket port info
        def handler_factory(*args, **kwargs):
            return QuietHTTPRequestHandler(*args, ws_port=ws_port, **kwargs)

        httpd = socketserver.TCPServer(("localhost", free_port), handler_factory)
        logger.info(f"HTTP server running on http://localhost:{free_port}")

        # Open browser after a short delay
        def open_browser():
            import time

            time.sleep(1.0)  # Wait for server to be ready
            url = f"http://localhost:{free_port}"
            logger.info(f"Opening browser to: {url}")
            webbrowser.open(url)

        # Start browser opening in background
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()

        # Serve forever
        httpd.serve_forever()

    except Exception as e:
        logger.error(f"HTTP server error: {e}")
    finally:
        # Always restore original directory
        os.chdir(original_dir)


def labware_type_to_web_format(labware_type: LabwareType) -> str:
    """Convert LabwareType enum to web-compatible format"""
    mapping = {
        LabwareType.MICROPLATE_96: "plate-96",
        LabwareType.MICROPLATE_384: "plate-384",
        LabwareType.DEEPWELL_96: "plate-96",  # Use similar visual
        LabwareType.RESERVOIR: "reservoir",
        LabwareType.TIP_RACK: "tips",
        LabwareType.EMPTY: "empty",
        LabwareType.UNKNOWN: "empty",
    }
    return mapping.get(labware_type, "empty")


def operation_status_to_web_format(status: OperationStatus) -> str:
    """Convert OperationStatus enum to web-compatible format"""
    mapping = {
        OperationStatus.ASPIRATING: "aspirate",
        OperationStatus.DISPENSING: "dispense",
        OperationStatus.MIXING: "mix",
        OperationStatus.WASHING: "wash",
        OperationStatus.MOVING: "move",
        OperationStatus.PICKING: "move",
        OperationStatus.PLACING: "move",
        OperationStatus.PUMPING: "dispense",
        OperationStatus.IDLE: "idle",
        OperationStatus.ERROR: "error",
    }
    return mapping.get(status, "idle")


class BravoDeckVisualizerWithState:
    """Enhanced WebSocket server for Bravo deck visualization with state management"""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8765,
        bravo_driver: Optional[BravoDriver] = None,
    ):
        self.host = host
        self.port = port
        self.clients = set()

        # Initialize or use provided Bravo driver
        self.bravo_driver = bravo_driver
        if self.bravo_driver is None:
            # Create a simulation driver with state tracking
            self.bravo_driver = BravoDriver(
                simulation_mode=True, enable_state_tracking=True
            )

        # Get the deck state from the driver
        self.deck_state = self.bravo_driver.get_deck_state()
        if self.deck_state is None:
            logger.warning(
                "BravoDriver doesn't have state tracking enabled, creating separate state tracker"
            )
            self.deck_state = BravoDeckState()

        # Legacy simple deck state for backward compatibility
        self.simple_deck_state = {
            i: {"labware": "empty", "volume": 0, "active": False} for i in range(1, 10)
        }

        self.current_operation = "Ready"

        # Sync initial state
        self._sync_state_to_simple_format()

    def _sync_state_to_simple_format(self):
        """Sync the BravoDeckState to simple format for web interface"""
        if not self.deck_state:
            return

        for nest_id in range(1, 10):
            nest = self.deck_state.get_nest(nest_id)
            if nest:
                # Convert labware type
                web_labware = labware_type_to_web_format(nest.labware_type)

                # Calculate total volume (current + dispensed)
                total_volume = max(0, nest.volume_info.current_volume)

                # Check if operation is active
                is_active = nest.operation_info.status != OperationStatus.IDLE

                self.simple_deck_state[nest_id] = {
                    "labware": web_labware,
                    "volume": int(total_volume),
                    "active": is_active,
                    "labware_name": nest.labware_name or "",
                    "operation": operation_status_to_web_format(
                        nest.operation_info.status
                    ),
                    "tips_loaded": nest.tip_info.tips_loaded,
                }

    def _sync_simple_to_state_format(self, nest_id: int, simple_data: dict):
        """Sync changes from simple format back to BravoDeckState"""
        if not self.deck_state:
            return

        nest = self.deck_state.get_nest(nest_id)
        if not nest:
            return

        # Convert web format back to enum
        web_to_labware = {
            "plate-96": LabwareType.MICROPLATE_96,
            "plate-384": LabwareType.MICROPLATE_384,
            "tips": LabwareType.TIP_RACK,
            "reservoir": LabwareType.RESERVOIR,
            "empty": LabwareType.EMPTY,
        }

        labware_type = web_to_labware.get(
            simple_data.get("labware", "empty"), LabwareType.EMPTY
        )
        labware_name = simple_data.get("labware_name", "")

        # Update the state
        nest.set_labware(labware_type, labware_name if labware_name else None)

        # Update volume if provided
        if "volume" in simple_data:
            current_vol = simple_data["volume"]
            nest.volume_info.current_volume = current_vol

    async def register_client(self, websocket):
        """Register a new client"""
        self.clients.add(websocket)
        logger.info(f"Client connected. Total: {len(self.clients)}")

        # Send current state to new client
        await self.send_deck_update(websocket)

    async def unregister_client(self, websocket):
        """Unregister a client"""
        self.clients.discard(websocket)
        logger.info(f"Client disconnected. Total: {len(self.clients)}")

    async def send_message(self, websocket, message: Dict[str, Any]):
        """Send message to specific client"""
        try:
            await websocket.send(json.dumps(message))
        except websockets.exceptions.ConnectionClosed:
            await self.unregister_client(websocket)

    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast to all clients"""
        if not self.clients:
            return

        disconnected = set()
        for client in self.clients.copy():
            try:
                await client.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)

        # Remove disconnected clients
        for client in disconnected:
            await self.unregister_client(client)

    async def send_deck_update(self, websocket=None):
        """Send deck state update"""
        # Sync state before sending
        self._sync_state_to_simple_format()

        # Enhanced message with state information
        message = {
            "type": "deck_update",
            "deck": self.simple_deck_state,
            "timestamp": datetime.now().isoformat(),
        }

        # Add state summary if available
        if self.deck_state:
            deck_summary = self.deck_state.get_deck_summary()
            message["state_info"] = {
                "active_operations": len(self.deck_state.get_active_operations()),
                "nests_with_labware": len(self.deck_state.get_nests_with_labware()),
                "nests_with_tips": len(self.deck_state.get_nests_with_tips()),
                "total_operations": deck_summary["deck_info"]["global_operation_count"],
                "error_count": deck_summary["deck_info"]["error_count"],
            }

        if websocket:
            await self.send_message(websocket, message)
        else:
            await self.broadcast_message(message)

    async def send_operation_glow(self, position: int, operation_type: str):
        """Send glow effect for operation"""
        message = {
            "type": f"{operation_type}_operation",
            "position": position,
            "timestamp": datetime.now().isoformat(),
        }
        await self.broadcast_message(message)

    async def broadcast_operation(self, operation: str, details: str = ""):
        """Broadcast operation status"""
        self.current_operation = operation
        message = {
            "type": "operation",
            "operation": operation,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }
        await self.broadcast_message(message)

    async def setup_default_deck(self):
        """Setup default labware layout using state management"""
        default_layout = [
            (1, LabwareType.TIP_RACK, "200µL Tips"),
            (2, LabwareType.MICROPLATE_96, "Source Plate"),
            (3, LabwareType.MICROPLATE_96, "Destination Plate"),
            (4, LabwareType.RESERVOIR, "Buffer Reservoir"),
            (6, LabwareType.MICROPLATE_384, "Assay Plate"),
            (8, LabwareType.MICROPLATE_96, "Control Plate"),
            (9, LabwareType.TIP_RACK, "1000µL Tips"),
        ]

        for position, labware_type, labware_name in default_layout:
            if self.deck_state:
                self.deck_state.set_labware_at_nest(
                    position, labware_type.value, labware_name
                )

            # Also update simple state for immediate visual update
            web_labware = labware_type_to_web_format(labware_type)
            self.simple_deck_state[position] = {
                "labware": web_labware,
                "volume": 150000 if "Plate" in labware_name else 0,  # Default volumes
                "active": False,
                "labware_name": labware_name,
                "operation": "idle",
                "tips_loaded": False,
            }

        await self.send_deck_update()

    async def simulate_operation_with_state(
        self, operation: str, position: int, volume: float = 0, **kwargs
    ):
        """Simulate a single operation using state management"""

        # Update state management
        if self.deck_state:
            operation_details = {"volume": volume, **kwargs}

            # Map operation names to OperationStatus
            op_mapping = {
                "aspirate": OperationStatus.ASPIRATING,
                "dispense": OperationStatus.DISPENSING,
                "mix": OperationStatus.MIXING,
                "wash": OperationStatus.WASHING,
                "move": OperationStatus.MOVING,
                "tips_on": OperationStatus.IDLE,  # Tips operations don't have separate status
                "tips_off": OperationStatus.IDLE,
            }

            if (
                operation in op_mapping
                and op_mapping[operation] != OperationStatus.IDLE
            ):
                self.deck_state.start_operation_at_nest(
                    position, operation, operation_details
                )

                # Update volumes
                if operation == "aspirate":
                    self.deck_state.update_volume_at_nest(position, aspirated=volume)
                elif operation == "dispense":
                    self.deck_state.update_volume_at_nest(position, dispensed=volume)

            # Handle tip operations
            if operation == "tips_on":
                tip_type = kwargs.get("tip_type", "standard")
                self.deck_state.update_tips_at_nest(
                    position, tips_on=True, tip_type=tip_type
                )
            elif operation == "tips_off":
                self.deck_state.update_tips_at_nest(position, tips_on=False)

        # Show glow effect
        glow_type = "move"
        if operation == "aspirate":
            glow_type = "aspirate"
        elif operation == "dispense":
            glow_type = "dispense"

        await self.send_operation_glow(position, glow_type)
        await self.broadcast_operation(
            f"{operation.title()} at position {position}",
            f"{volume} µL" if volume > 0 else "",
        )

        # Sync and update deck state
        self._sync_state_to_simple_format()
        await self.send_deck_update()
        await asyncio.sleep(1.5)

        # Complete operation in state management
        if self.deck_state:
            self.deck_state.complete_operation_at_nest(position)
            self._sync_state_to_simple_format()
            await self.send_deck_update()

    async def handle_client_message(self, websocket, message: str):
        """Handle incoming client messages"""
        try:
            data = json.loads(message)
            command = data.get("command")

            if command == "get_state":
                await self.send_deck_update(websocket)

            elif command == "get_detailed_state":
                # Send detailed state information
                if self.deck_state:
                    detailed_state = self.deck_state.export_state_to_dict()
                    message = {
                        "type": "detailed_state",
                        "state": detailed_state,
                        "timestamp": datetime.now().isoformat(),
                    }
                    await self.send_message(websocket, message)

            elif command == "simulate_transfer":
                from_pos = data.get("from", 1)
                to_pos = data.get("to", 2)
                volume = data.get("volume", 100)
                await self.simulate_transfer_with_state(from_pos, to_pos, volume)

            elif command == "simulate_operation":
                operation = data.get("operation")
                position = data.get("position", 1)
                volume = data.get("volume", 0)

                await self.simulate_operation_with_state(operation, position, volume)

            elif command == "set_labware":
                position = data.get("position", 1)
                labware_type = data.get("labware_type", "empty")
                labware_name = data.get("labware_name", "")

                # Update both state systems
                if self.deck_state:
                    self.deck_state.set_labware_at_nest(
                        position, labware_type, labware_name
                    )

                self._sync_simple_to_state_format(
                    position, {"labware": labware_type, "labware_name": labware_name}
                )

                await self.send_deck_update()

            elif command == "reset_deck":
                if self.deck_state:
                    self.deck_state.reset_all_nests()

                for i in range(1, 10):
                    self.simple_deck_state[i] = {
                        "labware": "empty",
                        "volume": 0,
                        "active": False,
                        "labware_name": "",
                        "operation": "idle",
                        "tips_loaded": False,
                    }

                await self.send_deck_update()

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON: {message}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def simulate_transfer_with_state(
        self, from_pos: int, to_pos: int, volume: float
    ):
        """Simulate a complete transfer using state management"""
        # Aspirate
        await self.simulate_operation_with_state("aspirate", from_pos, volume)
        await asyncio.sleep(0.5)

        # Dispense
        await self.simulate_operation_with_state("dispense", to_pos, volume)

    async def client_handler(self, websocket):
        """Handle WebSocket connections"""
        await self.register_client(websocket)
        try:
            async for message in websocket:
                await self.handle_client_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister_client(websocket)

    async def run_demo(self):
        """Run demo sequence using state management"""
        await asyncio.sleep(2)  # Wait for clients

        await self.setup_default_deck()
        await self.broadcast_operation("Demo starting...")
        await asyncio.sleep(1)

        # Demo operations with realistic liquid handling workflow
        operations = [
            ("tips_on", 1, 0, {"tip_type": "200µL"}),
            ("aspirate", 2, 100, {}),  # From source plate
            ("dispense", 3, 100, {}),  # To destination plate
            ("aspirate", 4, 50, {}),  # Buffer from reservoir
            ("dispense", 6, 50, {}),  # To assay plate
            ("wash", 4, 200, {"cycles": 3}),  # Wash tips
            ("tips_off", 9, 0, {}),  # Dispose tips
        ]

        for i, (op, pos, vol, extra_kwargs) in enumerate(operations):
            await self.broadcast_operation(f"Step {i+1}: {op}")
            await self.simulate_operation_with_state(op, pos, vol, **extra_kwargs)
            await asyncio.sleep(1)

        await self.broadcast_operation("Demo complete! 🎉")

        # Show final state summary
        if self.deck_state:
            summary = self.deck_state.get_deck_summary()
            await self.broadcast_operation(
                f"Operations performed: {summary['deck_info']['global_operation_count']}"
            )

    async def start(self, run_demo=False, serve_files=False, http_port=8080):
        """Start the server"""

        # Find free WebSocket port
        original_ws_port = self.port
        self.port = find_free_port(self.port)
        if self.port != original_ws_port:
            logger.info(
                f"WebSocket port {original_ws_port} in use, using {self.port} instead"
            )

        # Setup default deck layout when server starts
        await self.setup_default_deck()

        # Start HTTP file server if requested
        if serve_files:
            script_dir = Path(__file__).parent
            logger.info(f"Starting HTTP server from directory: {script_dir}")

            # Start HTTP server in background thread
            http_thread = threading.Thread(
                target=start_file_server,
                args=(str(script_dir), self.port, http_port),
                daemon=True,
            )
            http_thread.start()

            # Give HTTP server time to start
            await asyncio.sleep(1.5)

        # Start WebSocket server
        logger.info(f"Starting WebSocket server on ws://{self.host}:{self.port}")

        async with websockets.serve(self.client_handler, self.host, self.port):
            logger.info(f"✅ WebSocket server ready on ws://{self.host}:{self.port}")

            if not serve_files:
                logger.info("💡 Open index.html in your browser and click Connect")
            else:
                logger.info("🌐 Browser should open automatically")

            if run_demo:
                logger.info("🎬 Starting demo in 3 seconds...")
                await asyncio.sleep(3)
                asyncio.create_task(self.run_demo())

            try:
                # Keep the server running
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("🛑 Server stopping...")
                return


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Bravo Deck Visualizer with State Management"
    )
    parser.add_argument("--host", default="localhost", help="WebSocket host address")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket port number")
    parser.add_argument("--http-port", type=int, default=8080, help="HTTP server port")
    parser.add_argument("--demo", action="store_true", help="Run demo sequence")
    parser.add_argument(
        "--serve", action="store_true", help="Start HTTP file server and open browser"
    )

    args = parser.parse_args()

    visualizer = BravoDeckVisualizerWithState(host=args.host, port=args.port)

    try:
        asyncio.run(
            visualizer.start(
                run_demo=args.demo, serve_files=args.serve, http_port=args.http_port
            )
        )
    except KeyboardInterrupt:
        logger.info("Server stopped")


if __name__ == "__main__":
    main()
