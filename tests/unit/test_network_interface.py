import logging
from binascii import hexlify, unhexlify

import pytest
from pytest_mock import MockerFixture
from rich.pretty import pprint
from unittest.mock import MagicMock, call


def test_device_id(
        mocker: MockerFixture,
        mock_machine_module: MagicMock,
        mock_network_module: MagicMock
    ) -> None:
    """"""
    mock_id = unhexlify("E66164084373532B")
    mock_machine_module.unique_id.return_value = mock_id
    from networkutils.core import _DEVICE_ID

    assert hexlify(mock_id).decode().upper() == _DEVICE_ID
    mock_machine_module.unique_id.assert_called_once()


def test_connection_issue(mocker: MockerFixture, mock_network_module: MagicMock) -> None:
    """Test connection_issue function."""
    from networkutils.core import connection_issue
    mock_wlan = mock_network_module.WLAN.return_value
    mock_wlan.IF_AP = 1
    mock_wlan.IF_STA = 0

    # Scenario 1: AP mode
    mock_wlan.isconnected.return_value = True # Doesn't matter for AP mode
    assert connection_issue(mock_wlan, mock_network_module.AP_IF) is True
    mock_wlan.isconnected.assert_not_called()

    # Scenario 2: STA mode & connected
    mock_wlan.reset_mock()
    mock_wlan.isconnected.return_value = True
    assert connection_issue(mock_wlan, mock_network_module.STA_IF) is False
    mock_wlan.isconnected.assert_called_once()

    # Scenario 3: STA mode & not connected
    mock_wlan.reset_mock()
    mock_wlan.isconnected.return_value = False
    assert connection_issue(mock_wlan, mock_network_module.STA_IF) is True
    mock_wlan.isconnected.assert_called_once()


def test_activate_interface_becomes_active(
        mocker: MockerFixture,
        mock_network_module: MagicMock,
        mock_wlan_instance: MagicMock,
        mock_time_module: MagicMock,
        caplog: pytest.LogCaptureFixture) -> None:
    """Test activate_interface when wlan.active() becomes True (AP mode)."""
    from networkutils.core import activate_interface

    # a non-GOT_IP status
    mock_wlan_instance.status.return_value = mock_network_module.STAT_IDLE
    mock_wlan_instance.active.side_effect = (None, False, True)

    with caplog.at_level(logging.DEBUG, logger="networkutils.core"):
        activate_interface(mock_wlan_instance)

    assert mock_wlan_instance.active.call_count >= 3
    assert caplog.text
    assert mock_time_module.sleep.call_count == 1


def test_activate_interface_timeout(
        mocker: MockerFixture,
        mock_network_module: MagicMock,
        mock_wlan_instance: MagicMock,
        mock_time_module: MagicMock,
        caplog: pytest.LogCaptureFixture
    ) -> None:
    """Test activate_interface timeout scenario."""
    from networkutils.core import activate_interface
    mock_wlan_instance.status.return_value = mock_network_module.STAT_IDLE
    mock_wlan_instance.active.return_value = False

    with caplog.at_level(logging.DEBUG, logger="networkutils.core"):
        activate_interface(mock_wlan_instance)

    mock_wlan_instance.active.assert_any_call(True)
    assert mock_time_module.sleep.call_count == 5
    assert caplog.text


def test_deactivate_interface_becomes_inactive(
        mock_network_module: MagicMock,
        mock_wlan_instance: MagicMock,
        mock_time_module: MagicMock,
        caplog: pytest.LogCaptureFixture
    ) -> None:
    """Test deactivate_interface when wlan.active() becomes False."""
    from networkutils.core import deactivate_interface
    mock_wlan_instance.active.side_effect = (None, True, False)

    with caplog.at_level(logging.DEBUG, logger="networkutils.core"):
        deactivate_interface(mock_wlan_instance)

    assert mock_wlan_instance.active.call_count >= 3
    assert caplog.text
    assert mock_time_module.sleep.call_count == 1


def test_deactivate_interface_timeout(mocker: MockerFixture, mock_wlan_instance, mock_time_module, caplog):
    """Test deactivate_interface timeout scenario."""
    from networkutils.core import deactivate_interface

    side_effects = (None, True, True, True, True, True)
    mock_wlan_instance.active.side_effect = side_effects

    with caplog.at_level(logging.DEBUG, logger="networkutils.core"):
        deactivate_interface(mock_wlan_instance)

    mock_wlan_instance.active.assert_any_call(False)
    assert mock_time_module.sleep.call_count == 5
    assert caplog.text


def test_connect_interface_success(
    mocker: MockerFixture,
    network_env_instance: "NetworkEnv", # type: ignore
    mock_wlan_instance: MagicMock,
    mock_time_module: MagicMock,
    mock_network_module: MagicMock,
    caplog: pytest.LogCaptureFixture
):
    """Test connect_interface successful connection."""
    from networkutils.core import connect_interface

    SSID = "SSID"
    PASSWORD = "PASSWORD"
    network_env_instance.putenv("WLAN_SSID", SSID)
    network_env_instance.putenv("WLAN_PASSWORD", PASSWORD)

    mock_wlan_instance.scan.return_value = [(bytes(SSID,encoding="utf-8"), b"", 1, 0, 0)]

    mock_wlan_instance.status.side_effect = (
        mock_network_module.STAT_CONNECTING,
        mock_network_module.STAT_CONNECTING,
        mock_network_module.STAT_CONNECTING,
        mock_network_module.STAT_GOT_IP,
    )

    mock_wlan_instance.isconnected.side_effect = (False, False, True)

    with caplog.at_level(logging.DEBUG, logger="networkutils.core"):
        connect_interface(mock_wlan_instance)

    mock_wlan_instance.scan.assert_called_once()
    mock_wlan_instance.connect.assert_called_once_with(SSID, PASSWORD)
    assert str(mock_network_module.STAT_CONNECTING) in caplog.text
    assert str(mock_network_module.STAT_GOT_IP) in caplog.text


def test_connect_interface_ssid_not_set(
        network_env_instance: "NetworkEnv", # type: ignore
        mock_wlan_instance: MagicMock,
        caplog: pytest.LogCaptureFixture
    ) -> None:
    """Test connect_interface when WLAN_SSID is not set."""
    from networkutils.core import connect_interface, WLANConnectionError

    network_env_instance._env.pop("WLAN_SSID", None)

    with caplog.at_level(logging.DEBUG, logger="networkutils.core"):
        with pytest.raises(WLANConnectionError):
            connect_interface(mock_wlan_instance)
