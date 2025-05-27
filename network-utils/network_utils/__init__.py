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
    import os
    from connection import debug_network_status, get_network_interface

    _VERBOSE = const(True)

    os.putenv("WLAN_SSID", "SSID")
    os.putenv("WLAN_PASSWORD", "PASSWORD")

    WLAN, WLAN_MODE = get_network_interface(_VERBOSE)

    debug_network_status(WLAN, WLAN_MODE, verbose)

    if not connection_issue(WLAN, WLAN_MODE):
        print("STA CONNECTION ESTABLISHED")
    else:
        print("CONNECTION ERROR, WLAN IN AP MODE")
"""

import binascii
import machine
import network
import os

from time import sleep

# optional `network-utils-*` extension dependencies
try:
    from .mqtt import *
except ImportError:
    pass

_DEVICE_ID = binascii.hexlify(machine.unique_id()).decode().upper()


class CertificateNotFound(Exception):
    """SSL context certificate not found."""

    pass


class WLANConnectionError(Exception):
    """Raised on failed WLAN connection."""

    pass


def access_point_reset(
    WLAN: network.WLAN, verbose: bool
) -> tuple[network.WLAN, int]:
    """Reset a WLAN instance and restart in Access Point (AP) mode.

    Configures AP SSID & password through credentials stored in `AP_SSID` &
    `AP_PASSWORD` environment variables or

    Args:
        verbose (bool): Debug messages flag.

    Returns:
        network.WLAN
    """
    WLAN.disconnect()
    deactivate_interface(WLAN, verbose)
    WLAN.deinit()

    WLAN = network.WLAN(network.AP_IF)
    AP_SSID = os.getenv("AP_SSID")
    AP_PASSWORD = os.getenv("AP_PASSWORD")
    if AP_SSID is None or AP_PASSWORD is None:
        debug_message("ENV $AP_SSID & $AP_PASSWORD NOT SET", verbose)
        AP_SSID = f"DEVICE-{_DEVICE_ID}"
        AP_PASSWORD = _DEVICE_ID
        os.putenv("AP_SSID", AP_SSID)
        os.putenv("AP_PASSWORD", _DEVICE_ID)
        debug_message("USING DEFAULT AP_SSID & AP_PASSWORD", verbose)

    WLAN.config(ssid=AP_SSID, password=AP_PASSWORD)
    activate_interface(WLAN, verbose)
    return WLAN, network.AP_IF


def activate_interface(WLAN: network.WLAN, verbose: bool) -> None:
    """Activate WLAN interface and wait 5 seconds for initialisation.

    NOTE: The active method does not behave as expected on the Pico W
    for STA mode - it will always return False (hence the timeout).

    Args:
        WLAN (network.WLAN): WLAN instance.

        debug (bool): Debug messages flag.

    Returns:
        None.
    """
    debug_message("ACTIVATE NETWORK INTERFACE", verbose)
    # activate network interface
    WLAN.active(True)
    try:  # 5 second timeout
        await_timeout = iter(range(5))
        while next(await_timeout) >= 0:
            if WLAN.status() == network.STAT_GOT_IP or WLAN.active():
                debug_message("NETWORK INTERFACE ACTIVE - AP MODE", verbose)
                break
            sleep(1)
    except StopIteration:
        debug_message("NETWORK INTERFACE TIMEOUT - STA MODE", verbose)


def connect_interface(WLAN: network.WLAN, verbose: bool) -> None:
    """Connect a WLAN interface in STA mode.

    A connection is attempted using credentials stored in `WLAN_SSID` &
    `WLAN_PASSWORD` environment variables. A `WLANConnectionError` is raised
    if WLAN is in AP mode or the connection attempt times out (30s).

    Args:
        WLAN (network.WLAN): Activated WLAN interface.

        debug (bool): Debug messages flag.

    Raises:
        WLANConnectionError: On failed connection to WiFi access point.

    Returns:
        None.
    """
    try:
        WLAN_SSID = os.getenv("WLAN_SSID")
        WLAN_PASSWORD = os.getenv("WLAN_PASSWORD")

        if WLAN_SSID is None:
            debug_message("ENV $WLAN_SSID NOT SET", verbose)
            raise WLANConnectionError

        networks = {name.decode() for name, *_ in set(WLAN.scan()) if name}
        if WLAN_SSID not in networks:
            debug_message(f"SSID '{WLAN_SSID}' NOT AVAILABLE", verbose)
            debug_message(f"AVAILABLE NETWORKS: {networks}", verbose)
            raise WLANConnectionError

        if WLAN_PASSWORD is None:
            debug_message("WARNING: ENV $WLAN_PASSWORD NOT SET", verbose)

        debug_message(f"CONNECTING TO SSID '{WLAN_SSID}'", verbose)

        # connect WLAN interface
        WLAN.connect(WLAN_SSID, WLAN_PASSWORD)
    # if WLAN is not in STA mode
    except (OSError, TypeError) as e:
        debug_message(f"TypeError: {e}", verbose)
        debug_message(f"WLAN CONNECT ERROR - SSID {WLAN_SSID}", verbose)
        raise WLANConnectionError from e
    try:  # 30 second timeout
        debug_message("WAITING FOR WLAN CONNECTION", verbose)
        await_timeout = iter(range(30))
        while next(await_timeout) >= 0:
            debug_message(f"WLAN STATUS: {WLAN.status()}", verbose)
            if (WLAN.status() == network.STAT_GOT_IP) or WLAN.isconnected():
                break
            sleep(1)
    except StopIteration as e:
        debug_network_status(WLAN, WLAN.IF_STA, verbose)
        raise WLANConnectionError from e


def connection_issue(WLAN: network.WLAN, WLAN_MODE: int) -> bool:
    """Test for a connection issue.

    Args:
        WLAN (network.WLAN): Activated WLAN interface.

        verbose (bool): Debug messages flag.

    Returns:
        bool: True if WLAN is in AP mode or if WLAN is in STA mode and not
            connected to a WiFi access point, else False.
    """
    return (WLAN_MODE == WLAN.IF_AP) or (
        WLAN_MODE == WLAN.IF_STA and not WLAN.isconnected()
    )


def deactivate_interface(WLAN: network.WLAN, verbose: bool) -> None:
    """Deactivate a WLAN interface.

    NOTE: The `WLAN.active` method does not behave as expected on the Pico W
    for STA mode - it will always return False (hence the timeout).

    Args:
        WLAN (network.WLAN): WLAN instance.

        verbose (bool): Debug messages flag.

    Returns:
        None.
    """
    debug_message("DEACTIVATE NETWORK INTERFACE", verbose)
    WLAN.active(False)

    try:  # 5 second timeout
        await_timeout = iter(range(5))
        while next(await_timeout) >= 0:
            if not WLAN.active():
                debug_message("NETWORK INTERFACE INACTIVE - AP MODE", verbose)
                break
            sleep(1)
    except StopIteration:
        debug_message("DEACTIVATE NETWORK TIMEOUT - STA MODE", verbose)


def debug_message(message: str, verbose: bool) -> None:
    """Print a debug message.

    Args:
        message (str): Message to print.

        verbose (bool): Message print flag.
    """
    # `"{:^30}".format("CENTRED STRING")`
    if not verbose:
        return
    print("\n".join([i.strip() for i in message.split("\n")]))


def debug_network_status(WLAN: network.WLAN, mode: int, verbose: bool) -> None:
    """Print WLAN status debug messages.

    Args:
        WLAN (network.WLAN): WLAN instance.

        mode (str): WLAN instance mode.

        verbose (bool): Debug message print flag.
    """
    WLAN_MODE_STR = ("STA", "AP")[mode]
    status = WLAN.status()
    active = WLAN.active()
    connected = WLAN.isconnected()

    message = f"""
    WLAN INFO
    ---------
    MODE: {WLAN_MODE_STR}
    STATUS: {status}
    ACTIVE: {active}
    CONNECTED: {connected}
    """

    debug_message(message, verbose)


def get_network_interface(verbose: bool = False) -> tuple[network.WLAN, int]:
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

    Args:
        verbose (bool): Debug messages flag.

    Returns:
        tuple[network.WLAN, network.STA_IF | network.AP_IF]
    """
    debug_message("INITIALISE NETWORK WLAN INSTANCE", verbose)

    AP_SSID = os.getenv("AP_SSID")
    AP_PASSWORD = os.getenv("AP_PASSWORD")

    # initial declaration of AP SSID & PASSWORD based on unique ID
    if AP_SSID is None or AP_PASSWORD is None:
        AP_SSID = f"DEVICE-{_DEVICE_ID}"
        AP_PASSWORD = _DEVICE_ID
        os.putenv("AP_SSID", AP_SSID)
        os.putenv("AP_PASSWORD", _DEVICE_ID)

    WLAN_SSID = os.getenv("WLAN_SSID")

    # select WLAN instance mode based on credential values
    if WLAN_SSID is None or len(WLAN_SSID) < 1:
        # reset WLAN secrets
        os.unsetenv("WLAN_SSID")
        os.unsetenv("WLAN_PASSWORD")
        debug_message("SETTING WLAN MODE TO AP", verbose)
        WLAN_MODE = network.AP_IF
    else:
        WLAN_MODE = network.STA_IF
        debug_message("SETTING WLAN MODE TO STA", verbose)

    # create WLAN instance
    WLAN = network.WLAN(WLAN_MODE)
    # config WLAN AP with SSID & KEY values
    WLAN.config(ssid=AP_SSID, password=AP_PASSWORD, pm=0xA11140)

    activate_interface(WLAN, verbose)

    # attempt WLAN interface connection
    try:
        # successful STA mode connection
        connect_interface(WLAN, verbose)
        debug_message(f"WLAN CONNECTION SUCCESSFUL: {WLAN_SSID}", verbose)
        return WLAN, WLAN_MODE
    except WLANConnectionError:
        WLAN, WLAN_MODE = access_point_reset(WLAN, verbose)
        return WLAN, WLAN_MODE
    except StopIteration:
        # WLAN connection timed out
        debug_message(f"WLAN CONNECTION TO SSID {WLAN_SSID} TIMEOUT", verbose)
        debug_message("SWITCHING TO AP MODE", verbose)
        WLAN, WLAN_MODE = access_point_reset(WLAN, verbose)
        return WLAN, WLAN_MODE
