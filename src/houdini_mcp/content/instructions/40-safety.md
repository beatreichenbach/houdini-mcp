# Safety

- Confirm before destructive edits: delete, clear, overwrite, save, render, or bake.
- Save the scene before long or expensive operations.
- Do not modify unrelated nodes, selections, display flags, takes, or settings.
- Preserve the user's UI state: current network, viewport renderer, frame, framing, selection,
  display/render flags, and pane focus. Change UI state only when the task requires it.
- Respect manual node layout.
  Do not move existing nodes unless asked.
  Layout only new nodes.
- Do not save the scene unless the user asks.
- Treat external files and templates as trusted only when the user says so.
- Keep the scene recoverable: undoable changes, no silent overwrites.
