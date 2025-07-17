# sourcery skip: use-contextlib-suppress
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false
"""A MicroPython `network` module utility functions package.

This `network-utils` package contains utility functions that help implement
concrete network classes within the MicroPython `network` module, such as the
`network.WLAN` class. These functions utilise `asyncio` to enable asynchronous
programming.

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
    async access_point_reset: Reset a WLAN instance and restart in Access
        Point (AP) mode.

    async activate_interface: Activate WLAN interface and wait 5 seconds for
        initialisation.

    async connect_interface: Connect a WLAN interface in STA mode.

    connection_issue: Test for a connection issue.

    async deactivate_interface: Deactivate a WLAN interface.

    get_network_interface: Initialise & return a `network.WLAN`
        interface instance.

    network_status_message: Print WLAN status debug messages.
"""

import asyncio
import binascii
import logging
import machine
import network
import sys
import time
from typing import Any, Awaitable, Callable, Coroutine, Iterable, Optional, Union


_DEVICE_ID = binascii.hexlify(machine.unique_id()).decode().upper()

# %(asctime)s - 
_formatter = logging.Formatter("[%(levelname)s]: %(message)s")
_stream_handler = logging.StreamHandler(stream=sys.stdout)
_stream_handler.setFormatter(_formatter)
_logger = logging.getLogger(__name__)
_logger.addHandler(_stream_handler)
_logger.setLevel(logging.DEBUG)


class WaitAny:
    """Event-like class that waits on an iterable of Event-like instances."""
    def __init__(self, events: tuple[asyncio.Event]) -> None:
        """Initialises the class with `Event` instances to wait for.

        Args:
            events (tuple[asyncio.Event]): `Event` instances to wait for.
        """
        self._any_event = asyncio.Event()
        self._events = events
        
    async def wait(self) -> asyncio.Event:
        """Await the setting of a trigger `Event` by any coroutine.

        Returns:
           asyncio.Event: The `Event` instance that set the trigger `Event`. 
        """
        tasks = map(self.create_task, self._events)
        try:
            # wait for any task to set this event
            await self.any_event.wait()
        finally:
            self.any_event.clear()
            cancelled = self.cancel_tasks(tasks)
        # a value of False indicates the task had completed
        return self._events[cancelled.index(False)]
        
    async def wait_any(self, event: asyncio.Event) -> Union[asyncio.Event, None]:
        """Awaits the passed `Event` & sets an `Event` trigger.

        Args:
            event (asyncio.Event): The `Event` instance to await.
        """
        await event.wait()
        self.event_trigger.set()

    @property
    def any_event(self) -> asyncio.Event:
        """Property for main `WaitAny` `Event` instance."""
        return self._any_event

    def cancel_tasks(self, tasks: Iterable[asyncio.Task]) -> tuple[bool, ...]:
        """Cancels `Task` instances.

        The `cancel` method returns True for those that were in-progress and
        False for those that were already completed.

        Args:
            tasks (Iterable[asyncio.Task]): `Task` instances to cancel.

        Returns:
            tuple[bool, ...]: The result of each called `cancel` method.
        """
        # in-progress & cancelled is True, finished & cancelled is False
        return tuple(map(lambda task: task.cancel(), tasks))

    def create_task(self, event: asyncio.Event) -> asyncio.Task:
        """Create a `Task` that awaits the passed `Event`."""
        return asyncio.create_task(self.wait_any(event))


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


class NetworkModeError(Exception):
    """Raised on incorrect network interface ID."""

    pass


class WLANCredentialsError(Exception):
    """Raised on incorrect WLAN credentials."""

    pass


class WLANConnectionError(Exception):
    """Raised on failed WLAN connection."""

    pass


class WLANNotFoundError(Exception):
    """Raised on SSID not found in available networks."""

    pass


class WLANTimeoutError(Exception):
    """Raised on failed WLAN connection timeout."""

    pass
        

async def access_point_reset(WLAN: network.WLAN) -> tuple[network.WLAN, int]:
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
    await deactivate_interface(WLAN)
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
    await activate_interface(WLAN)
    return WLAN, network.AP_IF


