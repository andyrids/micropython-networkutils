# Testing

Testing instructions and guidance are listed here. All unit tests are written using the MicroPython version of [`unittest`](https://github.com/micropython/micropython-lib/tree/master/python-stdlib/unittest).

```mermaid
sequenceDiagram
    participant PT as PyTest Tests
    participant MT as mpremote Transport
    participant MP as MicroPython Device
    participant PF as Package Functions

    PT->>MT: Initialize transport
    activate MT
    MT->>MP: Establish serial connection
    activate MP
    
    rect black
        Note over PT,PF: Integration Test Boundary
        PT->>MT: Execute test case
        MT->>MP: Send test commands
        MP->>PF: Import package functions
        PF-->>MP: Execute function
        MP-->>MT: Return results
        MT-->>PT: Process test output
    end

    PT->>MT: Cleanup
    MT->>MP: Close connection
    deactivate MP
    deactivate MT
```

## Cloning The Repository

This repository is managed by Astral [`uv`](https://docs.astral.sh/uv/) Python package manager and can be installed by cloning the repository and syncing with uv.

```sh
git clone git@gitlab.com:micropython-iot-projects/libraries/micropython-network-utils.git
cd micropython-network-utils
uv sync
```

## Activate Virtual Environment

Activate the virtual environment:

```sh
. .venv/bin/activate
```

## Running Unit Tests

Unit test files are found within `tests/unit` directory. These tests can be run with `pytest`, with the following command:

```sh
python -m pytest
```
