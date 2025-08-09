"""
Pytest configuration and fixtures
"""

import pytest
from pybravo import BravoController


@pytest.fixture
def controller():
    """Create a BravoController instance for testing"""
    return BravoController()


@pytest.fixture
def connected_controller():
    """Create a connected BravoController instance for testing"""
    controller = BravoController()
    # Mock connection for testing
    controller._connected = True
    return controller
