# pyright: reportUndefinedVariable=false
"""Network configuration tests using `networkutils.NetworkEnv`.

Author: Andrew Ridyard.

License: GNU General Public License v3 or later.

Copyright (C): 2025.
"""

import pytest
from pytest_mock import MockerFixture
from unittest.mock import MagicMock


def test_networkenv_singleton() -> None:
    """Test `NetworkEnv` is a singleton."""
    from networkutils import NetworkEnv

    NetworkEnv._instance = None
    NetworkEnv._env = {}
    assert NetworkEnv() is NetworkEnv()


def test_networkenv_getenv_putenv(
    mocker: MockerFixture, network_env_instance: "NetworkEnv"
) -> None:
    """Test getting & setting network environment variables."""
    from networkutils import NetworkEnv

    env = network_env_instance

    env.putenv("FOO", "BAR")
    assert env.getenv("FOO") == "BAR"
    assert env.getenv("NOT_SET") is None

    env.putenv("TEST_INT", 123)
    assert env.getenv("TEST_INT") == "123"

    env.putenv("TEST_FLOAT", 45.6)
    assert env.getenv("TEST_FLOAT") == "45.6"

    env.putenv("EMPTY_STR", "")
    assert env.getenv("EMPTY_STR") is None
