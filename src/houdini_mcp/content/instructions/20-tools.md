# Tool use

- Use the narrowest tool that matches the task.
- Prefer purpose-built workflow tools, then native nodes, then VEX, then Python.
- Prefer a canonical shelf tool or the studio template the scene provides over hand-building a known network.
  Use the shelf tool only when no studio template exists for that asset class.
- Templates are network boxes. Resolve them with `list_network_boxes`; box
  membership is the template, not node names, position or adjacency.
- A node-by-node copy leaves each copy's inputs wired to the originals.
  Reconnect every input whose source is inside the copied set to the
  corresponding copy before editing parameters, and check the chain is
  contiguous afterwards.
- Never use Python to create nodes, set parameters, wire inputs, or press buttons when a tool or native node exists.
- Use `create_node`'s `position` when flow direction matters. Layout only new nodes.
- Place a new or copied branch as a block in free space beside the existing network (`layout_nodes`);
  never reflow a network that contains a template or a hand-built layout.

## Batch the work

- Every call is a round trip to Houdini's main thread. A round trip usually costs more than the cook.
- Combine independent reads and writes into one `execute` call. Do not issue one tool call per assistant message.
- Build repetitive chains with `build_network` (whole graph) or `build_sop_chain` (linear SOP chain).
  `build_network` takes `parent_path`, `nodes`, `dry_run`, `layout`.
  A node entry accepts `type`, `name`, `parms`, `inputs`, `flags`, `color`, `comment`, `expressions`,
  `override_expression`.
  An input entry is `{"index": 0, "source": "<node name>", "source_output": 0}`.
  Validate an unfamiliar spec with `dry_run: true`.
- Keep output small. Never dump unfiltered `usdcat` or full prim/attribute listings.
  Filter at the source: `Select-String`, `get_usd_prim` `attr_patterns` and `full: false`,
  `list_usd_prims` `depth` and `prim_type`. Large outputs slow every later call.
- Do not enumerate HDA internals. Reach for `find_nodes` and `get_node_info`
  on the nodes you need instead of listing a subtree.
- Do not re-run a command that already returned the data you need.
- Use only tools this server exposes. Do not invent tool names, parameters, or node types.
- Read tool results, including error fields.
  Do not assume success from a lack of exception.
- For long-running work, wait. Do not poll the scene or disk.

## Efficiency

- A template-based component conversion takes roughly 6-10 calls: one source
  inspection, one or two builds, one verification.
- A simple component asset without a template takes roughly 10-15 calls.
- If a routine build passes about 20 calls, stop and reassess.
