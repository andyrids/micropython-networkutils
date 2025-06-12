# pyright: reportArgumentType=false
"""Unit tests for network-utils package."""

import sys
from typing import Any, Optional, Union

import unittest
from network_utils.interface import NetworkEnv, connection_issue


class MockWLAN:
    """Mock class representing the `network.WLAN` interface."""

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

    def active(
        self, is_active: Optional[Union[bool, int]] = None
    ) -> Union[bool, None]:
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
        """Connect to the specified wireless network, using the specified key.

        Args:
            ssid (str, optional): Network SSID value.

            password (str, optional): Network password.

        Returns:
            None.
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


class TestNetworkUtils(unittest.TestCase):
    """Unit test class."""

    def test_system_micropython(self) -> None:
        """Test system implimentation for Micropython."""
        msg = "NOT RUNNING ON A MICROPYTHON DEVICE"
        self.assertEqual(
            getattr(sys.implementation, "name", None), "micropython", msg
        )


    def test_connection_issue_sta(self) -> None:
        """Test connection issue in STA mode."""
        WLAN = MockWLAN(MockWLAN.IF_STA)
        self.assertTrue(connection_issue(WLAN, MockWLAN.IF_STA))
        WLAN.connect("TEST_SSID", "TEST_PASSWORD")
        self.assertFalse(connection_issue(WLAN, MockWLAN.IF_STA))

    def test_connection_issue_ap(self) -> None:
        """Test connection issue in AP mode."""
        WLAN = MockWLAN(MockWLAN.IF_AP)
        self.assertTrue(connection_issue(WLAN, MockWLAN.IF_AP))

