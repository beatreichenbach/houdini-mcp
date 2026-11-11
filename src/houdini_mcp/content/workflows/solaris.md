# Solaris

Build USD scenes in Houdini's Solaris (LOPs).

Goal: {context}

## Think in layers, not in nodes

Solaris punishes anyone who treats it as SOPs with different node names. The
model you need, from `solaris/about_lops` (read it with get_help_page when a
composition question comes up):

- Every LOP output is a **fully composed stage**, not a delta. The stage's root layer is always empty except for a stack
  of sublayers.
- An edit lands in the **strongest in-memory layer**, which is why each node's edit is always visible and cannot be
  quietly overridden from elsewhere in the stage.
- LOPs **never modify a layer loaded from disk**. If the strongest sublayer is a file, the next editing node silently
  creates an anonymous in-memory layer above it and puts the edit there. Your edit is an override, not a change to the
  file.
- Solaris has **no Edit Target**. If you catch yourself wanting one, the nodes are loadlayer, layerreplace and
  edittargetlayer, not a stronger opinion sprayed downstream.

So: build the chain so the opinion you want to win is the one applied last, and
do not fight composition strength by editing the same prim twice.

## sublayer vs reference vs merge (getting this wrong is the classic tell)

- **sublayer** imports the layer(s) from a file into the layer stack. Whole-layer, no reparenting.
- **reference** imports a root prim and its descendants and attaches it onto the scene graph at a branch you choose.
  This is how an asset arrives somewhere specific.
- **merge** combines the layers from separate node chains into one layer stack. Branching then merging is normal in
  LOPs, unlike a linear SOP chain.
- A payload is the reference LOP in payload mode, not a node of its own.

## The SOP bridge, and which of the four you want

- **sopimport** takes geometry from an existing SOP network into USD prims.
- **sopcreate** builds USD geometry from scratch from a SOP network contained inside the node.
- **sopmodify** round-trips existing USD to SOPs, runs the contained network, converts back. Reach for this to edit USD
  geometry, not sopimport.
- The **lopimport SOP** goes the other way, pulling USD back into SOPs.

## Component Builder

Use the **Component Builder shelf tool** for reusable USD assets. Do not
hand-create the four nodes. The tool creates:

- **Component Geometry** contains the SOP network that defines the model. Double-click it to build the geometry and
  connect the result to the default output.
- **Material Library** contains the component's materials.
- **Component Material** binds materials onto the component geometry.
- **Component Output** assembles the final component prim and writes the USD files.

Build checklist:

1. Run the Component Builder shelf tool in `/stage`.
2. Set the display flag on Component Output. Rename it to the PascalCase asset name; its name becomes the root prim.
3. Delete every sticky note inside Component Geometry.
4. Build the geometry inside Component Geometry's SOP network, above the `default` output. Layout the internal network.
5. Name materials in the Material Library after the material.
6. Wire the nodes, set the display flag on Component Output, and layout `/stage`.

Use the proxy and simproxy outputs inside Component Geometry when the asset
needs display or collision proxies. Write the component to its own USD file and
reference it into scenes with a Reference or Asset Reference LOP.

To reference the component within the same network, create a Reference LOP,
connect the Component Output to its multi-input, and leave all parameters at
their defaults. It lands at `/<AssetName>`. Set a different hierarchy only when
the user asks for one.

## Lookdev and verification

During lookdev NEVER render to disk. Verify materials, bindings, and lights with
USD data first (`get_usd_bound_material`, `get_usd_attributes`, `list_lights`).
Do not switch the viewport renderer or capture a screenshot unless the user asks
or approves. If a visual check is approved, switch the delegate, capture, and
restore the previous renderer and view. `start_render` and render nodes are only
for final renders the user explicitly asks to be written to disk. The viewport
holds its own copy of the display-flag node's stage, so looking at a node is not
free but is far cheaper than a render.

## Order of work

1. `get_scene_info`. Do not change the network editor; work in `/stage` by node path.
2. Bring geometry in: reference to place an asset at a branch, sublayer to stack a whole layer.
3. Establish structure and transforms before look, so later nodes are not chasing paths that are still moving.
4. Materials, then lights, then render settings.
5. Verify hierarchy, bindings, and lights with USD data. Switch the viewport renderer or capture a screenshot only if
   the user asks.
6. `get_stage_info`, `list_usd_prims`, `get_usd_materials`, `get_usd_layers` to verify hierarchy, bindings and the layer
   stack. A prim that renders with the wrong material (or none): `get_usd_bound_material` names what it resolves to and
   where the binding comes from.

Wire with `connect_nodes_batch`. LOP chains read top to bottom, and
branch-then-merge is idiomatic.

## Target prim patterns

LOP nodes take **primitive patterns**, not one path. Full syntax is in
`solaris/pattern`; the load-bearing parts:

- `*` matches any characters within a name, `**` matches any number of hierarchy levels, `?` a single character,
  `[1234]` a character class. So `/Kitchen/**/Handle[1234]` reaches descendants at any depth.
