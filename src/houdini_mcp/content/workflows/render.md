# Rendering

Set up rendering in Houdini.

Goal: {context}

The renderer is the user's choice. Establish which renderer the scene uses before
following any renderer-specific page or node. `get_render_settings` and
`get_scene_info` are the first calls.

## What is renderer-independent

- Cameras and framing before lighting, lighting before materials, materials before sampling. Each of those invalidates judgements about the next.
- Resolution and sampling are different knobs. Raising resolution to fix noise is the classic waste.
- Deep output, cryptomatte, and LPE let compositing fix things without a re-render. Set them up before the first hero render.
- Render to disk only when asked. For look iteration, use the viewport renderer and `capture_screenshot`.
- Packed primitives and Alembic keep large geometry manageable. A proxy-and-swap rig is a last resort, not the default.

## Renderer-specific work

- For USD/Solaris scenes, the authority is the `solaris` workflow and its LOP render settings.
- For Arnold, use the `arnold` workflow.
- Do not mix settings or shader builders from different renderers in one scene.

## Order of work

1. `get_render_settings` and `get_scene_info` to establish the renderer and existing settings.
2. Set the camera and framing.
3. Block the lighting.
4. Assign materials.
5. Tune sampling and quality last, once the image is right.
6. Render only the requested frame range and output path, and report progress rather than guessing at completion.

{include:cleanup}
