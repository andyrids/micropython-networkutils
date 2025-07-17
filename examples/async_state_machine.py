"""_summary_
"""
import asyncio
import logging
from networkutils.core import WLANMachine, _logger

async def main() -> None:
    """Main coroutine to start the WLAN interface FSM."""
    fsm = WLANMachine()
    fsm.start()

    while True:
        await asyncio.sleep(1)

try:
    _logger.setLevel(logging.DEBUG)
    _logger.info("Executing `main` coroutine")
    asyncio.run(main())
except KeyboardInterrupt:
    _logger.error("Raised `KeyboardInterrupt`")
finally:
    _logger.info("Cleaning asyncio `AbstractEventLoop`")
    # clean up asyncio `AbstractEventLoop`
    asyncio.get_event_loop().close()
    asyncio.set_event_loop(asyncio.new_event_loop())