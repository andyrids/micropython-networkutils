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
    L([List /lib Directory])
    M([Import sys,<br/>print implementation name])
    N([Import network_utils])
    O([Print network_utils._DEVICE_ID])
    P([Create NetworkEnv,<br/>set WLAN_SSID & WLAN_PASSWORD])
    Q([Get & Print WLAN_SSID])
    R([Get & Print WLAN_PASSWORD])
    S([End Test])
    Z([Exit: No Devices Found])
    T([Cleanup: Exit Raw REPL if needed,<br/>Close Serial])

    A --> B
    B --> C
    C -- No --> Z
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
    Y --> L
    L --> M
    M --> N
    N --> O
    O --> P
    P --> Q
    Q --> R
    R --> S
    Z --> S
    S --> T
```

```mermaid
sequenceDiagram
    participant Tester as Integration Test Script
    participant Serial as SerialTransport (mpremote)
    participant Device as MicroPython Device
    participant Mip as mip Installer

    Tester->>Serial: Detect USB serial ports
    Serial->>Device: Connect to device
    Tester->>Serial: Enter raw REPL (no soft reset)
    Serial->>Device: Enter raw REPL
    Tester->>Serial: Print REPL status
    Serial->>Device: Query REPL status
    Serial-->>Tester: Return status

    Tester->>Mip: Install networkutils package
    Mip->>Device: Install via mpremote mip
    Device-->>Mip: Installation result
    Mip-->>Tester: Report install status

    Tester->>Serial: List [/lib](VALID_DIRECTORY) directory
    Serial->>Device: fs_listdir("lib")
    Device-->>Serial: Directory contents
    Serial-->>Tester: Return contents

    Tester->>Serial: Import and test network_utils
    Serial->>Device: exec("import network_utils")
    Device-->>Serial: Import result

    Tester->>Serial: Print network_utils._DEVICE_ID
    Serial->>Device: exec("print(network_utils._DEVICE_ID)")
    Device-->>Serial: Return device ID
    Serial-->>Tester: Return device ID

    Tester->>Serial: Set WLAN_SSID and WLAN_PASSWORD
    Serial->>Device: exec("env.putenv(...)")
    Device-->>Serial: Set result

    Tester->>Serial: Get and print WLAN_SSID
    Serial->>Device: exec("print(env.getenv('WLAN_SSID'))")
    Device-->>Serial: Return SSID
    Serial-->>Tester: Return SSID

    Tester->>Serial: Get and print WLAN_PASSWORD
    Serial->>Device: exec("print(env.getenv('WLAN_PASSWORD'))")
    Device-->>Serial: Return password
    Serial-->>Tester: Return password

    Tester->>Serial: Cleanup and close connection
    Serial->>Device: Exit raw REPL, close
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
