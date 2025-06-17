# sourcery skip: use-contextlib-suppress
# pyright: reportMissingImports=false
"""A MicroPython `network` module utility functions package.

This `network-utils` package contains utility functions that help implement
concrete network classes within the MicroPython `network` module, such as the
`network.WLAN` class.

The package has been designed to allow for future extensions:

- `network-utils` (WIP)
- `network-utils-mqtt` (TODO)
- `network-utils-microdot` (TODO)

This package uses static typing, which is enabled by the package dependencies.
On installation, the cross-compiled `typing.mpy` & `typing_extensions.mpy`
files are downloaded to the device `lib` folder.

Author: Andrew Ridyard.

License: GNU General Public License v3 or later.

Copyright (C): 2025.

Exceptions:
    WLANConnectionError: Raised on failed WLAN connection.

    WLANTimeoutError: Raised on WLAN connection timeout.

Functions:
    access_point_reset: Reset a WLAN instance and restart in Access Point
        (AP) mode.

    activate_interface: Activate WLAN interface and wait 5 seconds for
        initialisation.

    connect_interface: Connect a WLAN interface in STA mode.

    connection_issue: Test for a connection issue.

    deactivate_interface: Deactivate a WLAN interface.

    debug_message: Print a debug message.

    debug_network_status: Print WLAN status debug messages.

Examples:
    from network_utils import (
        NetworkEnv, connection_issue, get_network_interface, _logger
    )

    env = NetworkEnv()
    env.putenv("WLAN_SSID", "your SSID")
    env.putenv("WLAN_PASSWORD", "your PASSWORD")

    WLAN, WLAN_MODE = get_network_interface(debug=True)

    if not connection_issue(WLAN, WLAN_MODE):
        _logger.debug("STA CONNECTION ESTABLISHED")
    else:
        _logger.debug("CONNECTION ERROR, WLAN IN AP MODE")
"""

import binascii
import logging
import machine
import network
import sys
from time import sleep
from typing import Optional, Union


_DEVICE_ID = binascii.hexlify(machine.unique_id()).decode().upper()

_formatter = logging.Formatter("%(levelname)s:%(name)s:%(message)s")
_stream_handler = logging.StreamHandler(stream=sys.stdout)
_stream_handler.setFormatter(_formatter)
_logger = logging.getLogger(__name__)
_logger.addHandler(_stream_handler)
_logger.setLevel(logging.ERROR)


class NetworkEnv:
    """Network environment variable class."""

    _instance = None
    _env = {}

    def __new__(cls) -> "NetworkEnv":
        """Return a `singleton` instance of the `NetworkEnv` class.

        Returns:
            NetworkEnv: A new (if not previously initialised) or singleton
                instance of the `NetworkEnv` class.
        """
        if cls._instance is None:
            cls._instance = super(NetworkEnv, cls).__new__(cls)
            # extra initialisation here...
        return cls._instance

    def getenv(self, key: str) -> Union[str, None]:
        """Get environment variable from `_env` property.

        Args:
            key (str): Environment variable key.

        Returns:
            Union[str, None]: Environment variable value or None.
        """
        value = self._env.get(key)
        return str(value) if value else None

    def putenv(self, key: str, value: str) -> None:
        """Set environment variable in `_env` property.

        Args:
            key (str): Environment variable key.

            value (str): Environment variable value.

        Returns:
            None.
        """
        self._env[key] = value


class WLANConnectionError(Exception):
    """Raised on failed WLAN connection."""

    pass


class WLANTimeoutError(Exception):
    """Raised on failed WLAN connection timeout."""

    pass


def access_point_reset(WLAN: network.WLAN) -> tuple[network.WLAN, int]:
    """Reset a WLAN instance and restart in Access Point (AP) mode.

    Configures AP SSID & password through credentials stored in `AP_SSID` &
    `AP_PASSWORD` environment variables or defaults to `DEVICE-DEVICE_ID`
    as the SSID and DEVICE_ID as the password. DEVICE_ID represents the value
    returned by the `machine.unique_id` function.

    Args:
        WLAN (network.WLAN): WLAN interface instance.

    Returns:
        tuple[network.WLAN, int]: A WLAN instance in AP mode and the
            `network.AP_IF` AP mode enumeration value.
    """
    WLAN.disconnect()
    deactivate_interface(WLAN)
    WLAN.deinit()

    env = NetworkEnv()

    WLAN = network.WLAN(network.AP_IF)
    AP_SSID = env.getenv("AP_SSID")
    AP_PASSWORD = env.getenv("AP_PASSWORD")
    if AP_SSID is None or AP_PASSWORD is None:
        _logger.debug("ENV $AP_SSID & $AP_PASSWORD NOT SET")
        AP_SSID = f"DEVICE-{_DEVICE_ID}"
        AP_PASSWORD = _DEVICE_ID
        env.putenv("AP_SSID", AP_SSID)
        env.putenv("AP_PASSWORD", _DEVICE_ID)
        _logger.debug("USING DEFAULT AP_SSID & AP_PASSWORD")

    WLAN.config(ssid=AP_SSID, password=AP_PASSWORD)
    activate_interface(WLAN)
    return WLAN, network.AP_IF


