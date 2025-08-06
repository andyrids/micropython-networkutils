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

    WLAN_SSID = "WLAN_SSID"
    WLAN_PASSWORD = "WLAN_PASSWORD"
    AP_SSID = "AP_SSID"
    AP_PASSWORD = "AP_PASSWORD"

    _instance = None
    _env = {}

    def __new__(cls) -> "NetworkEnv":
        """Return a `singleton` instance of the `NetworkEnv` class.

        1. `WLAN_SSID` - Access Point to connect to in STA mode 
        2. `WLAN_PASSWORD` - Access Point password
        3. `AP_SSID` - Broadcasting Access Point SSID in AP mode
        4. `AP_PASSWORD` - Broadcasting Access Point password in AP mode

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
            key: Environment variable key.

        Returns:
            Environment variable value or None.
        """
        value = self._env.get(key)
        return str(value) if value else None

    def putenv(self, key: str, value: str) -> None:
        """Set environment variable in `_env` property.

        Args:
            key: Environment variable key.

            value: Environment variable value.
        """
        self._env[key] = value
    
    def delenv(self, key: str) -> None:
        """Deletes an environment variable.

        Args:
            key: Environment variable key.
        """
        if self.getenv(key):
            del self._env[key]

class NetworkModeError(Exception):
    """Raised on incorrect network interface ID."""

    pass


class WLANCredentialsError(Exception):
    """Raised on incorrect WLAN credentials."""

    pass


class WLANConnectionError(Exception):
    """Raised on failed WLAN connection."""

    pass


class WLANInitialisationError(Exception):
    """Raised on incorrect WLAN mode."""

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
                _logger.debug("Network interface active")
                break
            await asyncio.sleep(1)
    except StopIteration:
        _logger.debug("Network interface activation timeout")


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
        WLAN: WLAN interface instance.
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


async def uninitialise_interface(WLAN: network.WLAN) -> None:
    """Uninitialise a WLAN interface.
    
    Args:
        WLAN: WLAN interface instance.
    """
    _logger.debug("Unitialising network interface")
    if isinstance(WLAN, network.WLAN):
        WLAN.disconnect()
        await deactivate_interface(WLAN)
        WLAN.deinit()

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
    mode_name = ("STA", "AP")[mode]
    _logger.debug(f"Initialising WLAN interface in {mode_name} mode")

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
        """Initialises a `State` class.

        Args:
            machine: A Concrete `Machine` instance that manages the
                `State` as a Finite State Machine (FSM).

            in_composite: Within a `CompositeState` hierarchy flag. Defaults
                to False.
        """
        self._machine = machine
        self._in_composite = in_composite

    @property
    def machine(self) -> "Machine":
        """Reference to the FSM."""
        return self._machine
    
    @property
    def hierarchy(self) -> str:
        """Concrete `State` hierarchy (atomic states have 1 level)."""
        return self.name

    @property
    def name(self) -> str:
        """Class name (most-derived)."""
        return self.__class__.__name__
    
    @property
    def in_composite(self) -> bool:
        """`CompositeState` substate flag."""
        return self._in_composite

    async def on_enter(
            self,
            coro: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None,
            *args
        ) -> None:
        """Coroutine to run on state entry."""
        coro_name = coro.__name__ if coro else "NOP"
        _logger.debug(f"Executing `{self.name}.on_enter` - `{coro_name}`")
        if coro:
            await coro(*args)

    async def on_exit(
            self,
            coro: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None,
            *args
        ) -> None:
        """Coroutine to run on state exit."""
        coro_name = coro.__name__ if coro else "NOP"
        _logger.debug(f"Executing `{self.name}.on_exit` - `{coro_name}`")
        if coro:
            await coro(*args)

    async def run(self) -> None:
        """Abstract method to be implemented by a concrete `State`."""
        _logger.debug(f"Executing `{self.name}.run`")
        raise NotImplementedError("Missing abstract `State.run` method")


