"""Example Finite State Machine usage in AP mode"""

import asyncio
import logging
import network
from networkutils.core import WLANMachine, _logger


async def main() -> None:
    """Runs FSM main coroutine."""
    fsm = WLANMachine(mode=network.AP_IF, reset_state=False)
    fsm.start()

    while True:
        await asyncio.sleep(1)


try:
    _logger.setLevel(logging.DEBUG)
    _logger.info("Executing `main`")
    asyncio.run(main())
except KeyboardInterrupt:
    _logger.info("Caught `KeyboardInterrupt`")
except SystemExit:
    _logger.info("Caught `SystemExit`")
finally:
    _logger.info("Cleaning asyncio `AbstractEventLoop`")
    # clean up asyncio `AbstractEventLoop`
    asyncio.get_event_loop().close()
    asyncio.new_event_loop()