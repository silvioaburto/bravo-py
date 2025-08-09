"""
Tests for core PyBravo functionality
"""

import pytest
from pybravo import BravoController
from pybravo.exceptions import BravoConnectionError, BravoCommandError


class TestBravoController:
    """Test cases for BravoController"""

    def test_init(self):
        """Test controller initialization"""
        controller = BravoController()
        assert controller.port is None
        assert controller.timeout == 30.0
        assert not controller.is_connected()

    def test_init_with_params(self):
        """Test controller initialization with parameters"""
        controller = BravoController(port="/dev/ttyUSB0", timeout=60.0)
        assert controller.port == "/dev/ttyUSB0"
        assert controller.timeout == 60.0

    def test_connect(self, controller):
        """Test connection to device"""
        result = controller.connect()
        assert result is True
        assert controller.is_connected()

    def test_disconnect(self, connected_controller):
        """Test disconnection from device"""
        assert connected_controller.is_connected()
        connected_controller.disconnect()
        assert not connected_controller.is_connected()

    def test_get_status_connected(self, connected_controller):
        """Test getting status when connected"""
        status = connected_controller.get_status()
        assert isinstance(status, dict)
        assert "status" in status
        assert "position" in status
        assert "temperature" in status

    def test_get_status_not_connected(self, controller):
        """Test getting status when not connected"""
        with pytest.raises(BravoCommandError, match="Device not connected"):
            controller.get_status()

    def test_move_to_connected(self, connected_controller):
        """Test moving to position when connected"""
        # Should not raise an exception
        connected_controller.move_to(10.0, 20.0, 30.0)
        connected_controller.move_to(10.0, 20.0)  # Without Z

    def test_move_to_not_connected(self, controller):
        """Test moving when not connected"""
        with pytest.raises(BravoCommandError, match="Device not connected"):
            controller.move_to(10.0, 20.0)

    def test_aspirate_valid(self, connected_controller):
        """Test aspiration with valid parameters"""
        connected_controller.aspirate(100.0)
        connected_controller.aspirate(50.0, speed=10.0)

    def test_aspirate_invalid_volume(self, connected_controller):
        """Test aspiration with invalid volume"""
        with pytest.raises(BravoCommandError, match="Volume must be positive"):
            connected_controller.aspirate(-10.0)

        with pytest.raises(BravoCommandError, match="Volume must be positive"):
            connected_controller.aspirate(0.0)

    def test_aspirate_not_connected(self, controller):
        """Test aspiration when not connected"""
        with pytest.raises(BravoCommandError, match="Device not connected"):
            controller.aspirate(100.0)

    def test_dispense_valid(self, connected_controller):
        """Test dispensing with valid parameters"""
        connected_controller.dispense(100.0)
        connected_controller.dispense(50.0, speed=10.0)

    def test_dispense_invalid_volume(self, connected_controller):
        """Test dispensing with invalid volume"""
        with pytest.raises(BravoCommandError, match="Volume must be positive"):
            connected_controller.dispense(-10.0)

    def test_dispense_not_connected(self, controller):
        """Test dispensing when not connected"""
        with pytest.raises(BravoCommandError, match="Device not connected"):
            controller.dispense(100.0)
