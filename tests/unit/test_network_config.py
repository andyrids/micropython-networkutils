from binascii import unhexlify
from typing import Callable
import pytest
from pytest_mock import MockerFixture
# import network_utils

@pytest.fixture(autouse=True)
def patch_micropython_modules(mocker: MockerFixture):
    # patch network.WLAN and network constants
    mocker.patch.dict('sys.modules', {
        "network_utils.network": mocker.MagicMock(),
        "network_utils.machine": mocker.MagicMock(),
        "network": mocker.MagicMock(),
        "machine": mocker.MagicMock(),
    })

    mocker.patch("machine.unique_id", return_value=unhexlify("E66164084373532B"))


def test_networkenv_singleton(patch_micropython_modules: Callable):
    """Test NetworkEnv singleton."""
    from network_utils import NetworkEnv
    assert NetworkEnv() is NetworkEnv()


def test_networkenv_getenv_putenv(patch_micropython_modules: Callable):
    """Test getting & setting network environment variables."""
    from network_utils import NetworkEnv
    env = NetworkEnv()
    env.putenv("FOO", "BAR")
    assert env.getenv("FOO") == "BAR"
    assert env.getenv("NOT_SET") is None
