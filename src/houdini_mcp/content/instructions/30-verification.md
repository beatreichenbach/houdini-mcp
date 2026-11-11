# Verification

- For a known pipeline, verify the deliverable once at the end.
  For exploratory work, verify each change.
- Read error messages fully.
  Fix the cause, not the symptom.
- Verify with data first: hierarchy, prims, bindings, attributes, lights, error nodes.
- Do not switch the renderer, frame the view, or capture screenshots unless asked or approved.
  If a visual check is approved, restore the previous renderer and view.
- Undo a failed change as a whole rather than deleting nodes one by one.
- Two failed fixes: stop and consult the docs or the user.
- Report what you verified and what you did not.

## Template-based deliverables

Verify only: root prim and kind, geo/mtl scopes, material count, bindings per mesh/subset, proxy state, and error count.
Do not dump every material attribute, full prim hierarchy, or intermediate node parameters.
Stop when the deliverable check passes. The user performs the final visual check.

Verification is reduced, not removed:

- The first asset of a new class gets the full check, including bounds and orientation against the source.
- Investigate the first failed check instead of continuing on assumptions.
- Batch several assets only after one asset of that class has passed.
