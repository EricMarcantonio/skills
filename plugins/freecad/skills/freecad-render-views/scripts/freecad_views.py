"""FreeCAD 1.1 view rendering that respects the API's real limits.

Import this instead of re-deriving the workarounds: render through the document's
own ActiveView, use only the named camera presets, keep batches small, and let the
caller reopen the document when a camera looks stale.
"""

import os
import time

# Measured on ONE model (doors facing -Y) and not a fact: two careful readings have
# disagreed about viewFront vs viewRear, because the presets are axis-based and the
# answer depends which way the model faces. Probe before trusting this map.
SIDE_VIEWS = {
    "doors": "viewRear",         # reading A: -Y face (doors)
    "back": "viewFront",         # reading A: +Y face (back wall)
    "side_left": "viewLeft",
    "side_right": "viewRight",
    "plan": "viewTop",
    "bottom": "viewBottom",
    "iso": "viewIsometric",      # steep; prefer dimetric/trimetric for 3/4 reads
    "dimetric": "viewDimetric",
    "trimetric": "viewTrimetric",
    "axonometric": "viewAxonometric",
}

# saveImage wedges the GUI thread after roughly five captures in one call
SAFE_BATCH = 3


def render_views(doc, prefix, views, out_dir, width=1200, height=900, settle=2):
    """One PNG per requested view. Returns {name: path}.

    Keep `views` to SAFE_BATCH entries per call and call again for the rest.
    Prefer ONE view per call: setting a preset and capturing in the same call has
    been observed to write the previous camera's image, and even settle loops
    produced a stale frame. Captures also land late, so poll for the files.
    Uses the document's OWN view: FreeCADGui.ActiveDocument is whichever document
    was built or opened last, which silently captures the wrong model.
    """
    import FreeCADGui
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    if len(views) > SAFE_BATCH:
        raise ValueError("render at most %d views per call: saveImage wedges the "
                         "GUI thread beyond that" % SAFE_BATCH)
    av = FreeCADGui.getDocument(doc.Name).ActiveView
    try:
        av.setCameraType("Orthographic")
    except Exception:
        pass
    saved = {}
    for name in views:
        getattr(av, SIDE_VIEWS[name])()
        av.fitAll()
        for _ in range(settle):
            FreeCADGui.updateGui()
            time.sleep(0.3)
        path = os.path.join(out_dir, "%s_%s.png" % (prefix, name))
        av.saveImage(path, width, height, "White")
        saved[name] = path
    return saved


def probe_marker(doc, marker_name, views):
    """Which preset shows `marker_name` in front? Render a one-sided marker object
    and look: this is the only reliable way to map presets to faces."""
    return render_views(doc, "probe_" + marker_name, views, "/tmp/probe", width=400, height=300)


def reopen(doc_name, path):
    """Reopen a document for a fresh camera state (stale views are common)."""
    import FreeCAD
    if doc_name in [d.Name for d in FreeCAD.listDocuments().values()]:
        FreeCAD.closeDocument(doc_name)
    return FreeCAD.openDocument(path)


def flat_lines(doc):
    """Exploded views read far better with edges drawn."""
    import FreeCADGui
    for o in doc.Objects:
        vo = o.ViewObject
        if vo is None or not vo.Visibility or not o.TypeId.startswith("Part::"):
            continue
        try:
            vo.DisplayMode = "Flat Lines"
        except Exception:
            pass
    FreeCADGui.updateGui()
