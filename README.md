# MicroPython Package Repository - `network-utils`

NOTE: **WIP**

This is a repository for a MicroPython package named `network-utils`, which contains utility functions related to interfaces exposed by the [`network`](https://docs.micropython.org/en/latest/library/network.html#module-network) standard library and external packages on the [`micropython-lib`](https://github.com/micropython/micropython-lib) repository.

* `typing`: [micropython-stubs](https://raw.githubusercontent.com/Josverl/micropython-stubs/refs/heads/main/mip/typing.py)
* `typing_extensions`: [micropython-stubs](https://raw.githubusercontent.com/Josverl/micropython-stubs/refs/heads/main/mip/typing_extensions.py)

This package follows the ***extension package*** concept outlined in the [micropython-lib](https://github.com/micropython/micropython-lib) repository. Extension packages will extend the functionality of the `network-utils` package, by adding additional files to the same package directory. These packages will follow the naming convention `network-utils-*` and will install extra modules to a directory named `network_utils` on the device

e.g. `network-utils` would install `__init__.py` file on the device as `lib/network_utils/__init__.py` and the `network-utils-mqtt` extension package would install `mqtt.py` as `lib/network_utils/mqtt.py`.

Installation of `network-utils` will only install files that are part of the `network-utils` package whereas installation of `network-utils-mqtt` will install the package extension files along with the `network-utils` package it extends.

```text
micropython-network-utils
├── network-utils          <-- network-utils package
│   ├── manifest.py
│   ├── network_utils      <-- device installation dir i.e. `lib/network_utils/__init__.py`
│   │   └── __init__.py
│   └── package.json       <-- package URLs & dependencies 
├── network-utils-mqtt     <-- Extension package for network-utils
│   ├── manifest.py
│   ├── network_utils      <-- device installation dir i.e. i.e. `lib/network_utils/mqtt.py`
│   │   └── mqtt.py
│   ├── package.json       <-- extension package URLs & dependencies (includes network-utils)
│   └── test_wlan.py
```

## Cloning The Repository

This repository is managed by Astral [`uv`](https://docs.astral.sh/uv/) Python package manager and can be installed by cloning the repository and syncing with uv.

```sh
git clone git@gitlab.com:micropython-iot-projects/libraries/micropython-network-utils.git
cd micropython-network-utils
uv sync
```

## MicroPython Package Installation

The following commands will install the `network-utils` package based on the URLs and dependencies listed in the `network-utils/package.json`.

### REPL

The following code will import `mip` and install the `network-utils` package from the REPL.

```python
>>> import mip
>>> mip.install("gitlab:micropython-iot-projects/libraries/micropython-network-utils/network-utils", version="main")
```

### mpremote

The following commands will install the `network-utils` package on your device using `mpremote` Python package.

```sh
mpremote mip install gitlab:micropython-iot-projects/libraries/micropython-network-utils/network-utils@main
```
