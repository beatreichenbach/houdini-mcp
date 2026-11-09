# Contributing Guide

For package boundaries, runtime flow, and how to add commands, resources, prompts, and workflows, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Development

```sh
uv venv --python 3.13
uv pip install -e ".[dev]"
uv run pre-commit install
```

Run the checks:

```sh
uv run ruff format src tests houdini
uv run ruff check --select I --fix src tests houdini
uv run ruff check src tests houdini
uv run ty check
uv run pytest
```

Run live Houdini tests with:

```sh
uv run pytest -m integration
```

### Releasing Changes

```sh
uv run semantic-release version
```
