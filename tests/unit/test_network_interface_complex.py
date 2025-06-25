# pyright: reportUndefinedVariable=false
"""Complex interface unit tests module.

Tests are based around `networkutils.core.get_network_interface`, which
utilises all other interface & helper functions within `networkutils.core`.

Author: Andrew Ridyard.

License: GNU General Public License v3 or later.

Copyright (C): 2025.
"""

import logging
from binascii import hexlify, unhexlify

import pytest
from pytest_mock import MockerFixture
from rich.pretty import pprint
from unittest.mock import AsyncMock, MagicMock, NonCallableMagicMock


@pytest.fixture
def mock_interface_helpers(
    mocker: MockerFixture,
) -> dict[str, MagicMock | AsyncMock | NonCallableMagicMock]:
    """Mock helper functions within the interface module."""

    activate_interface = mocker.patch("networkutils.core.activate_interface")
    connect_interface = mocker.patch("networkutils.core.connect_interface")
    access_point_reset = mocker.patch("networkutils.core.access_point_reset")

    return {
        "activate_interface": activate_interface,
        "connect_interface": connect_interface,
        "access_point_reset": access_point_reset,
    }


def test_get_network_interface_debug_mode(
    mocker: MockerFixture,
    network_env_instance: "NetworkEnv",
    mock_network_module: MagicMock,
    mock_interface_helpers: dict[
        str, MagicMock | AsyncMock | NonCallableMagicMock
    ],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test get_network_interface with debug=True sets logger level."""
    from networkutils.core import get_network_interface, _logger

    # a `setLevel` patch to track & facilitate call assertions
    set_level = mocker.patch.object(_logger, "setLevel", autospec=True)

    # force AP mode to avoid `connect_interface` & `access_point_reset`
    network_env_instance.putenv("WLAN_SSID", None)

    # `_logger` instance from `networkutils.core` is what we need to check
    # in `conftest`, `logging.getLogger` returns `mock_logger_instance`
    with caplog.at_level(logging.DEBUG, logger="networkutils.core"):
        get_network_interface(debug=True)

    # `networkutils.core._logger` is `logging.getLogger("networkutils.core")`
    # default level is `logging.ERROR`, expecting `logging.DEBUG`
    set_level.assert_any_call(logging.DEBUG)
