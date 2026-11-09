# Contributing Guide

## Development

```sh
uv venv --python 3.13
uv pip install -e ".[dev]"
uv run pre-commit install
```

Run the checks:

```sh
uv run ruff format houdini_mcp tests
uv run ruff check --select I --fix houdini_mcp tests
uv run ruff check houdini_mcp tests
uv run ty check
uv run pytest
```

### Releasing Changes

```sh
uv run semantic-release version
```