class CompositeState(State):
    """Base class for composite states."""
    def __init__(
            self,
            machine: "Machine",
            initial_substate_cls: Optional[type["State"]] = None,
            in_composite: bool = False,
        ) -> None:
        """Initialises a `CompositeState` class.
        
        Args:
            machine: A Concrete `Machine` instance that manages the
                `CompositeState`.
            
            initial_substate_cls: A concrete `State` class to instantiate and
                set as the initial substate. Defaults to None.
            
            in_composite: Within a `CompositeState` hierarchy flag. Defaults
                to False.
            """
        super().__init__(machine, in_composite)
        self._substate = None
        self._initial_substate_cls = initial_substate_cls

    @property
    def hierarchy(self) -> str:
        """Concrete `CompositeState` hierarchy."""
        hierarchy_str = self.substate.hierarchy if self.substate else "None"
        # e.g. 'APModeState[ActiveAPState[BroadcastingState]]'
        return f"{self.name}[{hierarchy_str}]"

    @property
    def substate(self) -> Union[State, None]:
        """Current substate property."""
        return self._substate

    async def on_enter(
            self,
            coro: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None,
            *args
        ) -> None:
        """Executes logic & coroutines on state entry.

        Args:
            coro: Coroutine to be run on state entry.

            *args: Coroutine arguments.
        """
        await super().on_enter(coro, *args)
        if self._initial_substate_cls:
            _logger.info(f"Initial `{self.name}.change_substate`")
            await self.change_substate(
                self._initial_substate_cls(self.machine, in_composite=True)
            )

    async def on_exit(
            self,
            coro: Optional[Callable[..., Coroutine[Any, Any, Any]]] = None,
            *args
        ) -> None:
        """Executes logic & coroutines on state exit.

        Args:
            coro: Coroutine to be run on state exit.

            *args: Coroutine arguments.
        """
        substate = self.substate
        if isinstance(substate, State):
            await substate.on_exit()
            self._substate = None
        await super().on_exit(coro, *args)
    
    async def run(self) -> None:
        """Run current substate logic."""
        substate = self.substate
        if isinstance(substate, State):
            await substate.run()
        else:
            await asyncio.sleep_ms(100)

    async def change_substate(
            self, new_substate: Union["CompositeState", State]
        ) -> None:
        """Transitions current substate to another.
        
        If current substate is a `CompositeState`, transition is delegated to
        `substate.change_substate`.

        Args:
           new_substate: New substate instance.
        """

        substate = self.substate
        if isinstance(substate, CompositeState) and new_substate.in_composite:
            # delegate transition to child `CompositeState`
            await substate.change_substate(new_substate)
            return

        if isinstance(substate, State):
            await substate.on_exit()
            _logger.info(
                f"{self.name}[{substate.name} -> {new_substate.name}]"
            )
        else:
            _logger.info(f"{self.name}[None -> {new_substate.name}]")
        await new_substate.on_enter()
        self._substate = new_substate


# ------ State Classes ------ #

class UninitialisedState(State):
    """The `WLAN` interface is not initialised."""
    async def run(self) -> None:
        """Transitions to `WLANModeChoiceState`."""
        try:
            # transition to WLAN mode selection
            await self.machine.transition(WLANModeChoiceState(self.machine))
        except OSError as e:
            await self.machine.transition(
                TerminalErrorState(
                    self.machine, f"Error in `WLANModeChoiceState` ({e})"
                )
            )


class WLANModeChoiceState(State):
    """Transient choice state for `WLAN` initialisation mode (AP | STA).
    
    The WLAN interface mode is based on the `machine.WLAN_MODE` value,
    if set, or the `NetworkEnv` environment variables. STA mode is
    selected if `WLAN_SSID` is set, else AP. `AP_SSID` defaults to
    'DEVICE-[Microcontroller ID]' and `AP_PASSWORD` defaults to
    [Microcontroller ID] if not set.
    """
    async def run(self) -> None:
        """Transitions to `APModeState` | `STAModeState`."""

        MODE = self.machine.WLAN_MODE
        if MODE is None or not network.STA_IF <= MODE <= network.AP_IF:
            env = NetworkEnv()
            WLAN_SSID = env.getenv(NetworkEnv.WLAN_SSID)
            # select WLAN instance mode based on credential values
            if WLAN_SSID is None or len(WLAN_SSID) < 1:
                MODE = network.AP_IF
            else:
                MODE = network.STA_IF

        await self.machine.transition(
            InitialisingState(self.machine, wlan_mode=MODE)
        )


