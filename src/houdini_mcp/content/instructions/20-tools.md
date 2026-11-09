# Tool use

- Use the narrowest tool that matches the task.
- Check what exists before creating: node types, parameters, operators, and available tools.
- Check the running Houdini version before relying on a version-specific node or parameter.
- Prefer purpose-built workflow tools, then native nodes, then VEX, then Python.
- Prefer a canonical shelf tool (`run_shelf_tool`) over hand-building a known network.
  This includes Component Builder and other shelf-tool setups.
- Never use Python to create nodes, set parameters, wire inputs, or press UI buttons when a tool or native node exists.
- Use `create_node`'s `position` when the flow direction matters, and layout new networks with
  `layout_children` after building.
- Do not call the Houdini plugin over raw HTTP. Use the server's tools.
- Batch independent calls.
  Every call has a fixed round-trip cost before it does any work.
- Only use tools this server exposes.
  Workflow guides may describe a larger planned tool surface; do not call a tool that is not available.
- Do not invent tool names, parameters, or node types.
  If something is missing, say so.
- Read tool results, including error fields.
  Do not assume success from a lack of exception.
- For long-running work, wait for the result.
  Do not poll the scene or the disk.
