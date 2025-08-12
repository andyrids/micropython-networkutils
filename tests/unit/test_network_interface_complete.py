# pyright: reportUndefinedVariable=false
"""Complete interface unit tests module.

Tests are based around `networkutils.core` utility functions, which
are used with `networkutils.core.get_network_interface`.

Author: Andrew Ridyard.

License: GNU General Public License v3 or later.

Copyright (C): 2025.
"""

import logging
from binascii import hexlify, unhexlify

import pytest
from pytest_mock import MockerFixture
from rich.pretty import pprint
from unittest.mock import MagicMock


def test_device_id(
    mocker: MockerFixture,
    mock_machine_module: MagicMock,
    mock_network_module: MagicMock,
) -> None:
    """"""
    mock_id = unhexlify("E66164084373532B")
    mock_machine_module.unique_id.return_value = mock_id
    from networkutils.core import _DEVICE_ID

    assert hexlify(mock_id).decode().upper() == _DEVICE_ID
    mock_machine_module.unique_id.assert_called_once()


def test_connection_issue(
    mocker: MockerFixture, mock_network_module: MagicMock
) -> None:
    """Test connection_issue function."""
    from networkutils import connection_issue

    mock_wlan = mock_network_module.WLAN.return_value
    mock_wlan.IF_AP = 1
    mock_wlan.IF_STA = 0

    # scenario 1: AP mode
    mock_wlan.isconnected.return_value = True  # doesn't matter for AP mode
    assert connection_issue(mock_wlan, mock_network_module.AP_IF) is True
    mock_wlan.isconnected.assert_not_called()

    # scenario 2: STA mode & connected
    mock_wlan.reset_mock()
    mock_wlan.isconnected.return_value = True
    assert connection_issue(mock_wlan, mock_network_module.STA_IF) is False
    mock_wlan.isconnected.assert_called_once()

    # scenario 3: STA mode & not connected
    mock_wlan.reset_mock()
    mock_wlan.isconnected.return_value = False
    assert connection_issue(mock_wlan, mock_network_module.STA_IF) is True
    mock_wlan.isconnected.assert_called_once()


