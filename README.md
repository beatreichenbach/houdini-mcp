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

By default, the plugin binds to `127.0.0.1`.
If you change `HOUDINI_MCP_BIND`, set `HOUDINI_MCP_HOST` on the MCP client to the same address.

To remove it:

```sh
.venv/bin/python -m houdini_mcp uninstall
```

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development setup and check commands.

## License

MIT License.
Copyright 2026 - Beat Reichenbach.
See the [License](LICENSE) file for details.
