"""Pytest `conftest` with fixtures & mocks for MicroPython modules.

Mocks include MicroPython stdlib modules; `machine`, `network` & `time`.

Author: Andrew Ridyard.

License: GNU General Public License v3 or later.

Copyright (C): 2025.
"""

import logging
import sys
from binascii import hexlify, unhexlify
from typing import Any, Optional
from unittest.mock import MagicMock, call

import pytest
from pytest_mock import MockerFixture


class MockWLAN:
    """A mock class for `network.WLAN`"""

    IF_STA = 0
    IF_AP = 1
    PM_NONE = 0
    PM_PERFORMANCE = 1
    PM_POWERSAVE = 2
    STAT_WRONG_PASSWORD = -3
    STAT_NO_AP_FOUND = -2
    STAT_CONNECT_FAIL = -1
    STAT_IDLE = 0
    STAT_CONNECTING = 1
    STAT_GOT_IP = 3

    def __init__(self, mode: int) -> None:
        """Initialise MockWLAN interface.

        Args:
            mode (int): Network interface mode, STA (0) or AP (1).
        """
        if not self.IF_STA <= mode <= self.IF_AP:
            raise ValueError(f"Incorrect network mode - {mode}")
        self._mode = mode
        self._active = False
        self._connected = False
        self._status = self.STAT_IDLE
        self._config = {}

    def active(self, is_active: Optional[bool | int] = None) -> bool | None:
        """Activate or deactivate network interface or query current state.

        Ff no argument is provided. Most other methods require active interface.

        Args:
            is_active (bool | int, optional): Activate or deactivate network
                interface based on value or query current state if None.
                Defaults to None.

        Returns:
            Union[bool, None]: None if activating or deactivating the network
                interface else boolean value based on current network state.
        """
        if is_active:
            self._active = bool(is_active)
        else:
            return self._active

    def config(self, *args, **kwargs: Any) -> None:
        """Get or set general network interface parameters.

        These methods allow to work with additional parameters beyond standard
        IP configuration (as dealt with by AbstractNIC.ipconfig()). These
        include network-specific and hardware-specific parameters.

        For setting parameters, keyword argument syntax should be used,
        multiple parameters can be set at once. For querying, parameters name
        should be quoted as a string, and only one parameter can be queries at
        time:
        """
        try:
            (key,) = args
            return self._config.get(key)
        except ValueError:
            self._config.update(kwargs)

    def connect(
        self, ssid: Optional[str] = None, password: Optional[str] = None
    ) -> None:
        """Connect to the wireless network, using the specified key.

        Args:
            ssid (str, optional): Network SSID value.

            password (str, optional): Network password.
        """
        isauth = ssid == "TEST_SSID" and password == "TEST_PASSWORD"
        self._status = self.STAT_GOT_IP if isauth else self.STAT_CONNECT_FAIL
        self._connected = isauth

    def deinit(self) -> None:
        """Uninitialise network interface."""
        self._active = False

    def disconnect(self):
        """Disconnect from the currently connected wireless network."""
        self._connected = False

    def isconnected(self) -> bool:
        """Tests connection in STA & AP modes.

        Returns:
            bool: In STA mode, returns True if connected to a WiFi access
                point and has a valid IP address. In AP mode returns True
                when a station is connected. Returns False otherwise.
        """
        return self._connected

    def scan(self) -> list[tuple]:
        """Scan for the available wireless networks.

        Hidden networks -- where the SSID is not broadcast -- will also be
        scanned if the WLAN interface allows it. Scanning is only possible on
        STA interface.

        Returns:
            list[tuple]: list of tuples with the information about WiFi access
                points; (ssid, bssid, channel, RSSI, security, hidden)
        """
        return [(b"TEST_SSID", b"", 12, 0, 0)]

    def status(self):
        """Return the current status of the wireless connection.

        When called with no argument, the return value describes the network
        link status. The possible statuses are defined as constants in the
        network module:

        * ``STAT_IDLE`` -- no connection and no activity,
        * ``STAT_CONNECTING`` -- connecting in progress,
        * ``STAT_WRONG_PASSWORD`` -- failed due to incorrect password,
        * ``STAT_NO_AP_FOUND`` -- failed because no access point replied,
        * ``STAT_CONNECT_FAIL`` -- failed due to other problems,
        * ``STAT_GOT_IP`` -- connection successful.

        Returns:
            int: Constant value representing current status of the wireless
                connection.
        """
        return self._status


