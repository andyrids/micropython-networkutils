
import logging
import sys
from binascii import hexlify, unhexlify
from typing import Any
from unittest.mock import MagicMock, call

import pytest
from pytest_mock import MockerFixture


@pytest.fixture
def mock_machine_module(mocker: MockerFixture) -> MagicMock:
    """"""
    mock_machine = mocker.MagicMock(name="machine_module")
    mock_machine.unique_id.return_value = unhexlify("E66164084373532B")
    return mock_machine


@pytest.fixture
def mock_network_module(mocker: MockerFixture) -> MagicMock:
    """"""
    class MockWLAN:
        STA_IF = 0
        AP_IF = 1
        PM_NONE = 0
        PM_PERFORMANCE = 1
        PM_POWERSAVE = 2


    mock_wlan_class = mocker.MagicMock(name="WLAN_class")
    mock_wlan_class.STA_IF = MockWLAN.STA_IF
    mock_wlan_class.AP_IF = MockWLAN.AP_IF
    mock_wlan_class.PM_NONE = MockWLAN.PM_NONE
    mock_wlan_class.PM_PERFORMANCE = MockWLAN.PM_PERFORMANCE
    mock_wlan_class.PM_POWERSAVE = MockWLAN.PM_POWERSAVE

    mock_network = mocker.MagicMock(name="network_module")
    mock_network.IF_STA = 0
    mock_network.IF_AP = 1
    mock_network.PM_NONE = 0
    mock_network.PM_PERFORMANCE = 1
    mock_network.PM_POWERSAVE = 2
    mock_network.STAT_WRONG_PASSWORD = -3
    mock_network.STAT_NO_AP_FOUND = -2
    mock_network.STAT_CONNECT_FAIL = -1
    mock_network.STAT_IDLE = 0
    mock_network.STAT_CONNECTING = 1
    mock_network.STAT_GOT_IP = 3

    mock_network.WLAN.return_value = mocker.MagicMock(spec=MockWLAN, name="WLAN_instance")
    mock_network.WLAN.PM_NONE = MockWLAN.PM_NONE
    mock_network.WLAN.PM_PERFORMANCE = MockWLAN.PM_PERFORMANCE
    mock_network.WLAN.PM_POWERSAVE = MockWLAN.PM_POWERSAVE

    return mock_network


@pytest.fixture
def mock_time_module(mocker: MockerFixture) -> MagicMock:
    """Mocks the time module."""
    mock_time = mocker.MagicMock(name="time_module")
    mock_time.sleep = mocker.MagicMock(name="sleep_func")
    # time.time() can be configured with side_effect in tests
    mock_time.time = mocker.MagicMock(name="time_func", return_value=0)
    return mock_time


@pytest.fixture
def mock_wlan_instance(mock_network_module):
    # instance returned by network.WLAN()
    return mock_network_module.WLAN.return_value


@pytest.fixture(autouse=True)
def patch_micropython_stdlib(
    mocker: MockerFixture,
    mock_machine_module: MagicMock,
    mock_network_module: MagicMock,
    mock_time_module: MagicMock,
) -> None:
    """Patch `sys.modules` with mocked MicroPython stdlib.
    
    This fixture patches `sys.modules` for the entire test session and
    ensures any modules imported by `network_utils.interface` are replaced
    with these mocks.
    """
    modules = {
        "machine": mock_machine_module,
        "network": mock_network_module,
        "time": mock_time_module,
    }
    mocker.patch.dict("sys.modules", modules)


@pytest.fixture
def network_env_instance():
    """Provides a clean NetworkEnv instance for each test."""
    # Import after mocks are set up by autouse fixture
    from network_utils.interface import NetworkEnv
    # clear singleton instance & environment for test isolation
    NetworkEnv._instance = None
    NetworkEnv._env = {}
    return NetworkEnv()