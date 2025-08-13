"""Async AP mode example."""

import asyncio
import logging
import network
from networkutils import (
    NetworkEnv,
    activate_interface,
    connect_interface,
    get_network_interface,
)
from networkutils.core import (
    WLANConnectionError,
    WLANCredentialsError,
    WLANNotFoundError,
    _logger,
)


async def main() -> None:
    """Initialises, activates & connects a WLAN to an access point."""
    # get initialised WLAN interface in STA mode & activate
    WLAN = get_network_interface(mode=network.AP_IF)
    await activate_interface(WLAN)

    try:
        # attempt connection to access point
        await connect_interface(WLAN)
    except WLANConnectionError:
        _logger.error("Failed connection to access point")
    except WLANCredentialsError:
        _logger.error("Incorrect credentials for access point")
    except WLANNotFoundError:
        _logger.error("Access point not found in available networks")

    if WLAN.isconnected():
        _logger.info("Connected to access point")

    while True:
        await asyncio.sleep(1)


try:
    # set logging level for verbose debug messages
    _logger.setLevel(logging.DEBUG)

    # set environment variables
    env = NetworkEnv()
    env.putenv(NetworkEnv.WLAN_SSID, "S23")
    env.putenv(NetworkEnv.WLAN_PASSWORD, "q5fgITAC")

    _logger.info("Executing `main` coroutine")
    asyncio.run(main())
except KeyboardInterrupt:
    _logger.error("Caught `KeyboardInterrupt`")
finally:
    _logger.info("Cleaning asyncio `AbstractEventLoop`")
    # clean up asyncio `AbstractEventLoop`
    asyncio.get_event_loop().close()
    asyncio.new_event_loop()