@pytest.mark.asyncio
async def test_activate_interface_becomes_active(
    mocker: MockerFixture,
    mock_asyncio_module: MagicMock,
    mock_network_module: MagicMock,
    mock_wlan_instance: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test activate_interface when wlan.active() becomes True (AP mode)."""
    from networkutils import activate_interface

    # a non-GOT_IP status
    mock_wlan_instance.status.return_value = mock_network_module.STAT_IDLE
    mock_wlan_instance.active.side_effect = (None, False, True)

    with caplog.at_level(logging.DEBUG, logger="networkutils.core"):
        await activate_interface(mock_wlan_instance)

    assert mock_wlan_instance.active.call_count >= 3
    assert caplog.text
    assert mock_asyncio_module.sleep.call_count == 1


@pytest.mark.asyncio
async def test_activate_interface_timeout(
    mocker: MockerFixture,
    mock_asyncio_module: MagicMock,
    mock_network_module: MagicMock,
    mock_wlan_instance: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test activate_interface timeout scenario."""
    from networkutils import activate_interface

    mock_wlan_instance.status.return_value = mock_network_module.STAT_IDLE
    mock_wlan_instance.active.return_value = False

    with caplog.at_level(logging.DEBUG, logger="networkutils.core"):
        await activate_interface(mock_wlan_instance)

    mock_wlan_instance.active.assert_any_call(True)
    assert mock_asyncio_module.sleep.call_count == 5
    assert caplog.text


@pytest.mark.asyncio
async def test_deactivate_interface_becomes_inactive(
    mock_asyncio_module: MagicMock,
    mock_network_module: MagicMock,
    mock_wlan_instance: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test deactivate_interface when wlan.active() becomes False."""
    from networkutils import deactivate_interface

    mock_wlan_instance.active.side_effect = (None, True, False)

    with caplog.at_level(logging.DEBUG, logger="networkutils.core"):
        await deactivate_interface(mock_wlan_instance)

    assert mock_wlan_instance.active.call_count >= 3
    assert caplog.text
    assert mock_asyncio_module.sleep.call_count == 1


@pytest.mark.asyncio
async def test_deactivate_interface_timeout(
    mocker: MockerFixture,
    mock_asyncio_module: MagicMock,
    mock_wlan_instance: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test deactivate_interface timeout scenario."""
    from networkutils import deactivate_interface

    side_effects = (None, True, True, True, True, True)
    mock_wlan_instance.active.side_effect = side_effects

    with caplog.at_level(logging.DEBUG, logger="networkutils.core"):
        await deactivate_interface(mock_wlan_instance)

    mock_wlan_instance.active.assert_any_call(False)
    assert mock_asyncio_module.sleep.call_count == 5
    assert caplog.text


@pytest.mark.asyncio
async def test_connect_interface_success(
    mocker: MockerFixture,
    network_env_instance: "NetworkEnv",
    mock_wlan_instance: MagicMock,
    mock_network_module: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test connect_interface successful connection."""
    from networkutils import connect_interface

    SSID = "SSID"
    PASSWORD = "PASSWORD"
    network_env_instance.putenv("WLAN_SSID", SSID)
    network_env_instance.putenv("WLAN_PASSWORD", PASSWORD)

    mock_wlan_instance.status.side_effect = (
        mock_network_module.STAT_CONNECTING,
        mock_network_module.STAT_CONNECTING,
        mock_network_module.STAT_GOT_IP,
    )

    with caplog.at_level(logging.DEBUG, logger="networkutils.core"):
        await connect_interface(mock_wlan_instance)

    mock_wlan_instance.connect.assert_called_once_with(SSID, PASSWORD)
    assert str(mock_network_module.STAT_CONNECTING) in caplog.text
    assert str(mock_network_module.STAT_GOT_IP) in caplog.text


@pytest.mark.asyncio
async def test_connect_interface_ssid_not_set(
    network_env_instance: "NetworkEnv",  # type: ignore
    mock_wlan_instance: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test connect_interface when WLAN_SSID is not set."""
    from networkutils.core import connect_interface, WLANConnectionError

    network_env_instance._env.pop("WLAN_SSID", None)

    with caplog.at_level(logging.DEBUG, logger="networkutils.core"):
        with pytest.raises(WLANConnectionError):
            await connect_interface(mock_wlan_instance)


@pytest.mark.asyncio
async def test_connect_interface_ssid_not_found_in_scan(
    network_env_instance: "NetworkEnv",
    mock_wlan_instance: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test `scan_networks` where `WLAN_SSID` is not available."""
    from networkutils import scan_networks

    SSID = "SSID"
    network_env_instance.putenv("WLAN_SSID", SSID)

    mock_wlan_instance.scan.return_value = [
        (bytes("WRONG_SSID", encoding="utf-8"), b"", 1, 0, 0)
    ]

    with caplog.at_level(logging.ERROR, logger="networkutils.core"):
        assert await scan_networks(mock_wlan_instance) is False

    assert SSID in caplog.text


@pytest.mark.asyncio
async def test_connect_interface_os_error(
    network_env_instance: "NetworkEnv",
    mock_asyncio_module: MagicMock,
    mock_wlan_instance: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test connect_interface when wlan.connect() raises OSError."""
    from networkutils.core import connect_interface, WLANConnectionError

    SSID = "SSID"
    PASSWORD = "PASSWORD"
    network_env_instance.putenv("WLAN_SSID", SSID)
    network_env_instance.putenv("WLAN_PASSWORD", PASSWORD)

    mock_wlan_instance.scan.return_value = [
        (bytes(SSID, encoding="utf-8"), b"", 1, 0, 0)
    ]

    mock_wlan_instance.connect.side_effect = OSError("")

    with caplog.at_level(logging.ERROR, logger="networkutils.core"):
        with pytest.raises(WLANConnectionError):
            await connect_interface(mock_wlan_instance)

    _, log_level, message = next(iter(caplog.record_tuples))
    assert SSID in message and log_level == logging.ERROR


@pytest.mark.asyncio
async def test_connect_interface_timeout(
    network_env_instance: "NetworkEnv",
    mock_asyncio_module: MagicMock,
    mock_wlan_instance: MagicMock,
    mock_time_module: MagicMock,
    mock_network_module: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test connect_interface timeout during connection wait."""
    from networkutils.core import connect_interface, WLANTimeoutError

    SSID = "SSID"
    PASSWORD = "PASSWORD"
    network_env_instance.putenv("WLAN_SSID", SSID)
    network_env_instance.putenv("WLAN_PASSWORD", PASSWORD)

    mock_wlan_instance.scan.return_value = [
        (bytes(SSID, encoding="utf-8"), b"", 1, 0, 0)
    ]

    mock_wlan_instance.status.return_value = mock_network_module.STAT_CONNECTING
    mock_wlan_instance.isconnected.return_value = False

    # simulate exceeding 30s timeout loop
    mock_time_module.time.side_effect = range(31)

    with caplog.at_level(logging.ERROR, logger="networkutils.core"):
        with pytest.raises(WLANTimeoutError):
            await connect_interface(mock_wlan_instance)

    assert mock_asyncio_module.sleep.call_count == 30

    _, log_level, message = next(iter(caplog.record_tuples))
    assert SSID in message and log_level == logging.ERROR


@pytest.mark.asyncio
async def test_access_point_reset_env_vars_set(
    mocker: MockerFixture,
    network_env_instance: "NetworkEnv",
    mock_asyncio_module: MagicMock,
    mock_network_module: MagicMock,
    mock_wlan_instance: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test `access_point_reset` when $AP_SSID & $AP_PASSWORD are set."""
    from networkutils import access_point_reset

    # mock helper functions called by access_point_reset
    mock_deactivate = mocker.patch("networkutils.core.deactivate_interface")
    mock_activate = mocker.patch("networkutils.core.activate_interface")

    SSID = "SSID"
    PASS = "PASSWORD"
    network_env_instance.putenv("AP_SSID", SSID)
    network_env_instance.putenv("AP_PASSWORD", PASS)

    # 1. `mock_wlan_instance` is passed initially to `access_point_reset`
    # 2. `access_point_reset` calls `network.WLAN`, creating a new instance
    new_mock_wlan = MagicMock(name="New_WLAN_Instance")
    mock_network_module.WLAN.return_value = new_mock_wlan

    with caplog.at_level(logging.DEBUG, logger="networkutils.core"):
        reset_wlan, reset_wlan_mode = await access_point_reset(
            mock_wlan_instance
        )

    # 1. `WLAN.disconnect` 2. `deactivate_interface` 3. `WLAN.deinit`
    mock_wlan_instance.disconnect.assert_called_once()
    mock_deactivate.assert_called_once_with(mock_wlan_instance)
    mock_wlan_instance.deinit.assert_called_once()

    # create a new WLAN instance in AP mode
    mock_network_module.WLAN.assert_called_once_with(mock_network_module.AP_IF)
    assert network_env_instance.getenv("AP_SSID") == SSID

    new_mock_wlan.config.assert_called_once_with(ssid=SSID, password=PASS)
    mock_activate.assert_called_once_with(new_mock_wlan)

    assert reset_wlan is new_mock_wlan
    assert reset_wlan_mode == mock_network_module.AP_IF


@pytest.mark.asyncio
async def test_access_point_reset_env_vars_not_set(
    mocker: MockerFixture,
    network_env_instance: "NetworkEnv",
    mock_asyncio_module: MagicMock,
    mock_network_module: MagicMock,
    mock_wlan_instance: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test `access_point_reset` with default AP SSID & password."""
    from networkutils.core import access_point_reset, _DEVICE_ID

    mock_deactivate = mocker.patch("networkutils.core.deactivate_interface")
    mock_activate = mocker.patch("networkutils.core.activate_interface")

    # reset $AP_SSID & $AP_PASSWORD in env
    network_env_instance._env.pop("AP_SSID", None)
    network_env_instance._env.pop("AP_PASSWORD", None)

    new_mock_wlan = MagicMock(name="New_WLAN_Instance_Default")
    mock_network_module.WLAN.return_value = new_mock_wlan

    # `_DEVICE_ID` is 'E661084373532B' (`conftest.mock_machine_module`)
    SSID = f"DEVICE-{_DEVICE_ID}"
    PASS = _DEVICE_ID

    with caplog.at_level(logging.DEBUG, logger="networkutils.core"):
        reset_wlan, reset_wlan_mode = await access_point_reset(
            mock_wlan_instance
        )

    mock_network_module.WLAN.assert_called_once_with(mock_network_module.AP_IF)

    assert network_env_instance.getenv("AP_SSID") == SSID
    assert network_env_instance.getenv("AP_PASSWORD") == PASS

    new_mock_wlan.config.assert_called_once_with(ssid=SSID, password=PASS)
    mock_activate.assert_called_once_with(new_mock_wlan)

    assert reset_wlan is new_mock_wlan
    assert reset_wlan_mode == mock_network_module.AP_IF
    assert caplog.text
