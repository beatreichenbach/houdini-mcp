# Architecture

## Overview

The project has two runtime halves and one shared contract:

- `houdini_mcp` is the MCP server, started by the MCP client outside Houdini.
- `houdini_mcp_plugin` is the HTTP receiver inside Houdini, executing `hou` calls on the main thread.
- `houdini_mcp_protocol` is the shared, stdlib-only contract between them.

Houdini package assets live in `houdini/`.

## Runtime flow

```text
MCP client
  │ stdio
houdini_mcp
  │ HTTP on loopback
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
├── src/
│   ├── houdini_mcp/              # MCP server
│   ├── houdini_mcp_plugin/       # Houdini-side plugin
│   └── houdini_mcp_protocol/     # shared contract
├── tests/
├── ARCHITECTURE.md
├── CONTRIBUTING.md
├── README.md
└── pyproject.toml
```

## Design principles

- The server never imports Houdini modules.
- The plugin never imports MCP or HTTP client libraries.
- The protocol stays stdlib-only so both halves can import it.
- Tools, resources, and prompts are registered explicitly by the server, not through import side effects.
- Command names are shared enums, and the plugin's known-command set is derived from them.
- Skills and templates are data, not executable code.
- The Houdini package points at the live repository, so updating is a git pull rather than reinstalling a package.

## Resources, prompts, and skills

Resources, prompts, and skills are server-side data.
They do not require the plugin and do not import Houdini modules.

A skill is a directory under `src/houdini_mcp/skills/builtin/<name>/`:

```text
<name>/
├── skill.toml          # metadata
├── SKILL.md            # main instructions
├── references/         # supporting markdown
└── templates/          # optional Houdini files
```

The server exposes a skill's `SKILL.md` and supporting files as resources, and can expose a prompt that reads the skill.
User skills can be loaded from a separate skills directory and override built-ins by name.

Skills should contain markdown and data only.
Do not put executable Python inside a skill.

## Templates

A `.hip` file is a reference and the source of truth.
Do not convert it into hand-maintained markdown.

The planned inspection path runs `hython` in a separate process and returns a structured summary, so the model can read the graph without loading the file into the user's session.

Templates can execute Houdini-side scripts, so treat them as trusted input.
