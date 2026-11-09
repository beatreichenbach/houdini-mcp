# Shading

Build and assign materials in Houdini.

Goal: {context}

The renderer decides the shader builder. Establish it before creating anything:
`get_render_settings` and `get_scene_info`. In Solaris, materials belong in a
Material Library LOP, never in `/mat` or at the object level.

## Assign first, then author

- Get a material bound and visible before making it good. An unassigned perfect shader looks identical to no shader.
- Use the shader builder that matches the renderer. For Arnold, see the `arnold` workflow.
- Do not mix shader builders from different renderers in one material library.
- Neutral gray is a linear value: use `0.2`, not `0.5`.

## Judgement

- Layering is a first-class approach, not a workaround. Build layered shaders rather than hand-mixing outputs.
- Textures need UVs. UV work belongs upstream in SOPs and is not a shading fix.
- Normal maps need the correct tangent-space convention; a mismatch reads as a lighting bug.
- Overrides and stylesheets are how one material serves many objects with variation. Reach for them before duplicating a shader per variant.
- Expose shader controls as parameters so lookdev is a parameter change, not a graph edit.

## Order of work

1. `get_render_settings` and `get_scene_info` to establish the renderer.
2. `list_materials` and `get_material_info` to see what already exists.
3. Create and **assign** the material, then verify the binding with `get_usd_bound_material`. Use a viewport look or `capture_screenshot` only if the user asks.
4. Author base colour, then roughness and specular, then detail maps. Judge each against the USD binding and, if approved, a lit viewport look.
5. Promote the controls you will actually tweak.
6. Use overrides or stylesheets for per-object variation instead of copies.

{include:cleanup}