class InitialisingState(State):
    """The `WLAN` interface is initialising in AP | STA mode."""

    def __init__(
            self,
            machine: "Machine",
            in_composite: bool = False,
            *,
            wlan_mode: int
        ) -> None:
        """Initialises the `InitialisingState` class.

        Args:
            machine: A Concrete `Machine` instance that manages the
                `State`.

            in_composite: Within a `CompositeState` hierarchy flag. Defaults
                to False.

            wlan_mode: WLAN mode to initialise the interface in, 
                either STA (0) | AP (1).

        Raises:
            WLANInitialisationError: If `wlan_mode` is not valid.
        """
        super().__init__(machine, in_composite)
        if not network.STA_IF <= wlan_mode <= network.AP_IF:
            raise WLANInitialisationError

        self.machine._WLAN = get_network_interface(wlan_mode)
        self.machine._WLAN_MODE = wlan_mode

        env = NetworkEnv()
        self.machine.WLAN.config(
            ssid=env.getenv(env.AP_SSID),
            password=env.getenv(env.AP_PASSWORD)
        )

    async def run(self) -> None:
        """Transitions to `WLANModeChoiceState`."""

        if self.machine.WLAN_MODE == network.STA_IF:
            await self.machine.transition(
                STAModeState(self.machine, InactiveSTAState)
            )
        else:
            await self.machine.transition(
                    APModeState(self.machine, InactiveAPState)
                )

# ------ AP Mode Composite State Classes ------ #

class APModeState(CompositeState):
    """Container `CompositeState` for each AP mode `State`.
    
    APModeState [Composite]
    ├── InactiveAPState
    ├── ActivatingAPState
    ├── ActiveAPState [Composite]
    │   └── BroadcastingState
    └── DeactivatingAPState
    """


class InactiveAPState(State):
    """The `WLAN` AP is initialised but not active."""
    async def run(self) -> None:
        """Transitions to `ActivatingAPState`."""
        await self.machine.transition(
            ActivatingAPState(self.machine, in_composite=True)
        )


class ActivatingAPState(State):
    """The `WLAN` AP is activating."""

    async def on_enter(self) -> None:
        """Calls `activate_interface` on state entry."""
        await super().on_enter(activate_interface, self.machine.WLAN)

    async def run(self) -> None:
        """Transitions to `BroadcastingState`."""
        await self.machine.transition(
            ActiveAPState(self.machine, BroadcastingState, in_composite=True)
        )


class ActiveAPState(CompositeState):
    """Container `CompositeState` for each active AP mode `State`.

    ActiveAPState [Composite]
    └── BroadcastingState
    """


class BroadcastingState(State):
    """The `WLAN` AP is actively broadcasting its network."""
    async def run(self) -> None:
        """TODO: implement logic on device connection to AP."""
        SSID = self.machine.WLAN.config("ssid")
        _logger.info(f"Broadcasting SSID '{SSID}'")

        # 1. Handle client connections
        # 2. Await Event for `DeactivatingAPState`
        while True:
            await asyncio.sleep(5)


class DeactivatingAPState(State):
    """The `WLAN` AP is deactivating."""

    async def on_enter(self) -> None:
        """Calls `deactivate_interface` on state entry."""
        await super().on_enter(deactivate_interface, self.machine.WLAN)

    async def run(self) -> None:
        """Transitions to `InactiveAPState`."""
        await asyncio.sleep(1)
        await self.machine.transition(
            InactiveAPState(self.machine, in_composite=True),
        )


# ------ STAModeState Composite State ------ #

