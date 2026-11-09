# Arnold

Use Arnold for rendering, materials, and lighting in Solaris.

## Scope

- Render with Arnold through Solaris. Do not use Mantra.
- Do not create materials or lights outside Solaris: no `/mat`, no object-level materials, and no object-level lights.

## Component assets

- Build reusable assets with the Component Builder shelf tool.
- After each Component Geometry node, insert a Mesh LOP in Edit mode, set its primitive pattern to `%type:Mesh`, and turn on **Double Sided**. Place it before Component Material so the bindings and Component Output see the double-sided mesh.
- Thin surfaces, leaves, cards, cloth, and open meshes need this. Arnold does not render backfaces otherwise.

## Materials

- Use a Material Library LOP. Inside it, create an Arnold Material Builder (`arnold_materialbuilder`) and build the shader network there.
- Name the material builder after the material: `Gray`, `Wood`, `Water`. Do not add `_mtl`, `_mat`, or `_shader`.
- Connect the material to the Material Library output.
- Assign with Component Material for component assets, or `assignmaterial` for scene-level binds.
- Do not use Karma Material Builder, MaterialX Standard Surface, or USD Preview Surface for Arnold unless the user explicitly asks for them.
- Neutral gray is a linear value: use `0.2`, not `0.5`.

## Lighting

- Create Arnold lights in the LOP stage. Do not use object-level lights.
- Balance with exposure, not raw intensity. Use lightmixer to compare, and lightlinker when a light must miss specific geometry.
- Check light parameter names with `get_parameter_schema`; do not guess.

## Rendering

- Use Arnold render settings and render products in Solaris.
- During lookdev, use the Arnold viewport only if the user asks or approves. Do not switch the viewport renderer unasked. Write to disk only when the user asks.
- A final render belongs in Solaris; do not fall back to a Mantra ROP.

## Verification

- Confirm the Mesh LOP's **Double Sided** parameter is on.
- Confirm material bindings with the USD material tools.
- If the user asked for an Arnold viewport check, confirm the active delegate is Arnold. Do not switch it just to verify.

## Context

{context}

{include:cleanup}
