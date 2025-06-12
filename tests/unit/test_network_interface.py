from binascii import hexlify, unhexlify
import pytest
from pytest_mock import MockerFixture
from unittest.mock import MagicMock


def test_device_id(
        mocker: MockerFixture,
        mock_machine_module: MagicMock,
        mock_network_module: MagicMock
    ) -> None:
    """"""
    mock_id = unhexlify("E66164084373532B")
    mock_machine_module.unique_id.return_value = mock_id
    from network_utils.interface import _DEVICE_ID

    assert hexlify(mock_id).decode().upper() == _DEVICE_ID
    mock_machine_module.unique_id.assert_called_once()