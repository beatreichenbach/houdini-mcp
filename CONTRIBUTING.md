# Contributing Guide

For package boundaries, runtime flow, and how to add commands, resources, prompts, and skills, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Development

```sh
uv venv --python 3.13
uv pip install -e ".[dev]"
uv run pre-commit install
```

Run the checks:

```sh
uv run ruff format src tests
uv run ruff check --select I --fix src tests
uv run ruff check src tests
uv run ty check
uv run pytest
```

### Releasing Changes

```sh
uv run semantic-release version
```