class STAModeState(CompositeState):
    """Container `CompositeState` for each STA mode `State`.
    
    STAModeState [Composite]
    ├── InactiveSTAState
    ├── ActivatingSTAState
    ├── ActiveSTAState [Composite]
    │   ├── DisconnectedSTAState
    │   ├── ScanningSTAState
    │   ├── ConnectingSTAState
    │   ├── ConnectedSTAState
    │   └── STAConnectionErrorState
    └── DeactivatingSTAState
    """


class InactiveSTAState(State):
    """The `WLAN` STA is initialised but not active."""
    async def run(self) -> None:
        """Transitions to `ActivatingSTAState`."""
        await self.machine.transition(
            ActivatingSTAState(self.machine, in_composite=True)
        )


class ActivatingSTAState(State):
    """The `WLAN` STA is activating."""

    async def on_enter(self) -> None:
        """Calls `activate_interface` on state entry."""
        await super().on_enter(activate_interface, self.machine.WLAN)

    async def run(self) -> None:
        """Transitions to `ActiveSTAState[DisconnectedSTAState]`."""
        await self.machine.transition(
            ActiveSTAState(
                self.machine,
                in_composite=True,
                initial_substate_cls=DisconnectedSTAState
            ),
        )


class ActiveSTAState(CompositeState):
    """Container `CompositeState` for each active STA mode `State`.

    ActiveSTAState [Composite]
    ├── DisconnectedSTAState
    ├── ScanningSTAState
    ├── ConnectingSTAState
    ├── ConnectedSTAState
    └── STAConnectionErrorState
    """

class DisconnectedSTAState(State):
    """The `WLAN` STA is not connected to an Access Point."""

    async def run(self) -> None:
        """Transitions to `ScanningSTAState`."""
        await self.machine.transition(
            ScanningSTAState(self.machine, in_composite=True),
        )


class ScanningSTAState(State):
    """The `WLAN` STA is scanning for available Access Points."""

    async def run(self) -> None:
        """Transitions to `ConnectingSTAState`."""
        if await scan_networks(self.machine.WLAN):
            await self.machine.transition(
                ConnectingSTAState(self.machine, in_composite=True)
            )
        else:
            raise WLANConnectionError


class ConnectingSTAState(State):
    """The `WLAN` STA is connecting to an Access Point."""

    async def run(self) -> None:
        try:
            await connect_interface(self.machine.WLAN)
            await self.machine.transition(
                ConnectedSTAState(self.machine, in_composite=True)
            )
        except (
            WLANConnectionError, WLANCredentialsError, WLANTimeoutError
        ) as e:
            _logger.error(f"Caught {e.__class__.__name__}")
            await self.machine.transition(
                STAConnectionErrorState(
                    self.machine, in_composite=True, exception=e
                )
            )


class ConnectedSTAState(State):
    """The `WLAN` STA is connected to an Access Point."""
    async def run(self) -> None:
        """Transitions to `STAConnectionErrorState` on connection error.

        Monitors `WLAN` connection every 5 seconds.
        """
        env = NetworkEnv()
        WLAN_SSID = env.getenv("WLAN_SSID")
        while True:
            await asyncio.sleep(5)
            if not self.machine.WLAN.isconnected():
                _logger.error(f"Connection error - SSID '{WLAN_SSID}'")
                await self.machine.transition(
                    STAConnectionErrorState(self.machine, in_composite=True)
                )
                break


class STAConnectionErrorState(State):
    """The `WLAN` STA experienced a connection error."""

    def __init__(
            self,
            machine: "Machine",
            in_composite: bool = True,
            exception: Optional[Exception] = None,
            timeout: int = 30
        ) -> None:
        """Initialises `STAConnectionErrorState`.

        If a valid `Exception` instance is passed to `exception`, it is
        raised when the `run` method is called.

        Args:
            machine: A Concrete `Machine` instance that manages the
                `State`.

            in_composite: Within a `CompositeState` hierarchy flag. Defaults
                to False.

            exception: An exception instance to raise.

            timeout: A timeout value (seconds) to await for reconnection to an
                Access Point. Defaults to 30.
        """
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
        """Transitions to `ConnectedSTAState` | `DisconnectedSTAState`."""
        if isinstance(self.exception, Exception):
            raise self.exception

        await asyncio.sleep(self.timeout)
        if self.machine.WLAN.isconnected():
            await self.machine.transition(
                ConnectedSTAState(self.machine, in_composite=True),
            )
        # STAConnectionErrorState -> DisconnectedSTAState -> ScanningSTAState
        else:
            await self.machine.transition(
                DisconnectedSTAState(self.machine, in_composite=True),
            )


