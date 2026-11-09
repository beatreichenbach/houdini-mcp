# Houdini MCP

An MCP server for SideFX Houdini.

## Installation

Create a virtual environment and install the server:

```sh
python -m venv .venv
.venv/bin/pip install -e .
```

Install the Houdini package file:

```sh
.venv/bin/python -m houdini_mcp install
```

This writes `houdini_mcp.json` into the detected Houdini packages directories, for example `~/houdini21.0/packages`.
Use `--packages-dir PATH` if detection is wrong.

Point your MCP client at the server:

```json
{
  "mcpServers": {
    "houdini": {
      "command": "/path/to/houdini-mcp/.venv/bin/python",
      "args": [
        "-m",
        "houdini_mcp"
      ]
    }
  }
}
```

Restart Houdini after installing the package file.

The plugin listens only on `127.0.0.1` and rejects browser and non-local requests.
Houdini and the MCP client must run on the same machine.

To remove it:

```sh
.venv/bin/python -m houdini_mcp uninstall
```

## Custom content

Built-in content lives in `src/houdini_mcp/content/`.
User content lives in the platform config directory or custom directories set with `HOUDINI_MCP_CONTENT` under
`houdini_mcp/content/` and can overwrite existing files:

```text
~/.config/houdini_mcp/content/
└── workflows/
    └── my-workflow.md
```

Use `{context}` for the caller’s context and `{include:name}` to include a shared fragment.

Inspect content with:

```sh
.venv/bin/python -m houdini_mcp content path
.venv/bin/python -m houdini_mcp content list
```

## Environment variables

Server variables are read by the MCP server process.
Plugin variables are read inside Houdini; set them in `houdini.env` or the environment used to launch Houdini.

| Variable                     | Used by        | Default        | Description                                                   |
|------------------------------|----------------|----------------|---------------------------------------------------------------|
| `HOUDINI_MCP_PORT`           | Server, Plugin | `8100`         | First port the server scans and the plugin prefers.           |
| `HOUDINI_MCP_TIMEOUT`        | Server         | `135`          | Command timeout in seconds.                                   |
| `HOUDINI_MCP_LOG_LEVEL`      | Server         | `INFO`         | Log level.                                                    |
| `HOUDINI_MCP_CONTENT`        | Server         | none           | Additional content roots, separated by the OS path separator. |
| `HOUDINI_MCP_AUTOSTART`      | Plugin         | `1`            | Set to `0` to disable autostart.                              |
| `HOUDINI_MCP_AUTO_LAYOUT`    | Plugin         | `0`            | Set to `1` to allow network layout.                           |
| `HOUDINI_MCP_OUTPUT_TIMEOUT` | Plugin         | `2`            | Seconds to wait for render or cache output files.             |
| `HOUDINI_MCP_PROJECT_ROOT`   | Plugin         | none           | Optional root for scene and file operations.                  |
| `HOUDINI_MCP`                | Plugin         | set by install | Repository root used by the Houdini package file.             |

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup and check commands.

## License

MIT License.
Copyright 2026 - Beat Reichenbach.
See the [License](LICENSE) file for details.