def activate_interface(WLAN: network.WLAN) -> None:
    """Activate WLAN interface and wait 5 seconds for initialisation.

    NOTE: The active method does not behave as expected on the Pico W for STA
    mode - it will always return False (hence the timeout). This might be a
    nuance of the Pico W and should work on other microcontrollers.

    Args:
        WLAN (network.WLAN): WLAN interface instance.

    Returns:
        None.
    """
    _logger.debug("ACTIVATE NETWORK INTERFACE")
    # activate network interface
    WLAN.active(True)
    try:  # 5 second timeout
        await_timeout = iter(range(5))
        while next(await_timeout) >= 0:
            if WLAN.status() == network.STAT_GOT_IP or WLAN.active():
                _logger.debug("NETWORK INTERFACE ACTIVE - AP MODE")
                break
            sleep(1)
    except StopIteration:
        _logger.debug("NETWORK INTERFACE TIMEOUT - STA MODE")


def connect_interface(WLAN: network.WLAN) -> None:
    """Connect a WLAN interface in STA mode.

    A connection is attempted using credentials stored in `WLAN_SSID` &
    `WLAN_PASSWORD` environment variables. A `WLANConnectionError` is raised
    if WLAN is in AP mode or the connection attempt times out (30s).

    Args:
        WLAN (network.WLAN): Activated WLAN interface.

    Raises:
        WLANConnectionError: On failed connection to WiFi access point.

    Returns:
        None.
    """
    try:
        env = NetworkEnv()

        WLAN_SSID = env.getenv("WLAN_SSID")
        WLAN_PASSWORD = env.getenv("WLAN_PASSWORD")

        if WLAN_SSID is None:
            _logger.debug("ENV $WLAN_SSID NOT SET")
            raise WLANConnectionError

        networks = {name.decode() for name, *_ in set(WLAN.scan()) if name}
        if WLAN_SSID not in networks:
            _logger.error(f"SSID '{WLAN_SSID}' NOT AVAILABLE")
            _logger.debug(f"AVAILABLE NETWORKS: {networks}")
            raise WLANConnectionError

        if WLAN_PASSWORD is None:
            _logger.warning("WARNING: ENV $WLAN_PASSWORD NOT SET")

        _logger.debug(f"CONNECTING TO SSID '{WLAN_SSID}'")

        # connect WLAN interface
        WLAN.connect(WLAN_SSID, WLAN_PASSWORD)
    # if WLAN is not in STA mode
    except (OSError, TypeError) as e:
        _logger.debug(f"TypeError: {e}")
        _logger.error(f"WLAN CONNECT ERROR - SSID {WLAN_SSID}")
        raise WLANConnectionError from e
    try:  # 30 second timeout
        _logger.debug("WAITING FOR WLAN CONNECTION")
        await_timeout = iter(range(30))
        while next(await_timeout) >= 0:
            _logger.debug(f"WLAN STATUS: {WLAN.status()}")
            if (WLAN.status() == network.STAT_GOT_IP) or WLAN.isconnected():
                break
            sleep(1)
    except StopIteration as e:
        _logger.error(f"WLAN CONNECTION TO SSID {WLAN_SSID} TIMEOUT")
        _logger.debug(network_status_message(WLAN, WLAN.IF_STA))
        raise WLANTimeoutError from e


def connection_issue(WLAN: network.WLAN, mode: int) -> bool:
    """Test for a connection issue.

    Args:
        WLAN (network.WLAN): Activated WLAN interface.

        mode (int): WLAN interface mode - client (`WLAN.IF_STA`) or
            access point (`WLAN.IF_AP`).

    Returns:
        bool: True if WLAN is in AP mode or if WLAN is in STA mode and not
            connected to a WiFi access point, else False.
    """
    return mode == WLAN.IF_AP or (
        mode == WLAN.IF_STA and not WLAN.isconnected()
    )


def deactivate_interface(WLAN: network.WLAN) -> None:
    """Deactivate a WLAN interface.

    NOTE: The `WLAN.active` method does not behave as expected on the Pico W
    for STA mode - it will always return False (hence the timeout). This might
    be a nuance of the Pico W and should work on other microcontrollers.

    Args:
        WLAN (network.WLAN): WLAN interface instance.

    Returns:
        None.
    """
    _logger.debug("DEACTIVATE NETWORK INTERFACE")
    WLAN.active(False)

    try:  # 5 second timeout
        await_timeout = iter(range(5))
        while next(await_timeout) >= 0:
            if not WLAN.active():
                _logger.debug("NETWORK INTERFACE INACTIVE - AP MODE")
                break
            sleep(1)
    except StopIteration:
        _logger.debug("DEACTIVATE NETWORK TIMEOUT - STA MODE")


