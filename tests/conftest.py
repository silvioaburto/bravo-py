"""
Pytest configuration and fixtures
"""

import pytest
from pybravo import BravoDriver


@pytest.fixture
def controller():
    """Create a driver instance for testing"""
    return BravoDriver()


@pytest.fixture
def connected_controller():
    """Create a connected BravoController instance for testing"""
    controller = BravoDriver()
    # Mock connection for testing
    controller._connected = True
    return controller
