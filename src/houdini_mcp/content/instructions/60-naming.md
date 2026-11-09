# Naming

## Houdini nodes

- Leave existing node names alone unless the user asks.
- Only rename Attribute Wrangles, and name them after what they do: `set_height`, `mask_water`.
- Houdini node names you create use lowercase words separated by underscores.
- Do not use generic suffixes such as `_1`, `_final`, `_new`, or `_temp`.
- Prefix intermediary input or output nulls referenced by other nodes with `IN_` or `OUT_`.

## USD assets and materials

- USD component assets are PascalCase. The Component Output node name is the asset name:
  `Pig`, `Chair`, `WaterTank`. It becomes the root prim, for example `/Pig`.
- Materials in a Material Library are PascalCase and use exactly the material name:
  `Gray`, `Wood`, `Water`. Never add `_mtl`, `_mat`, `_shader`, or similar suffixes.
- Do not rename generated Component Builder nodes. Only the Component Output and the material
  name carry meaning.
- Keep the asset name through references: `/Pig`, `/Pig/geo`, `/Pig/materials/Gray`.
