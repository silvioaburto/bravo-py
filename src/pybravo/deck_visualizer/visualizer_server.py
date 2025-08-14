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


class BravoDeckVisualizer:
    """Simple WebSocket server for Bravo deck visualization"""

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients = set()

        # Simple deck state - 9 positions
        self.deck_state = {
            i: {"labware": "empty", "volume": 0, "active": False} for i in range(1, 10)
        }

        self.current_operation = "Ready"

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
        message = {
            "type": "deck_update",
            "deck": self.deck_state,
            "timestamp": datetime.now().isoformat(),
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
        """Setup default labware layout"""
        default_layout = {
            1: {"labware": "tips", "volume": 0},
            2: {"labware": "plate-96", "volume": 150000},
            3: {"labware": "plate-96", "volume": 75000},
            4: {"labware": "reservoir", "volume": 500000},
            5: {"labware": "empty", "volume": 0},
            6: {"labware": "plate-384", "volume": 50000},
            7: {"labware": "empty", "volume": 0},
            8: {"labware": "plate-96", "volume": 0},
            9: {"labware": "tips", "volume": 0},
        }

        for pos, config in default_layout.items():
            self.deck_state[pos].update(config)
            self.deck_state[pos]["active"] = False

        await self.send_deck_update()

    async def simulate_operation(
        self, operation: str, position: int, volume: float = 0
    ):
        """Simulate a single operation"""
        # Show glow effect
        glow_type = "move"
        if operation == "aspirate":
            glow_type = "aspirate"
            self.deck_state[position]["volume"] = max(
                0, self.deck_state[position]["volume"] - volume
            )
        elif operation == "dispense":
            glow_type = "dispense"
            self.deck_state[position]["volume"] += volume

        await self.send_operation_glow(position, glow_type)
        await self.broadcast_operation(
            f"{operation.title()} at position {position}",
            f"{volume} μL" if volume > 0 else "",
        )

        # Update deck state
        self.deck_state[position]["active"] = True
        await self.send_deck_update()
        await asyncio.sleep(1.5)

        # Clear active state
        self.deck_state[position]["active"] = False
        await self.send_deck_update()

    async def handle_client_message(self, websocket, message: str):
        """Handle incoming client messages"""
        try:
            data = json.loads(message)
            command = data.get("command")

            if command == "get_state":
                await self.send_deck_update(websocket)
            elif command == "simulate_transfer":
                from_pos = data.get("from", 1)
                to_pos = data.get("to", 2)
                volume = data.get("volume", 100)
                await self.simulate_transfer(from_pos, to_pos, volume)
            elif command == "simulate_operation":
                # Handle operations from the enhanced driver
                operation = data.get("operation")
                position = data.get("position", 1)
                volume = data.get("volume", 0)

                if operation == "aspirate":
                    await self.send_operation_glow(position, "aspirate")
                    await self.broadcast_operation(
                        f"Aspirating {volume} μL from position {position}"
                    )
                    # Update deck state
                    if position in self.deck_state:
                        self.deck_state[position]["active"] = True
                        self.deck_state[position]["volume"] = max(
                            0, self.deck_state[position]["volume"] - volume
                        )
                        await self.send_deck_update()
                        await asyncio.sleep(1.5)
                        self.deck_state[position]["active"] = False
                        await self.send_deck_update()

                elif operation == "dispense":
                    await self.send_operation_glow(position, "dispense")
                    await self.broadcast_operation(
                        f"Dispensing {volume} μL to position {position}"
                    )
                    # Update deck state
                    if position in self.deck_state:
                        self.deck_state[position]["active"] = True
                        self.deck_state[position]["volume"] += volume
                        await self.send_deck_update()
                        await asyncio.sleep(1.5)
                        self.deck_state[position]["active"] = False
                        await self.send_deck_update()

                elif operation in ["tips_on", "tips_off", "move_to_location"]:
                    await self.send_operation_glow(position, "move")
                    operation_text = operation.replace("_", " ").title()
                    await self.broadcast_operation(
                        f"{operation_text} at position {position}"
                    )
                    # Update deck state
                    if position in self.deck_state:
                        self.deck_state[position]["active"] = True
                        await self.send_deck_update()
                        await asyncio.sleep(1.5)
                        self.deck_state[position]["active"] = False
                        await self.send_deck_update()

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON: {message}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def simulate_transfer(self, from_pos: int, to_pos: int, volume: float):
        """Simulate a complete transfer"""
        # Aspirate
        await self.simulate_operation("aspirate", from_pos, volume)
        await asyncio.sleep(0.5)

        # Dispense
        await self.simulate_operation("dispense", to_pos, volume)

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
        """Run demo sequence"""
        await asyncio.sleep(2)  # Wait for clients

        await self.setup_default_deck()
        await self.broadcast_operation("Demo starting...")
        await asyncio.sleep(1)

        # Demo operations
        operations = [
            ("tips_on", 1, 0),
            ("aspirate", 2, 100),
            ("dispense", 8, 100),
            ("aspirate", 4, 50),
            ("dispense", 6, 50),
            ("tips_off", 9, 0),
        ]

        for i, (op, pos, vol) in enumerate(operations):
            await self.broadcast_operation(f"Step {i+1}: {op}")
            await self.simulate_operation(op, pos, vol)
            await asyncio.sleep(1)

        await self.broadcast_operation("Demo complete! 🎉")

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
                return  # Changed from 'break' to 'return'


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Bravo Deck Visualizer")
    parser.add_argument("--host", default="localhost", help="WebSocket host address")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket port number")
    parser.add_argument("--http-port", type=int, default=8080, help="HTTP server port")
    parser.add_argument("--demo", action="store_true", help="Run demo sequence")
    parser.add_argument(
        "--serve", action="store_true", help="Start HTTP file server and open browser"
    )

    args = parser.parse_args()

    visualizer = BravoDeckVisualizer(host=args.host, port=args.port)

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