async def activate_interface(WLAN: network.WLAN) -> None:
    """Activate WLAN interface and wait 5 seconds for initialisation.

    NOTE: The active method does not behave as expected on the Pico W for STA
    mode - it will always return False (hence the timeout). This might be a
    nuance of the Pico W and should work on other microcontrollers.

    Args:
        WLAN (network.WLAN): WLAN interface instance.
    """
    _logger.debug("Activating network interface")
    # activate network interface
    WLAN.active(True)
    try:  # 5 second timeout
        await_timeout = iter(range(5))
        while next(await_timeout) >= 0:
            if WLAN.status() == network.STAT_GOT_IP or WLAN.active():
                _logger.debug("Network interface active - AP mode")
                break
            await asyncio.sleep(1)
    except StopIteration:
        _logger.debug("Network interface timeout - STA mode")


async def scan_networks(WLAN: network.WLAN) -> bool:
    """Scan for available WiFi networks.

    Indicates whether `WLAN_SSID` value is found in the available networks,
    if it is set in `NetworkEnv`.

    Args:
        WLAN (network.WLAN): WLAN interface instance.

    Returns:
        bool: True if `WLAN_SSID` is set in `NetworkEnv` and value is found
            in the available networks, else False.
    """
    env = NetworkEnv()

    WLAN_SSID = env.getenv("WLAN_SSID")
    if WLAN_SSID is None:
        _logger.debug("`WLAN_SSID` not set in `NetworkEnv`")
        return False
    networks = {name.decode() for name, *_ in set(WLAN.scan()) if name}
    if WLAN_SSID not in networks:
        _logger.error(f"SSID '{WLAN_SSID}' not found")
        _logger.debug(f"Available networks: {networks}")
        return False
    return True


async def connect_interface(WLAN: network.WLAN) -> None:
    """Connect a WLAN interface in STA mode.

    A connection is attempted using credentials stored in `WLAN_SSID` &
    `WLAN_PASSWORD` environment variables.

    Args:
        WLAN (network.WLAN): Activated WLAN interface.

    Raises:
        WLANConnectionError: Failed connection to access point.
        WLANCredentialsError: Incorrect credentials for access point.
        WLANNotFoundError: Access point not found in available networks.
    """
    try:
        env = NetworkEnv()
        WLAN_SSID = env.getenv("WLAN_SSID")
        WLAN_PASSWORD = env.getenv("WLAN_PASSWORD")

        if WLAN_PASSWORD is None:
            _logger.warning("`$WLAN_PASSWORD` not set in `NetworkEnv`")

        _logger.info(f"Connecting to SSID '{WLAN_SSID}'")

        # connect WLAN interface
        WLAN.connect(WLAN_SSID, WLAN_PASSWORD)
    # if WLAN is not in STA mode
    except (OSError, TypeError) as e:
        _logger.error(f"Error connecting to SSID '{WLAN_SSID}' - {e}")
        raise WLANConnectionError from e
    try:  # 30 second timeout
        _logger.debug("Waiting for WLAN connection")
        await_timeout = iter(range(30))
        while next(await_timeout) >= 0:
            _logger.debug(f"WLAN status code: {WLAN.status()}")
            if WLAN.status() < network.STAT_IDLE:
                raise WLANConnectionError
            if (WLAN.status == network.STAT_GOT_IP) or WLAN.isconnected():
                break
            await asyncio.sleep(1)
    except StopIteration as e:
        _logger.error(f"SSID '{WLAN_SSID}' connection timeout")
        raise WLANTimeoutError from e
    except WLANConnectionError as e:
        status_exception = {
            network.STAT_CONNECT_FAIL: WLANConnectionError,
            network.STAT_NO_AP_FOUND: WLANNotFoundError,
            network.STAT_WRONG_PASSWORD: WLANCredentialsError
        }
        raise status_exception.get(WLAN.status(), Exception) from e


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