class DeactivatingSTAState(State):
    """The `WLAN` STA is deactivating."""

    async def on_enter(self) -> None:
        """Calls `deactivate_interface` on state exit."""
        await super().on_enter(deactivate_interface, self.machine.WLAN)

    async def run(self) -> None:
        """Transitions to `InactiveSTAState`."""
        await self.machine.transition(
            InactiveSTAState(self.machine, in_composite=True)
        )


# ------------------------------------------ #


class ResettingState(State):
    """The `WLAN` is resetting."""

    async def run(self) -> None:
        """Transitions to `InitialisingState`."""
        await self.machine.transition(UninitialisedState(self.machine))


class TerminalErrorState(State):
    """The `WLAN` is in a terminal error state."""

    def __init__(
            self, machine: "Machine",
            message: str,
            reset_state: bool = False
        ) -> None:
        """Initialises `TerminalErrorState`.

        Args:
            machine: A Concrete `Machine` instance that manages the
                `State`.

            message: Error message detailing cause of `TerminalErrorState`
                transition.

            reset_state: A flag allowing transition to `ResettingState` if
                True. Defaults to False.
        """
        super().__init__(machine)
        self._message = message
        self._reset_state = reset_state
    
    @property
    def reset_state(self) -> bool:
        """Transition to `ResettingState` flag."""
        return self._reset_state

    @property
    def message(self) -> str:
        """Terminal error details message."""
        return self._message

    async def run(self) -> None:
        """Terminates FSM main loop or transitions to `ResettingState`."""
        _logger.info(f"Terminal error - {self.message}")
        await asyncio.sleep(5)
        if self.access_point_reset:
            env = NetworkEnv()
            env.delenv(NetworkEnv.WLAN_SSID)
            env.delenv(NetworkEnv.WLAN_PASSWORD)
            await self.machine.transition(ResettingState(self.machine))


# ------ Finite State Machine Classes ------ #


class Machine:
    """Abstract base class for individual State Machines."""

    def __init__(self, current_state: State) -> None:
        """Initialises the Finite State Machine (FSM).

        Args:
            current_state: The current state of the FSM.
        """
        self._current_state = current_state

    @property
    def current_state(self) -> State:
        """Current FSM `State`."""
        return self._current_state

    @property
    def name(self) -> str:
        """FSM class name."""
        return self.__class__.__name__

    async def transition(self, new_state: State) -> None:
        """Transitions to a new `State`.

        Args:
            new_state: New `State` to transition to.
        """
        _logger.info(f"Executing `{self.name}.transition`")
        if new_state.in_composite and isinstance(self.current_state, CompositeState):
            # delegate transition to parent `CompositeState`
            await self.current_state.change_substate(new_state)
        else:
            # top-level 'Atomic' `State` transition
            _logger.info(f"{self.current_state.name} -> {new_state.name}")
            await self.current_state.on_exit()
            await new_state.on_enter()
            self._current_state = new_state
        _logger.info(f"{self.name}[{self.current_state.hierarchy}]")

    async def run(self) -> None:
        """Executes the main FSM execution loop logic."""
        _logger.info(f"Executing `{self.name}.run`")
        await self.current_state.on_enter()
        while True:
            await self.current_state.run()
            await asyncio.sleep_ms(10)

    def start(self) -> None:
        """Abstract `start` method to be implemented by concrete FSM."""
        _logger.info("Executing `Machine.start`")
        raise NotImplementedError("Missing `Machine.start` method")