- A collection is `/House/LivingRoom.collection:KeyLights`, or the shorthand `%/House/LivingRoom/KeyLights`.
- `~` prunes and `&` intersects. Both matter for cost: in the worst case a pattern compares every prim on the stage, so
  prune to prevent traversal and use `&` to narrow scope before an expensive test. This is most important with VEX
  expressions, where `&` tells Houdini which part of the stage to traverse instead of running VEX over everything.

Most LOPs default their prim-path parameter to an expression around
`lastmodifiedprims()`, because a cooking LOP records the prims it touched. That
default retargets itself when upstream paths change, which a path you typed by
hand does not. Prefer the default or a pattern over a hardcoded path, and expect
hand-typed paths to be what breaks after a rename.

## Materials

- Materials live in a Material Library LOP. Never build them in `/mat` or at the object level.
- Create the material with the shader builder for the renderer the user has chosen, and connect it to the Material
  Library output.
- Bind with Component Material for component assets, or `assignmaterial` downstream for scene-level binds. Target a
  pattern or collection rather than one prim at a time.
- Do not mix shader builders from different renderers in one material library.

## Lighting

- Create lights for the target renderer in the LOP stage. Do not use object-level lights.
- `create_light` for one light (dome, distant, rect, sphere, disk, cylinder); `create_light_rig` with a preset ("
  outdoor", "three_point", "studio", "hdri") for a set.
- Light intensity is named `xn__inputsintensity_i0b`, not "intensity", in Houdini 20+. `get_parameter_schema` gives the
  exact names on any light or material node, so check rather than guess.
- Balance with exposure, not raw intensity. Use lightmixer to compare, and lightlinker when a light must miss specific
  geometry.

## Output

- An in-memory layer is written only if it has a Save Path. configurelayer sets it.
- layerbreak discards everything below it, so what you deliver is only your own opinions. This is how a shot layer ships
  without dragging the asset it referenced.
- componentoutput is the packaged-asset path rather than a hand-rolled hierarchy.

## Failure signatures

- **Edit had no effect.** The target pattern matched nothing, or the prim lives in an unloaded payload. Unloaded payload
  contents do not appear in the scene graph tree, do not match primitive patterns, and are not touched by LOP nodes (
  `solaris/about_lops`, Payloads).
- **Edit went to the wrong layer.** You expected an Edit Target. Use loadlayer, layerreplace or edittargetlayer.
- **Nothing on disk after a render.** In-memory layer with no Save Path.
- **Material shows in the viewport but not in the final render.** The material was built outside Solaris, with the wrong
  shader builder for the renderer, or not bound to the prim.
- **Pattern is slow on a big stage.** No pruning, so every prim on the stage is being compared. Prune with `~`, narrow
  with `&`.
- **Stage slow to open.** Payloads all loading by default. configurestage, or an input-less sublayer, controls that.

## Core LOP vocabulary

A name with a version range exists only in those versions of the
20.5-22.0 range this server supports. Unannotated names exist
throughout. Check `get_scene_info` before relying on an annotated name.

| Category          | Types                                                                                                                                                      |
|-------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Scene assembly    | sublayer, reference, assetreference, merge, componentoutput, stagemanager, sceneimport                                                                     |
| Component Builder | componentgeometry, componentgeometryvariants, componentmaterial, componentoutput                                                                           |
| Layer control     | configurelayer, layerbreak, loadlayer, layerreplace, edittargetlayer                                                                                       |
| SOP bridge        | sopimport, sopcreate, sopmodify                                                                                                                            |
| Transforms        | xform, edit, matchsize, restructurescenegraph, duplicate                                                                                                   |
| Materials         | materiallibrary, assignmaterial, editmaterialproperties, editmaterial, materialvariation, materiallinker                                                   |
| Lights            | light, distantlight, domelight, lightmixer, portallight (21.0+), geometrylight (21.0+), lightlinker                                                        |
| Rendering         | renderproduct, rendervar, rendersettings                                                                                                                   |
| Instancing        | copytopoints (22.0+), instancer (20.5-21.0), pointinstancer (22.0+), scatterinstances (22.0+), modifypointinstances, splitpointinstancers, retimeinstances |
| Layout            | paintinstances (22.0+), layout (20.5-21.0), drop, editprototypes                                                                                           |
| Pruning/config    | prune, configurelayer, configureprimitive, drawmode, configurestage                                                                                        |
| USD editing       | editproperties, addvariant, setvariant, collection, scope, graftbranches, graftstages, splitscene, copyproperty, modifypaths                               |
| Constraints       | blendconstraint, followpathconstraint, lookatconstraint, parentconstraint                                                                                  |
| Geometry prims    | mesh, basiscurves, points, volume, capsule, cone, cube, cylinder, sphere                                                                                   |

The Instancing and Layout rows carry two 22.0 renames. Houdini keeps the
pre-22.0 spelling as a creation alias so old scenes load, which means the older
name still creates a node on 22.0 while the newer name does not exist before it.
Prefer the 22.0+ spelling once get_scene_info confirms 22.0, and use the
20.5-21.0 spelling when you have not checked the version.

A Python LOP is almost never the answer: creating prims, assigning materials,
setting transforms and editing layers each have a node.

{include:cleanup}
