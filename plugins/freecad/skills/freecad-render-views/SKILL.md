---
name: freecad-render-views
description: Use when rendering or screenshotting FreeCAD views, exporting per-side or exploded image sets, or when a FreeCAD render comes out blank, stale, of the wrong document, or refuses to change.
---

# Rendering FreeCAD views reliably

FreeCAD 1.1's view API is narrower than it looks, and most failures are silent: you
get an image, it is just the wrong one. Verify captures instead of trusting them.

## The rules

- **Render through the document's own view.** `FreeCADGui.ActiveDocument` is
  whichever document was built or opened last, so a loop rendering "the assembled
  model" while another document exists captures that other document. Always
  `FreeCADGui.getDocument(doc.Name).ActiveView`.
- **Never assume what a preset shows — probe it.** The presets are axis-based, and
  two careful readings of the same model have disagreed about `viewFront` vs
  `viewRear` because it depends on which way the model faces. Determine it with a
  one-sided probe: add an opaque slab with a colour marker on exactly one side,
  render, and see which preset puts the marker in front. BoundBox ground truth beats
  labels (`Handle` protruding to −Y tells you which face is the door).
  `scripts/freecad_views.py` ships a `SIDE_VIEWS` map measured on one model
  (doors facing −Y) — treat it as a starting guess, not a fact.
- **`viewPosition` and `viewUp` are read-only.** Assigning raises
  `RuntimeError: Extension object missing implement of setattr`, and camera
  read-back is useless (`av.viewPosition` is a bound method;
  `getCameraOrientation()` returns a near-constant rotation for every preset).
  Only the named presets work: `viewFront`, `viewRear`, `viewLeft`, `viewRight`,
  `viewTop`, `viewBottom`, `viewIsometric`, `viewDimetric`, `viewTrimetric`,
  `viewAxonometric`. Orbit to reach other angles; verify by probe, never by reading
  the camera.
- **Set the camera in one call and capture in the next.** Setting a preset and
  calling `saveImage` in the same `execute_code` call can write the *previous*
  camera's image; even repeated `updateGui()` + sleeps still produced one stale
  frame out of three. Two calls, one view each, never failed.
- **Captures land late, and `execute_code` is fire-and-forget.** It returns
  "Python code execution scheduled" with no stdout and the script keeps running
  after the call returns, so files appear afterwards. Write results to a file and
  poll for them; do not read a missing file as a failure. A long-running loop also
  stops returning entirely — batch about three views per call and re-check the
  directory between calls.
- **Orthographic for elevations:** `av.setCameraType("Orthographic")`; the default
  perspective makes preset views look steep and foreshortened.
- **Never put a TechDraw page in a document you still drive.** A
  `TechDraw::DrawPage` has no `.Shape`, so anything that walks the document reading
  `.Shape` — including the FreeCAD MCP screenshot path — raises
  `'TechDraw.DrawPage' object has no attribute 'Shape'` and then fails on every
  later call in that document. Keep drawing pages in their own document.
- **Exploded views separate each part along its own normal** and read far better in
  `Flat Lines` display mode. Thin panels are edge-on in a straight-on view, so use a
  trimetric or plan view for an exploded set.
- **Mirror-symmetric models need a one-sided marker** to say which side you are
  looking at; no view of a symmetric part can tell you whether it is "left" or
  "right".
- **A part that "disappears" under a sloped roof is intersecting it**, not
  mis-rendering. Check the model.

## Script

```python
import sys; sys.path.insert(0, "/Users/eric/.pi/agent/skills/freecad-render-views/scripts")
from freecad_views import render_views, reopen, flat_lines
render_views(doc, "Shed", ["doors"], "/tmp/views")     # one view, one call
```
`render_views` refuses more than three views per call and uses the document's own
view. Reopen the document between batches (`reopen`) when a camera looks stale.