def get_network_interface(
    pm: Optional[int] = None, debug: bool = False
) -> tuple[network.WLAN, int]:
    """Initialise & activate a `network.WLAN` interface instance.

    The interface is initialised in either STA or AP mode depending on
    environment variable values and connection availability.

    STA Mode
    --------
    1. `WLAN_SSID` & `WLAN_PASSWORD` environment variables set
    2. Successful connection with `WLAN_SSID` & `WLAN_PASSWORD`

    AP Mode
    --------
    1. Environment variables not set or WLAN connection failed
    2. SSID is DEVICE-[UNIQUE ID] or `AP_SSID` environment variable
    3. Password is [UNIQUE ID] or `AP_PASSWORD` environment variable
    4. Check device IP on connection to SSID via PC/mobile

    Interface enumerations:
        network.STA_IF | WLAN.IF_STA (0) - Client
        network.AP_IF | WLAN.IF_AP (1) - Access point

    Status enumerations:
        network.STAT_WRONG_PASSWORD (-3)
        network.STAT_NO_AP_FOUND (-2)
        network.STAT_CONNECT_FAIL (-1)
        network.STAT_IDLE (0)
        network.STAT_CONNECTING (1)
        network.STAT_GOT_IP (3)

    Power mode enumerations:
        WLAN.PM_NONE - Disable power management
        WLAN.PM_PERFORMANCE - Enable power management with a shorter timer
        WLAN.PM_POWERSAVE - Increased power savings and reduced performance

    Args:
        pm (int, optional): WLAN power management mode; WLAN.PM_NONE,
            WLAN.PM_PERFORMANCE or WLAN.PM_POWERSAVE. Defaults to None.

        debug (bool): Debug messages flag.

    Returns:
        tuple[network.WLAN, int]: An activated WLAN instance and its relevant
            interface mode - `network.STA_IF` or `network.AP_IF`.
    """
    if debug:
        _logger.setLevel(logging.DEBUG)

    _logger.debug("INITIALISE NETWORK WLAN INSTANCE")

    env = NetworkEnv()

    AP_SSID = env.getenv("AP_SSID")
    AP_PASSWORD = env.getenv("AP_PASSWORD")

    # initial declaration of AP SSID & PASSWORD based on unique ID
    if AP_SSID is None or AP_PASSWORD is None:
        AP_SSID = f"DEVICE-{_DEVICE_ID}"
        AP_PASSWORD = _DEVICE_ID
        env.putenv("AP_SSID", AP_SSID)
        env.putenv("AP_PASSWORD", _DEVICE_ID)

    WLAN_SSID = env.getenv("WLAN_SSID")

    # select WLAN instance mode based on credential values
    if WLAN_SSID is None or len(WLAN_SSID) < 1:
        # reset WLAN secrets
        _logger.debug(f"INVALID SSID ({WLAN_SSID}) SETTING AP MODE")
        WLAN_MODE = network.AP_IF
    else:
        WLAN_MODE = network.STA_IF
        _logger.debug("SETTING WLAN MODE TO STA")

    # create WLAN instance
    WLAN = network.WLAN(WLAN_MODE)
    # config WLAN AP with SSID & KEY values
    if pm not in {WLAN.PM_NONE, WLAN.PM_PERFORMANCE, WLAN.PM_POWERSAVE}:
        pm = WLAN.PM_NONE
    WLAN.config(ssid=AP_SSID, password=AP_PASSWORD, pm=pm)
    activate_interface(WLAN)
    if WLAN_MODE == network.AP_IF:
        return WLAN, WLAN_MODE

    # attempt WLAN interface connection
    try:
        # successful STA mode connection
        connect_interface(WLAN)
        _logger.debug(f"WLAN CONNECTION SUCCESSFUL: {WLAN_SSID}")
        return WLAN, WLAN_MODE
    except (WLANConnectionError, WLANTimeoutError):
        _logger.error("RESETTING TO AP MODE")
        WLAN, WLAN_MODE = access_point_reset(WLAN)
        return WLAN, WLAN_MODE


def network_status_message(WLAN: network.WLAN, mode: int) -> str:
    """Print WLAN status debug messages.

    Args:
        WLAN (network.WLAN): WLAN interface instance.

        mode (str): WLAN interface mode - client (`WLAN.IF_STA`) or
            access point (`WLAN.IF_AP`).
    """
    WLAN_MODE_STR = ("STA", "AP")[mode]
    status = WLAN.status()
    active = WLAN.active()
    connected = WLAN.isconnected()

    return f"""
        WLAN INFO
        ---------
        MODE: {WLAN_MODE_STR}
        STATUS: {status}
        ACTIVE: {active}
        CONNECTED: {connected}
        """