async def deactivate_interface(WLAN: network.WLAN) -> None:
    """Deactivate a WLAN interface.

    NOTE: The `WLAN.active` method does not behave as expected on the Pico W
    for STA mode - it will always return False (hence the timeout). This might
    be a nuance of the Pico W and should work on other microcontrollers.

    Args:
        WLAN (network.WLAN): WLAN interface instance.

    Returns:
        None.
    """
    _logger.debug("Deactivating network interface")
    WLAN.active(False)

    try:  # 5 second timeout
        await_timeout = iter(range(5))
        while next(await_timeout) >= 0:
            if not WLAN.active():
                _logger.debug("Network interface inactive")
                break
            await asyncio.sleep(1)
    except StopIteration:
        _logger.debug("Deactivate network interface timeout")


def get_network_interface(
        mode: int = network.AP_IF,
        pm: int = network.WLAN.PM_NONE,
    ) -> network.WLAN:
    """Initialise & return a `network.WLAN` interface instance.

    The interface is initialised in either STA or AP mode depending on
    environment variable values and connection availability.

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
        mode (int): Network interface ID for STA/AP modes - `network.STA_IF`
            or `network.AP_IF`. Defaults to `network.AP_IF`.

        pm (int): Power management mode; `network.WLAN.PM_NONE`,
            `network.WLAN.PM_PERFORMANCE` or `network.WLAN.PM_POWERSAVE`.
            Defaults to `network.WLAN.PM_NONE`.

    Returns:
        network.WLAN: A `network.WLAN` instance.
    """
    if mode not in (network.AP_IF, network.STA_IF):
        _logger.error(f"Incorrect Network mode (`{mode}`)")
        raise NetworkModeError

    _logger.debug("Initialising WLAN interface")

    interface = network.WLAN(mode)
    interface.config(pm=pm)
    return interface


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


# ------ Hierarchical Finite State Machine Classes ------ #

class State:
    """Base class for individual atomic states."""

    def __init__(
            self, machine: "Machine", in_composite: bool = False
    ) -> None:
        self._machine = machine
        self._in_composite = in_composite

    @property
    def machine(self) -> "Machine":
        """"""
        return self._machine
    
    @property
    def in_composite(self) -> bool:
        """"""
        return self._in_composite

    async def on_enter(
            self,
            coro: Optional[Callable[[], Coroutine[Any, Any, Any]]] = None
        ) -> None:
        """Coroutine to run on entering state."""
        coro_name = coro.__name__ if coro else "NOP"
        _logger.debug(f"Executing `State.on_enter` - `{coro_name}`")
        if coro:
            await coro()

    async def on_exit(
            self,
            coro: Optional[Callable[[], Coroutine[Any, Any, Any]]] = None
        ) -> None:
        """Coroutine to run on exiting state."""
        coro_name = coro.__name__ if coro else "NOP"
        _logger.debug(f"Executing `State.on_exit` - `{coro_name}`")
        if coro:
            await coro()

    async def run(self) -> None:
        """"""
        _logger.debug("Executing `State.run`")
        raise NotImplementedError("Missing abstract `State.run` method")


class CompositeState(State):
    """Base class for composite states."""
    def __init__(
            self,
            machine: "Machine",
            initial_substate_cls: Optional[type["State"]] = None
        ) -> None:
        super().__init__(machine)
        self._substate = None
        self._initial_substate_cls = initial_substate_cls

    @property
    def substate(self) -> Union[State, None]:
        """Current substate property."""
        return self._substate

    async def on_enter(self) -> None:
        _logger.debug("Executing `CompositeState.on_enter`")
        await super().on_enter()
        if self._initial_substate_cls:
            _logger.info(
                f"Initial substate -> `{self._initial_substate_cls}`"
            )
            await self.change_substate(
                self._initial_substate_cls(self.machine, in_composite=True)
            )

    async def on_exit(self) -> None:
        substate = self.substate
        if isinstance(substate, State):
            await substate.on_exit()
            self._substate = None
        await super().on_exit()
    
    async def run(self) -> None:
        """Run current substate logic."""
        substate = self.substate
        if isinstance(substate, State):
            await substate.run()
        else:
            await asyncio.sleep_ms(100)

    async def change_substate(self, new_substate: State) -> None:
        """"""
        _logger.info("Executing `CompositeState.change_substate`")
        substate = self.substate
        if isinstance(substate, State):
            await substate.on_exit()
            _logger.info(
                f"{substate.__class__.__name__} -> {new_substate.__class__.__name__}"
            )
        
        await new_substate.on_enter()
        self._substate = new_substate


