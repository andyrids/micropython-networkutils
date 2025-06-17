# Testing

Testing instructions and guidance are listed here. All unit tests are written using the [pytest](https://docs.pytest.org/en/stable/index.html) library.

## Cloning The Repository

This repository is managed by Astral [`uv`](https://docs.astral.sh/uv/) Python package manager and can be installed by cloning the repository and syncing with uv.

```sh
git clone git@gitlab.com:micropython-iot-projects/libraries/micropython-networkutils.git
cd micropython-networkutils
uv sync --all-extras
```

## Activate Virtual Environment

Activate the virtual environment:

```sh
. .venv/bin/activate
```

## Test Layout

```text
...
├── tests                                      <-- Main test directory
│   ├── integration                            <-- Integration tests
│   │   ├── __init__.py
│   │   └── main.py                            <-- WIP for integration tests
│   ├── unit                                   <-- Unit tests
│   │   ├── __init__.py
│   │   ├── test_network_config.py             <-- Network configuration tests
│   │   ├── test_network_interface_complete.py <-- Complete interface tests
│   │   └── test_network_interface_complex.py  <-- Complex interface unit tests
│   ├── __init__.py
│   └── conftest.py                            <-- Fixtures & mocks for MicroPython modules
```

## Unit Testing

The unit test functions can be run with the following command:

```sh
pytest --cov=networkutils/networkutils -v
```

## Integration Testing

> [!IMPORTANT]
> Integration tests (`tests/integration`) are a WIP.

Having experimented with `mpremote`, I have found a way to install the `networkutils` package and connect to a microcontroller in a script context, rather than through the CLI. Through a programmatic connection to the REPL, it is possible to send commands that utilise and test the package on the device, returning any output as a string for assertions within pytest functions.

```mermaid
flowchart TD
    A([Start Integration Test])
    B([Detect USB Serial Ports])
    C{Found Device?}
    D([Connect to Serial Device])
    E{In Raw REPL?}
    F([Exit Raw REPL])
    G([Enter Raw REPL])
    H([Wait 1s])
    I([Print REPL Status])
    J([Install networkutils via mip])
    K{Install Success?}
    Y([Log: Installation Failed])
    L([Run Command])
    M([Test Output])
    N([End Test])
    O([Exit: No Devices Found])
    P([Cleanup: Exit Raw REPL if needed,<br/>Close Serial])

    A --> B
    B --> C
    C -- No --> O
    C -- Yes --> D
    D --> E
    E -- Yes --> F
    E -- No --> G
    F --> G
    G --> H
    H --> I
    I --> J
    J --> K
    K -- No --> Y
    K -- Yes --> L
    Y --> O
    L --> M
    M --> N
    N --> P
    O --> P
```
