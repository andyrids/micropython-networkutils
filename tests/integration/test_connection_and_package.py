# pyright: reportAttributeAccessIssue=false
"""Complete integration test module.

Tests use `mpremote` to connect to a device and conduct the tests. The
`serial_connection` fixture ensures all integration tests use the same
`SerialTransport` instance, which is used to connect to the device and
send commands over the raw REPL.

1. `serial_connection` fixture yields a `SerialTransport` instance.

2. Test serial connection is open and a raw REPL connection can be made.

3. Test package installation using `mpremote`.

4. Test package can be imported correctly.

5. Integration test for `networkutils.core.NetworkEnv`.

Author: Andrew Ridyard.

License: GNU General Public License v3 or later.

Copyright (C): 2025."""
import logging
import time
from ast import literal_eval
from typing import Generator

import pytest
from mpremote import mip
from mpremote.commands import CommandError
from mpremote.transport import TransportError
from mpremote.transport_serial import SerialTransport
from rich.console import Console
from rich.logging import RichHandler
from serial.tools import list_ports


_console = Console()
_rich_handler = RichHandler(console=_console, rich_tracebacks=True)
_logger = logging.getLogger("integration")
_logger.handlers.clear()
_logger.setLevel(logging.DEBUG)
_logger.addHandler(_rich_handler)


@pytest.fixture(scope="module")
def serial_connection() -> Generator[SerialTransport]:
    """Yields a `SerialTransport` instance to integration tests.
    
    If connection fails, any tests consuming the fixture are skipped.
    After test completion, finally statement runs connection teardown
    and cleanup.
    """
    serial_transport = None
    try:
        # 1. auto-detect & connect to each available USB serial port
        for p in sorted(list_ports.comports()):
            if p.vid and p.pid:
                try:
                    serial_transport = SerialTransport(p.device, 115200)
                except TransportError as e:
                    e.add_note(f"PID: {p.pid} | VID: {p.vid}")
                    _console.print_exception()
                else:
                    break
        assert serial_transport is not None
        assert serial_transport.serial.is_open
        yield serial_transport
    finally:
        _console.print("Fixture `serial_connection`: cleanup & teardown")
        if serial_transport:
            if serial_transport.in_raw_repl:
                serial_transport.exit_raw_repl()
            serial_transport.close()
            assert serial_transport.in_raw_repl is False
            assert serial_transport.serial.is_open is False


def test_enter_raw_repl(serial_connection: SerialTransport) -> None:
    """"""
    assert serial_connection.serial.is_open
    serial_connection.enter_raw_repl(soft_reset=False)
    time.sleep(1)
    assert serial_connection.in_raw_repl


def test_package_installation(
        serial_connection: SerialTransport,
        caplog: pytest.LogCaptureFixture
    ) -> None:
    """"""
    assert serial_connection.serial.is_open
    assert serial_connection.in_raw_repl

    with caplog.at_level(logging.DEBUG, logger="integration"):
        try:
            mip._install_package(
                serial_connection,
                "github:andyrids/micropython-networkutils/networkutils/",
                "https://micropython.org/pi/v2",
                "lib",
                "main",
                True
            )
        except CommandError as e:
            e.add_note("`networkutils` installation failed")
            raise

        assert serial_connection.fs_isdir("lib/networkutils")
        assert serial_connection.fs_exists("lib/networkutils/core.py")


def test_package_import(
        serial_connection: SerialTransport,
        caplog: pytest.LogCaptureFixture
    ) -> None:
    """"""
    assert serial_connection.serial.is_open
    assert serial_connection.in_raw_repl

    with caplog.at_level(logging.DEBUG, logger="integration"):
        serial_connection.exec("from networkutils.core import _DEVICE_ID")
        serial_connection.exec("from networkutils.core import NetworkEnv")
    
def test_network_config(
        serial_connection: SerialTransport,
        caplog: pytest.LogCaptureFixture
    ) -> None:
    """"""
    assert serial_connection.serial.is_open
    assert serial_connection.in_raw_repl

    with caplog.at_level(logging.DEBUG, logger="integration"):
        ENV = {"WLAN_PASSWORD": "PASSWORD", "WLAN_SSID": "SSID"}
        serial_connection.exec("env = NetworkEnv();")
        for k,v in ENV.items():
            serial_connection.exec(f"env.putenv('{k}', '{v}')")

        out = serial_connection.exec("print(repr(env._env))")
        assert literal_eval(out.decode().strip()) == ENV