# ------ State Classes ------ #

class UninitialisedState(State):
    """Initial `State` before `network.WLAN` initialisation."""
    async def run(self) -> None:
        # `UninitialisedState` -> `InitialisingState`
        await self.machine.transition(InitialisingState(self.machine))


class InitialisingState(State):
    """Initialise `network.WLAN` interface in AP | STA mode."""
    async def run(self) -> None:
        """"""
        try:
            # transition to WLAN mode selection
            await self.machine.transition(WLANModeChoiceState(self.machine))
        except OSError as e:
            await self.machine.transition(
                TerminalErrorState(
                    self.machine,
                    f"Error transitioning -> WLANModeChoiceState ({e})"
                )
            )


class WLANModeChoiceState(State):
    """
    A transient choice state that decides the next mode (AP or STA)
    based on the context's configuration.
    """
    async def run(self) -> None:
        """"""
        env = NetworkEnv()
        AP_SSID = env.getenv("AP_SSID")
        AP_PASSWORD = env.getenv("AP_PASSWORD")

        if AP_SSID is None or AP_PASSWORD is None:
            AP_SSID = f"DEVICE-{_DEVICE_ID}"
            AP_PASSWORD = _DEVICE_ID
            env.putenv("AP_SSID", AP_SSID)
            env.putenv("AP_PASSWORD", _DEVICE_ID)

        WLAN_SSID = env.getenv("WLAN_SSID")
        # select WLAN instance mode based on credential values
        if WLAN_SSID is None or len(WLAN_SSID) < 1:
            self.machine._WLAN = get_network_interface(network.AP_IF)
            self.machine.WLAN.config(ssid=AP_SSID, password=AP_PASSWORD)
            await self.machine.transition(APModeState(self.machine))
        else:
            self.machine._WLAN = get_network_interface(network.STA_IF)
            await self.machine.transition(STAModeState(self.machine))


# ------ AP Mode Composite State Classes ------ #

class APModeState(CompositeState):
    """Container state for all Access Point (AP) mode operations."""
    def __init__(self, machine: "Machine") -> None:
        """"""
        super().__init__(machine, initial_substate_cls=InactiveAPState)


class InactiveAPState(State):
    """The AP interface is initialised but not active."""
    async def run(self) -> None:
        await self.machine.transition(
            ActivatingAPState(self.machine, in_composite=True), in_composite=True)


class ActivatingAPState(State):
    """Activate the AP interface."""
    async def run(self) -> None:
        await activate_interface(self.machine.WLAN)
        await self.machine.transition(ActiveAPState(self.machine), in_composite=True)


class ActiveAPState(CompositeState):
    """The AP is active and broadcasting."""
    def __init__(self, machine: "Machine"):
        super().__init__(machine, BroadcastingState)


class BroadcastingState(State):
    """The AP is actively broadcasting its network."""
    async def run(self) -> None:
        _logger.info("AP Mode - `BroadcastingState`")

        # 1. Handle client connections
        # 2. Await Event for `DeactivatingAPState`
        while True:
            await asyncio.sleep(5)


class DeactivatingAPState(State):
    """Deactivate the AP interface."""
    async def run(self):
        await asyncio.sleep(1)
        await self.machine.transition(InactiveAPState(self.machine), in_composite=True)


# ------ STAModeState Composite State ------ #

class STAModeState(CompositeState):
    """Composite state for all Client (STA) mode operations."""
    def __init__(self, machine: "Machine") -> None:
        """"""
        super().__init__(machine, InactiveSTAState)


