# Contribution Guidelines

Contributions are welcome.

## Cloning The Repository

This repository is managed by Astral [`uv`](https://docs.astral.sh/uv/) Python package manager and can be installed by cloning the repository and syncing with uv.

```sh
git clone git@gitlab.com:micropython-iot-projects/libraries/micropython-network-utils.git
cd micropython-network-utils
uv sync
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