@pytest.fixture
def mock_machine_module(mocker: MockerFixture) -> MagicMock:
    """"""
    mock_machine = mocker.MagicMock(name="machine_module")
    mock_machine.unique_id.return_value = unhexlify("E66164084373532B")
    return mock_machine


@pytest.fixture
def mock_network_module(mocker: MockerFixture) -> MagicMock:
    """"""
    mock_wlan_class = mocker.MagicMock(name="WLAN_class")
    mock_wlan_class.IF_STA = MockWLAN.IF_STA
    mock_wlan_class.IF_AP = MockWLAN.IF_AP
    mock_wlan_class.PM_NONE = MockWLAN.PM_NONE
    mock_wlan_class.PM_PERFORMANCE = MockWLAN.PM_PERFORMANCE
    mock_wlan_class.PM_POWERSAVE = MockWLAN.PM_POWERSAVE

    mock_network = mocker.MagicMock(name="network_module")
    mock_network.STA_IF = 0
    mock_network.AP_IF = 1
    mock_network.PM_NONE = 0
    mock_network.PM_PERFORMANCE = 1
    mock_network.PM_POWERSAVE = 2
    mock_network.STAT_WRONG_PASSWORD = -3
    mock_network.STAT_NO_AP_FOUND = -2
    mock_network.STAT_CONNECT_FAIL = -1
    mock_network.STAT_IDLE = 0
    mock_network.STAT_CONNECTING = 1
    mock_network.STAT_GOT_IP = 3
    mock_network.WLAN.return_value = mocker.MagicMock(
        spec=MockWLAN, name="WLAN_instance"
    )
    mock_network.WLAN.PM_NONE = MockWLAN.PM_NONE
    mock_network.WLAN.PM_PERFORMANCE = MockWLAN.PM_PERFORMANCE
    mock_network.WLAN.PM_POWERSAVE = MockWLAN.PM_POWERSAVE

    return mock_network


@pytest.fixture
def mock_time_module(mocker: MockerFixture) -> MagicMock:
    """Mocks the time module."""
    mock_time = mocker.MagicMock(name="time_module")
    mock_time.sleep = mocker.MagicMock(name="sleep_func")
    # `time.time` can be configured with side_effect in tests
    mock_time.time = mocker.MagicMock(name="time_func", return_value=0)
    return mock_time


@pytest.fixture
def mock_logging_module(mocker: MockerFixture) -> MagicMock:
    """Mocks the logging module."""
    mock_logging = mocker.MagicMock(name="logging_module")
    mock_logger_instance = mocker.MagicMock(name="logger_instance")
    mock_logging.getLogger.return_value = mock_logger_instance
    mock_logging.Formatter = mocker.MagicMock(name="Formatter_class")
    mock_logging.StreamHandler = mocker.MagicMock(name="StreamHandler_class")

    # Add logging level constants
    mock_logging.DEBUG = logging.DEBUG
    mock_logging.INFO = logging.INFO
    mock_logging.WARNING = logging.WARNING
    mock_logging.ERROR = logging.ERROR
    mock_logging.CRITICAL = logging.CRITICAL
    return mock_logging


@pytest.fixture
def mock_wlan_instance(mock_network_module: MagicMock) -> MagicMock:
    """Mocks a `network.WLAN` instance."""
    # instance returned by `network.WLAN`
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
        # "logging": mock_logging_module
    }
    mocker.patch.dict("sys.modules", modules)


@pytest.fixture
def network_env_instance() -> Any:
    """Provides a clean NetworkEnv instance for each test."""
    # Import after mocks are set up by autouse fixture
    from networkutils.core import NetworkEnv

    # clear singleton instance & environment for test isolation
    NetworkEnv._instance = None
    NetworkEnv._env = {}
    return NetworkEnv()