# STAModeState [Composite]
# ├── InactiveSTAState
# ├── ActivatingSTAState
# ├── ActiveSTAState [Composite]
# │   ├── DisconnectedSTAState
# │   ├── ScanningSTAState
# │   ├── ConnectingSTAState
# │   ├── ConnectedSTAState
# │   ├── STAConnectionErrorState
# │   └── DeactivatingSTAState
# └── ResettingState


class InactiveSTAState(State):
    """The STA interface is initialised but not active."""
    async def run(self) -> None:
        await self.machine.transition(
            ActivatingSTAState(self.machine, in_composite=True), in_composite=True
        )
    

class ActivatingSTAState(State):
    """The STA interface is activating."""
    async def run(self) -> None:
        await activate_interface(self.machine.WLAN)
        await self.machine.transition(
            ActiveSTAState(self.machine), in_composite=True
        )


class ActiveSTAState(CompositeState):
    """Composite state for active Client interface operations."""
    def __init__(self, machine: "Machine") -> None:
        super().__init__(machine, DisconnectedSTAState)


class DisconnectedSTAState(State):
    """The STA interface is not connected to an Access Point"""
    async def run(self) -> None:
        await self.machine.transition(
            ScanningSTAState(self.machine, in_composite=True),
            in_composite=True
        )


class ScanningSTAState(State):
    """The STA interface is not connected to an Access Point"""
    async def run(self) -> None:
        if await scan_networks(self.machine.WLAN):
            await self.machine.transition(
                ConnectingSTAState(self.machine, in_composite=True),
                in_composite=True
            )
        else:
            raise WLANConnectionError


class ConnectingSTAState(State):
    """The STA interface is not connected to an Access Point."""
    async def run(self) -> None:
        try:
            await connect_interface(self.machine.WLAN)
            await self.machine.transition(
                ConnectedSTAState(self.machine, in_composite=True),
                in_composite=True
            )
        except (
            WLANConnectionError, WLANCredentialsError, WLANTimeoutError
        ) as e:
            _logger.error(e.__class__.__name__)
            await self.machine.transition(
                STAConnectionErrorState(
                    self.machine, in_composite=True, exception=e
                ),
                in_composite=True
            )


class ConnectedSTAState(State):
    """The STA interface is connected to an Access Point."""
    async def run(self) -> None:
        env = NetworkEnv()
        WLAN_SSID = env.getenv("WLAN_SSID")
        while True:
            await asyncio.sleep(10)
            if not self.machine.WLAN.isconnected():
                _logger.error(f"Connection error - SSID '{WLAN_SSID}'")
                await self.machine.transition(
                    STAConnectionErrorState(self.machine, in_composite=True),
                    in_composite=True
                )
                break


class STAConnectionErrorState(State):
    """The STA interface experienced a connection error."""
    def __init__(
            self,
            machine: "Machine",
            in_composite: bool = True,
            exception: Optional[Exception] = None,
            timeout: int = 30
        ) -> None:
        """"""
        super().__init__(machine, in_composite)
        self._exception = exception
        self._timeout = timeout

    @property
    def exception(self) -> Union[Exception, None]:
        """`Exception` trigger property."""
        return self._exception

    @property
    def timeout(self) -> int:
        """`Exception` trigger property."""
        return self._timeout

    async def run(self) -> None:
        """"""
        if isinstance(self.exception, Exception):
            raise self.exception

        await asyncio.sleep(self.timeout)
        if self.machine.WLAN.isconnected():
            await self.machine.transition(
                ConnectedSTAState(self.machine, in_composite=True),
                in_composite=True
            )
        else:
            await self.machine.transition(
                DisconnectedSTAState(self.machine, in_composite=True),
                in_composite=True
            )


class DeactivatingSTAState(State):
    """The STA interface is deactivating."""
    async def run(self) -> None:
        await deactivate_interface(self.machine.WLAN)
        await self.machine.transition(
            InactiveSTAState(self.machine), in_composite=True
        )


# ------------------------------------------ #


class ResettingState(State):
    """Reset network interface."""
    async def run(self) -> None:
        """"""
        await self.machine.transition(InitialisingState(self.machine))
    
    def on_exit(self) -> None:
        """"""
        _logger.debug("`ResettingState`")


