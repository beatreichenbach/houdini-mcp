# Architecture

## Overview

The project has two runtime halves and one shared contract:

- `houdini_mcp` is the MCP server.
  The MCP client starts it outside Houdini.
- `houdini_mcp_plugin` is the HTTP receiver.
  It runs inside Houdini and executes `hou` calls on the main thread.
- `houdini_mcp_protocol` is the shared, stdlib-only contract.
  Both halves import it.

Houdini package assets live in `houdini/`.

## Runtime flow

```text
MCP client
  │ stdio
houdini_mcp
  │ HTTP on 127.0.0.1:8100
houdini_mcp_plugin
  │ hdefereval / hou
Houdini
```

## Package boundaries

| Package | Owns | Must not import |
|---|---|---|
| `houdini_mcp` | MCP server, tools, resources, prompts, skills, install | `hou`, `hwebserver` |
| `houdini_mcp_plugin` | hwebserver endpoints, dispatcher, `hou` commands | `mcp`, `httpx` |
| `houdini_mcp_protocol` | command enums, request/response models, error codes | anything third-party |

The only shared code is `houdini_mcp_protocol`.
It must stay importable by Houdini's Python.

## Repository layout

```text
houdini-mcp/
├── houdini/                      # Houdini package assets
│   ├── MainMenuCommon.xml
│   ├── python3.11libs/uiready.py
│   ├── python3.13libs/uiready.py
│   └── python3.14libs/uiready.py
├── src/
│   ├── houdini_mcp/              # MCP server
│   │   ├── bridge.py             # HTTP client for the plugin
│   │   ├── config.py
│   │   ├── constants.py
│   │   ├── errors.py
│   │   ├── install.py            # package JSON install/uninstall
│   │   ├── logging_config.py
│   │   ├── server.py             # MCPServer and lifespan
│   │   ├── tools/
│   │   └── __main__.py
│   ├── houdini_mcp_plugin/       # runs inside Houdini
│   │   ├── commands/             # hou command handlers
│   │   ├── constants.py
│   │   ├── dispatcher.py
│   │   ├── http.py               # hwebserver endpoints
│   │   └── startup.py
│   └── houdini_mcp_protocol/     # shared contract
│       ├── commands.py
│       ├── errors.py
│       ├── models.py
│       └── __init__.py
├── tests/
│   ├── mcp/
│   ├── mcp_plugin/
│   ├── mcp_protocol/
│   └── integration/
├── ARCHITECTURE.md
├── CONTRIBUTING.md
├── README.md
└── pyproject.toml
```

## Current features

- One MCP tool: `get_scene_info`.
- One plugin command: `scene.get_scene_info`.
- Plugin lifecycle: start, stop, status, autostart.
- Package install and uninstall.
- No resources, prompts, skills, or templates yet.

## Adding a command and tool

1. Add a member to `PluginCommand` in `src/houdini_mcp_protocol/commands.py`.
2. Add a handler under `src/houdini_mcp_plugin/commands/`:
   ```python
   @register_command(PluginCommand.SCENE_GET_SCENE_INFO)
   def get_scene_info() -> dict[str, Any]: ...
   ```
3. Import the command module from `src/houdini_mcp_plugin/commands/__init__.py`.
4. Add an MCP tool under `src/houdini_mcp/tools/`:
   ```python
   @server.tool()
   async def get_scene_info(ctx: BridgeContext) -> dict[str, Any]:
       """Return information about the current Houdini scene."""
       bridge = ctx.request_context.lifespan_context['bridge']
       return await bridge.execute(PluginCommand.SCENE_GET_SCENE_INFO)
   ```
5. Register the tool from `src/houdini_mcp/tools/__init__.py`.
6. Add a unit or integration test.

`PLUGIN_COMMANDS` is derived from `PluginCommand`, so it updates automatically.

## Resources and prompts

These are planned, not implemented yet.

- `src/houdini_mcp/resources/` will hold resource registration and loaders.
- `src/houdini_mcp/prompts/` will hold prompt registration.
- Registration should stay explicit, like `register_tools(server)`:
  ```python
  register_resources(server)
  register_prompts(server)
  ```

