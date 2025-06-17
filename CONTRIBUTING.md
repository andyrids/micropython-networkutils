# Contribution Guidelines

Contributions are welcome and these should ideally be made through the main repository on [GitLab](https://gitlab.com/micropython-iot-projects/libraries/micropython-network-utils).

## Local Development

This package facilitates MicroPython development in VSCode through the settings in `.vscode` and the [`micropython-stdlib-stubs`](https://github.com/Josverl/micropython-stubs) project dev dependency. Type hints on MicroPython code are enabled through the following files, which are included as a package dependency and installed to the device `lib/` directory:

* `typing`: [micropython-stubs](https://raw.githubusercontent.com/Josverl/micropython-stubs/refs/heads/main/mip/typing.py)
* `typing_extensions`: [micropython-stubs](https://raw.githubusercontent.com/Josverl/micropython-stubs/refs/heads/main/mip/typing_extensions.py)

In a MicroPython context, This package follows the ***extension package*** concept outlined in the [micropython-lib](https://github.com/micropython/micropython-lib) repository. Extension packages will extend the functionality of the `networkutils` package, by adding additional files to the same package directory. These packages will follow the naming convention `networkutils-*` and will install extra modules to the directory `lib/networkutils` on the device.

e.g. `networkutils` would install the `core.py` file on the device as `lib/networkutils/core.py` and the `networkutils-mqtt` extension package would install `mqtt.py` as `lib/networkutils/mqtt.py`.

Installation of `networkutils` will only install files that are part of the `networkutils` package, whereas installation of `networkutils-mqtt` will install the package extension files along with the `networkutils` package it extends.

```text
micropython-networkutils
├── networkutils           <-- Core `networkutils` package
│   ├── manifest.py
│   ├── networkutils       <-- Device installation dir i.e. `lib/networkutils/`
│   │   └── core.py        <-- Core package module
│   └── package.json       <-- Package URLs & dependencies (for `mip install`)
├── networkutils-mqtt      <-- Extension package for `networkutils`
│   ├── manifest.py
│   ├── networkutils       <-- Device installation dir i.e. `lib/networkutils/`
│   │   └── mqtt.py        <-- Extension package module
│   ├── package.json       <-- Extension package URLs & dependencies (includes core `networkutils`)
│   └── pyproject.toml     <-- Extension package `pyproject.toml` enables uv workspace & namespace package
```

In a standard Python context, this package is called `micropython-networkutils` and follows a Python [namespace](https://packaging.python.org/en/latest/guides/packaging-namespace-packages/) structure, with the shared namespace being `networkutils`. The aforementioned MicroPython ***extension packages*** in this context, are optional dependencies listed in the root `pyproject.toml.` For example, to install `networkutils` and `networkutils-mqtt`, you could pip install `micropython-networkutils[mqtt]`. This would enable imports like so:

```python
from networkutils.core import NetworkEnv
from networkutils.mqtt import CertificateNotFound
```

This namespace layout enables the local installation of the package and the use of `pytest` functions,
which can test the interface locally, in the same way it is exposed on the device.

## New Issues; Bugs & Features

### Features

Choose a suitable title and use a story format that explains the feature in depth:

```txt
As a [developer | user | system], instead of [current situation], I want [action | feature], so that [value | justification].
```

Issue description templates can help provide a useful format and context:

![issue example](./docs/img/new_feature_issue.png)

Full example:

![issue example](./docs/img/issue_example.png)

### Bugs

Use the `New Bug` description template when creating issues related to bugs:

![issue example](./docs/img/new_bug_issue.png)

## Cloning The Repository

This repository is managed by Astral [`uv`](https://docs.astral.sh/uv/) Python package manager and can be installed by cloning the repository and syncing with uv.

```sh
git clone git@gitlab.com:micropython-iot-projects/libraries/micropython-network-utils.git
cd micropython-network-utils
uv sync --all-extras
```

Activate the virtual environment created by uv:

```sh
source .venv/bin/activate
```

## Linting & Formatting

With the virtual environment activated, the `ruff` check & format commands will implement the rules set in the pyproject.toml file. These tool can be also be run using the commands `uv run ruff check` or `uv run ruff format`.

To run the ruff linting tool, use the following command:

```sh
ruff check --fix
```

To format the code in accordance with the project formatting rules, use the following command:

```sh
ruff format
```

### Commit Messages

Commit messages use the [conventional commits](https://www.conventionalcommits.org/en/v1.0.0/#summary) specification:

`<type>[optional scope]: <description>`

```sh
git commit -m "docs: update contribution guidelines."
git commit -m "chore: ruff lint & format."
git commit -m "feat: add new mqtt extension package module."
git commit -m "fix: patch an installation error for cli install command #1234."
```

A breaking change is indicated with a '!':

```sh
git commit -m "refactor!: drop support for rshell."
```