class TerminalErrorState(State):
    """A terminal error state."""
    def __init__(self, machine: "Machine", message: str) -> None:
        """"""
        super().__init__(machine)
        self._message = message

    async def run(self) -> None:
        """"""
        # await asyncio.sleep(3600)
        await asyncio.sleep(10)


# ------ Finite State Machine Classes ------ #


class Machine:
    """Abstract base class for individual State Machines."""

    def __init__(self, current_state: State) -> None:
        """Initialise the Finite State Machine (FSM).

        Args:
            current_state (State): The current state of the FSM.
        """
        self._current_state = current_state

    @property
    def current_state(self) -> State:
        """Current FSM `State` property."""
        return self._current_state

    @property
    def current_state_name(self) -> str:
        """Current FSM `State` class name property."""
        return self.current_state.__class__.__name__

    async def transition(
            self,
            new_state: State,
            in_composite: bool = False
        ) -> None:
        """Transition to a new `State`.
        
        Args:
            new_state (State): New `State` to transition to.

            in_composite (bool): New `State` in `CompositeState` flag.
                Defaults to False.
        """
        _logger.info("Executing `Machine.transition`")
        _logger.info(
            f"{self.current_state_name} -> {new_state.__class__.__name__}"
        )

        if in_composite and isinstance(self.current_state, CompositeState):
            # delegate transition to parent `CompositeState`
            await self.current_state.change_substate(new_state)
        else:
            # top-level 'Atomic' `State` transition
            await self.current_state.on_exit()
            await new_state.on_enter()
            self._current_state = new_state

    async def run(self) -> None:
        """Main execution loop."""
        _logger.info("Executing `Machine.run`")
        await self.current_state.on_enter()
        while True:
            await self.current_state.run()
            await asyncio.sleep_ms(10)

    def start(self) -> None:
        """Abstract `start` method to be implemented."""
        _logger.info("Executing `Machine.start`")
        raise NotImplementedError("Missing `Machine.start` method")


class WLANMachine(Machine):
    """WLAN interface Finite State Machine (FSM)."""
    def __init__(self) -> None:
        """Initialise FSM."""
        super().__init__(current_state=UninitialisedState(self))
        self._WLAN = None
        self._WLAN_MODE = None

    # --- Public API --- #

    def start(self) -> asyncio.Task:
        """Starts the FSM `run` coroutine `Task`."""
        _logger.info("Executing `WLANMachine.start`")
        return asyncio.create_task(self.handle_exceptions(self.run))

    @property
    def WLAN(self) -> network.WLAN:
        """FSM WLAN interface property."""
        if isinstance(self._WLAN, network.WLAN):
            return self._WLAN
        raise TypeError("`_WLAN` not set to a `network.WLAN` instance")

    async def handle_exceptions(
            self, coro: Callable[[], Coroutine[Any, Any, Any]]
        ) -> None:
        """Handle WLAN-related exceptions in `run` coroutine."""
        try:
            await coro()
        except (WLANConnectionError, NetworkModeError) as e:
            _logger.error(f"`{e.__class__.__name__}`")
            await self.transition(
                TerminalErrorState(self, e.__class__.__name__),
            )
        except WLANCredentialsError as e:
            _logger.error(f"`{e.__class__.__name__}`")
            _logger.error("Check `NetworkEnv` `$WLAN_PASSWORD` value")
            await self.transition(
                TerminalErrorState(self, str(e)),
            )
        except Exception as e:
            _logger.error(f"`{e.__class__.__name__}`")
        finally:
            _logger.info("`WLANMachine.handle_exceptions` cleanup")
            await deactivate_interface(self.WLAN)
            raise SystemExit


async def main() -> None:
    """"""
    env = NetworkEnv()
    env.putenv("WLAN_SSID", "S23")
    env.putenv("WLAN_PASSWORD", "q5fgITAC")

    fsm = WLANMachine()
    fsm.start()

    while True:
        await asyncio.sleep(1)


try:
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
    # reset MicroPython's single event loop state
    asyncio.new_event_loop()