class WLANMachine(Machine):
    """WLAN interface Finite State Machine (FSM)."""
    def __init__(
            self,
            wlan_mode: Optional[int] = None,
            reset_state: bool = False
        ) -> None:
        """Initialises the FSM.
        
        Args:
            wlan_mode: Specifies which mode to initialise the WLAN interface,
                STA (0) or AP (1). Defaults to None.

            reset_state: Causes a reset to Access Point mode, if the
                FSM transitions from `STAModeState` -> `TerminalErrorState`.
        """
        super().__init__(current_state=UninitialisedState(self))
        self._WLAN = None
        self._WLAN_MODE = wlan_mode in (network.STA_IF, network.AP_IF) or None
        self._reset_state = reset_state

        env = NetworkEnv()
        AP_SSID = env.getenv(NetworkEnv.AP_SSID)
        AP_PASSWORD = env.getenv(NetworkEnv.AP_PASSWORD)
        if AP_SSID is None or AP_PASSWORD is None:
            env.putenv(NetworkEnv.AP_SSID, f"DEVICE-{_DEVICE_ID}")
            env.putenv(NetworkEnv.AP_PASSWORD, _DEVICE_ID)

    # --- Public API --- #

    def start(self) -> asyncio.Task:
        """Starts the FSM `run` coroutine `Task`.
        
        The `Machine.run` coroutine executes the FSM current `State.on_enter`
        and `State.run` coroutines. When a state calls `Machine.transition`,
        this method handles `on_exit` of the current state and `on_entry` of
        the new state. The `Machine.run` loop will then call the new current
        state `run` method.

        Returns:
            A `asyncio.Task` instance for the main FSM coroutine.
        """
        _logger.info("Executing `WLANMachine.start`")
        # `handle_exceptions` facilitates terminal error transition logic
        return asyncio.create_task(self.handle_exceptions(self.run))

    @property
    def WLAN(self) -> network.WLAN:
        """FSM WLAN interface property."""
        if isinstance(self._WLAN, network.WLAN):
            return self._WLAN
        raise TypeError("`_WLAN` not set to a `network.WLAN` instance")

    @property
    def WLAN_MODE(self) -> Union[int, None]:
        """WLAN mode value network.STA_IF (0) |`network.AP_IF` (1)."""
        return self._WLAN_MODE

    @property
    def reset_state(self) -> bool:
        """Access Point mode reset flag."""
        return self._reset_state

    async def handle_exceptions(
            self, coro: Callable[[], Coroutine[Any, Any, Any]]
        ) -> None:
        """Handle WLAN-related exceptions in `run` coroutine.
        
        Facilitates transitions based on exceptions and avoids having to
        listen for `asyncio.Event` instances being set.
        """
        try:
            await coro()
        except (WLANConnectionError, NetworkModeError) as e:
            exception_cls = e.__class__.__name__
            _logger.error(f"Caught `{exception_cls}`")

            self._WLAN_MODE = network.AP_IF
            await self.transition(
                TerminalErrorState(self, exception_cls, self.reset_state)
            )
        except WLANCredentialsError as e:
            exception_cls = e.__class__.__name__
            _logger.error(f"Caught `{exception_cls}`")
            _logger.error("Check `NetworkEnv` `$WLAN_PASSWORD` value")

            self._WLAN_MODE = network.AP_IF
            await self.transition(
                TerminalErrorState(self, exception_cls, self.reset_state)
            )
        except Exception as e:
            _logger.error(f"`{e.__class__.__name__}`")
        finally:
            _logger.info("`WLANMachine.handle_exceptions` cleanup")
            _logger.info("Executing 'WLAN.disconnect` & `WLAN.deinit`")
            self.WLAN.disconnect()
            self.WLAN.deinit()
            raise SystemExit


async def main() -> None:
    """"""
    env = NetworkEnv()
    env.putenv(NetworkEnv.WLAN_SSID, "S23")
    env.putenv(NetworkEnv.WLAN_PASSWORD, "q5fgITAC")

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