A static markdown resource should be placed under `resources/` and registered with a stable URI.
A prompt should be a function under `prompts/` with a short docstring.
Do not register resources or prompts through import side effects.

## Skills

These are planned, not implemented yet.

```text
src/houdini_mcp/skills/
├── loader.py
├── models.py
└── builtin/
    └── <skill-name>/
        ├── skill.toml          # manifest
        ├── SKILL.md            # main instructions
        ├── references/         # supporting markdown
        └── templates/          # optional .hip/.hdanc/USD files
```

The manifest describes the skill and its resources.
`SKILL.md` is the main prompt body.
Supporting markdown belongs in `references/`.
Optional Houdini files belong in `templates/`.

The loader should expose:

- `skill://<name>/SKILL.md`
- `skill://<name>/references/<file>`
- `skill://<name>/templates/<file>`

A generic `use_skill(skill, context="")` prompt reads the skill and formats `{context}`.
The server instructions should include a short index of available skills.

User skills should be loaded from `~/.config/houdini-mcp/skills/` or `$HOUDINI_MCP_SKILLS`, with user skills overriding built-ins by name.

Skills are data, not code.
Do not put executable Python inside a skill bundle.

## Markdown conventions

- Use lowercase, hyphenated filenames.
- Keep one topic per file.
- Put the main workflow in `SKILL.md`.
- Put deeper reference material in `references/`.
- Use `skill.toml` for machine-readable metadata.
- Do not use YAML frontmatter.

## Templates

Templates are planned, not implemented yet.

- A `.hip` file is the source of truth.
  Do not convert it into hand-maintained markdown.
- `template.inspect` should run `hython` in a separate process and return a compact JSON graph summary.
- `template.list` and `template.inspect` are safe.
- `template.merge` or `template.open` would modify the current scene and needs explicit confirmation.
- Treat `.hip` templates as trusted input because they can execute Houdini-side scripts.
- Use Git LFS if built-in templates become large.

## Environment variables

Server:

- `HOUDINI_MCP_HOST`
- `HOUDINI_MCP_PORT`
- `HOUDINI_MCP_TIMEOUT`
- `HOUDINI_MCP_LOG_LEVEL`

Plugin:

- `HOUDINI_MCP_PORT`
- `HOUDINI_MCP_BIND`
- `HOUDINI_MCP_AUTOSTART`

External:

- `HOUDINI_USER_PREF_DIR` is read only by the install command.

Package file:

- `HOUDINI_MCP` points at the repository root.
- `PYTHONPATH` points at `$HOUDINI_MCP/src`.
- `path` points at `$HOUDINI_MCP/houdini`.

Environment-variable names and defaults belong in each package's `constants.py`.

## Testing

```text
tests/
├── mcp/               # server construction and settings
├── mcp_plugin/        # dispatcher unit tests with a fake hdefereval
├── mcp_protocol/      # request/response models
└── integration/       # live Houdini tests
```

The default run excludes integration tests:

```sh
uv run pytest
```

Run live Houdini tests manually:

```sh
uv run pytest -m integration
```

Integration tests talk to the plugin over HTTP.
They do not import Houdini modules.

## Install flow

1. Create a virtual environment and install the server editable.
2. Run `python -m houdini_mcp install`.
3. The command writes `houdini_mcp.json` into the detected Houdini packages directories.
4. The package file adds `$HOUDINI_MCP/src` to `PYTHONPATH` and `$HOUDINI_MCP/houdini` to the Houdini path.
5. Restart Houdini.
6. Point the MCP client at `.venv/bin/python -m houdini_mcp`.

Remove the package file with:

```sh
python -m houdini_mcp uninstall
```

## Known limitations

- Only `get_scene_info` exists.
- Resources, prompts, skills, and templates are not implemented.
- Stop is logical: hwebserver stays up, but health reports `stopped`.
- There is no session-selection tool for multiple Houdini sessions.
- Restart Houdini after changing plugin code.
- Restart the MCP client after changing server code.
- The package file points at the live repository, so moving the repo requires reinstalling.
