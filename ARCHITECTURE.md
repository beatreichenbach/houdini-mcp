# Architecture

## Runtime flow

```text
+----------------------+
|      MCP client      |
+----------+-----------+
           |
           | stdio
           v
+----------+-----------+
|     houdini_mcp      |
+----------+-----------+
           |
           | HTTP JSON on loopback
           v
+----------+-----------+
|  houdini_mcp_plugin  |
+----------+-----------+
           |
           | hdefereval / hou
           v
+----------+-----------+
|       Houdini        |
+----------------------+
```

## Python packages

- `houdini_mcp` is the MCP server, started by the MCP client outside Houdini.
- `houdini_mcp_plugin` is the HTTP receiver inside Houdini, executing `hou` calls on the main thread.
- `houdini_mcp_protocol` is the shared, stdlib-only contract between them.

## Package boundaries

| Package                | Imports                                                   |
|------------------------|-----------------------------------------------------------|
| `houdini_mcp`          | `mcp`, `httpx`, `platformdirs`, `houdini_mcp_protocol`    |
| `houdini_mcp_plugin`   | `hou`, `hwebserver`, `hdefereval`, `houdini_mcp_protocol` |
| `houdini_mcp_protocol` |                                                           |

## Repository layout

```text
houdini-mcp/
├── houdini/                      # Houdini package assets
└── src/
    ├── houdini_mcp/              # MCP server
    │   ├── content/              # markdown content
    │   │   ├── instructions/
    │   │   ├── shared/
    │   │   └── workflows/
    │   ├── prompts/              # content loading and prompt registration
    │   ├── resources/            # resource registration
    │   └── tools/                # MCP tools
    ├── houdini_mcp_plugin/       # Houdini-side plugin
    └── houdini_mcp_protocol/     # shared contract
```

## Design principles

- The server never imports Houdini modules.
- The plugin never imports MCP or HTTP client libraries.
- The protocol stays stdlib-only so both halves can import it.
- Tools, resources, and prompts are registered explicitly by the server, not through import side effects.
- Command names are shared enums, and the plugin's known-command set is derived from them.
- Content is data, not executable code.
- The Houdini package points at the live repository, so updating is a git pull rather than reinstalling a package.

## Content

Content is server-side.
They do not require the plugin and do not import Houdini modules.

Content lives in three directories:

- `content/instructions/`: server-level guidance.
  All files are concatenated into the MCP server instructions.
- `content/shared/`: reusable fragments.
  They are included with `{include:name}` and are not exposed on their own.
- `content/workflows/`: one markdown file per workflow prompt.

Built-in content lives under `src/houdini_mcp/content/`.
The local content directory lives in the platform user config directory under `houdini_mcp/content/`.
It is prepended to the built-in content, so local files take priority.
A local file with the same relative name replaces the built-in file.
New local files add content.

Workflows use `{context}` for the prompt argument and `{include:name}` for shared fragments.
Each workflow file becomes a prompt with the same name.

## Resources

Resources expose live Houdini data as read-only JSON.
They require the plugin:

- `houdini-mcp://scene`: current scene information.
- `houdini-mcp://scene/selection`: nodes selected in the current session.
- `houdini-mcp://scene/nodes`: top-level nodes in the current scene.
- `houdini-mcp://scene/nodes{+path}`: details for a node, for example `houdini-mcp://scene/nodes/obj/geo1`.

Static resources cannot receive a request context, so dynamic resources read the process bridge set during the server
lifespan.

## Tools

Tools are executable MCP actions.
Unlike content and resources, tools are code on the server side and often require a matching plugin command.

A tool that wraps an existing Houdini command lives under `src/houdini_mcp/tools/`.
A tool that needs new Houdini behavior also needs a matching command enum and a handler under
`src/houdini_mcp_plugin/commands/`.

