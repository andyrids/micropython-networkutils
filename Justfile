set dotenv-load := true

# ENVIRONMENT VARIABLES (`.env` or default)
# ====================================================

PORT := env("PORT", "8080")


[default]
@_:
    just --list

# ENVIRONMENT
# ====================================================

[doc("Install MicroPython stubs into `typings/` folder")]
[group("ENV")]
@stubs:
    uv export --only-group dev --no-hashes --no-emit-project | \
      grep "micropython" | \
      uv pip install --target typings --requirements -

[doc("Update project environment")]
[group("ENV")]
sync: stubs
    uv sync

[doc("Upgrade dependencies")]
[group("ENV")]
@upgrade:
    uv lock --upgrade

[doc("Clean project environment")]
[group("ENV")]
clean:
    rm -rf \
      .venv .pytest_cache \
      .mpy_cache .ruff_cache \
      .coverage htmlcov
    find . \
      -type d \
      -name "__pycache__" \
      -exec rm -r {} +

[doc("Clean & update project environment")]
[group("ENV")]
resync: clean sync

# DEV & QA
# ====================================================

[doc("Open browser @ `http://localhost:$PORT`")]
[group("DEV")]
@browser:
    uv run -m webbrowser -t http://127.0.0.1:{{ PORT }}

[doc("Git prune all unreachable objects immediately")]
[group("QA")]
@git-prune:
    git gc --prune=now

[doc("Check static typing")]
[group("QA")]
@static-typing:
    uv run mypy src tests

[doc("Install `prek` Git shims")]
[group("QA")]
@prek-install:
    uv run -m prek install

[doc("Prepare `prek` hook environments")]
[group("QA")]
@prek-install-prepare:
    uv run -m prek install --prepare-hooks

[doc("List `prek` Git hooks")]
[group("QA")]
@prek-list:
    uv run -m prek list

[doc("Update `prek` pinned hook repository revisions")]
[group("QA")]
@prek-update:
    uv run -m prek auto-update

_coverage *args:
    uv run -m coverage {{ args }}

[doc("Generate test coverage")]
[group("QA")]
@coverage:
    just _coverage erase
    just _coverage run -m pytest
    just _coverage combine
    just _coverage report
    just _coverage html

[doc("Format & lint")]
[group("QA")]
@format-lint:
    - uv run -m ruff format .
    - uv run -m ruff check --fix