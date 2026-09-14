"""FreeCAD document -> build spec, generically.

Nothing here knows a project. Object names, the model's own roof thickness, the
roof fall and the corner width are all arguments. A build's locked decisions —
wall layers, roof build-up, floor build-up, store, substitutions — are spec data
written by `building-from-reference` at intake, never constants in this module.

This is the only module in the engine that may import FreeCAD, and only inside
the functions that need it, so the pure helpers stay testable without it.
"""

from .spec import SpecError


def bounds_from_shapes(boxes):
    """Union of [xmin, xmax, ymin, ymax, zmin, zmax] boxes."""
    boxes = list(boxes)
    if not boxes:
        raise SpecError("no shapes to bound the envelope")
    return (min(b[0] for b in boxes), max(b[1] for b in boxes),
            min(b[2] for b in boxes), max(b[3] for b in boxes),
            min(b[4] for b in boxes), max(b[5] for b in boxes))


def envelope_from_bounds(bounds, model_roof_t, roof_fall, tall_side="front"):
    """Build the envelope from the model's wall bounds.

    In the model the wall top IS the roof underside, so the product's overall
    height is that z plus the MODEL's own roof thickness. A wood roof build-up is
    a spec decision and must not enter the envelope.
    """
    xmin, xmax, ymin, ymax, _zmin, zmax_wall = bounds
    return {"width": round(xmax - xmin, 2), "depth": round(ymax - ymin, 2),
            "height_tall": round(zmax_wall + model_roof_t, 2),
            "roof_fall": float(roof_fall), "tall_side": tall_side}


def _shape_box(obj):
    shape = getattr(obj, "Shape", None)
    if shape is None or shape.isNull():
        return None
    bb = shape.BoundBox
    return [bb.XMin, bb.XMax, bb.YMin, bb.YMax, bb.ZMin, bb.ZMax]


def wall_bounds(doc, wall_object=None, panel_suffixes=("Cut", "CutL", "CutR"),
                post_prefixes=("Post",)):
    """Bounds of the wall envelope: `wall_object` when given, else the panels.

    The caller names its own objects: a modelled wall solid by name, or the panel
    and post naming convention of the model. No project names are baked in.
    """
    if wall_object:
        obj = doc.getObject(wall_object)
        if obj is None:
            raise SpecError("model has no object named %s" % wall_object)
        box = _shape_box(obj)
        if box is None:
            raise SpecError("%s has no shape" % wall_object)
        return tuple(box)
    boxes = []
    for obj in doc.Objects:
        name = obj.Name
        if not (name.endswith(tuple(panel_suffixes))
                or name.startswith(tuple(post_prefixes))):
            continue
        box = _shape_box(obj)
        if box:
            boxes.append(box)
    if not boxes:
        raise SpecError("model has neither %s nor objects starting with %s"
                        % (wall_object or "a wall solid", ", ".join(post_prefixes)))
    return bounds_from_shapes(boxes)


def band_opening(model_band, envelope_width, corner_width, height_tall,
                 roof_build_up, door_head):
    """Re-place a clerestory band for a different roof build-up and corner width.

    The band spans between the corners, not the moulded posts, and sits under the
    roof build-up, so it both narrows and drops when the build-up grows. Dropping
    it keeps the band's own height under an unchanged envelope while staying above
    the door head; if it cannot, that is a spec error, not a clamp.
    """
    band_w, band_h, _model_sill = model_band
    wall_top = height_tall - roof_build_up
    sill = round(wall_top - band_h, 2)
    if sill < door_head:
        raise SpecError("band does not fit: sill %.2f mm is below the door head %.2f mm"
                        % (sill, door_head))
    return {"wall": "front", "kind": "band",
            "width": round(envelope_width - 2 * corner_width, 2),
            "height": float(band_h), "sill": sill, "header": None,
            "mullions": 4, "panes": [3.5, 1.5, 4.5, 4.5, 1.5]}


def openings_from_cutters(doc, envelope, door_name="fw_door", band_name="fw_band",
                          corner_width=89.0, roof_build_up=0.0, extra=()):
    """Read the door and the band from the model's own cutter objects.

    Everything else an opening needs — transoms, louvres, headers, sills — is
    spec data the caller supplies through `extra`, because a model's cutters do
    not carry intent. For a real build `roof_build_up` is mandatory: its `0.0`
    default silently places the band at the wall top instead of under the roof
    build-up.
    """
    door = doc.getObject(door_name)
    band = doc.getObject(band_name)
    if door is None or band is None:
        raise SpecError("model is missing %s / %s cutters" % (door_name, band_name))
    dbox = _shape_box(door)
    if dbox is None:
        raise SpecError("%s cutter has no shape; a null cutter cannot define an "
                        "opening" % door_name)
    bbox = _shape_box(band)
    if bbox is None:
        raise SpecError("%s cutter has no shape; a null cutter cannot define an "
                        "opening" % band_name)
    door_head = round(dbox[5], 2)
    band_block = band_opening(
        model_band=(round(bbox[1] - bbox[0], 2), round(bbox[5] - bbox[4], 2),
                    round(bbox[4], 2)),
        envelope_width=envelope["width"], corner_width=corner_width,
        height_tall=envelope["height_tall"], roof_build_up=roof_build_up,
        door_head=door_head)
    return [{"wall": "front", "kind": "door", "width": round(dbox[1] - dbox[0], 2),
             "height": round(dbox[5] - dbox[4], 2), "sill": 0.0, "header": "2x8"},
            band_block] + list(extra)


def check_envelope(spec, doc, **wall_bounds_kwargs):
    """Fail loudly if the model no longer matches the spec."""
    xmin, xmax, ymin, ymax, _zmin, _zmax = wall_bounds(doc, **wall_bounds_kwargs)
    env = spec.envelope
    width = xmax - xmin
    depth = ymax - ymin
    if abs(width - env["width"]) > 1.0 or abs(depth - env["depth"]) > 1.0:
        raise SpecError("envelope mismatch: model is %.1f x %.1f mm, spec says "
                        "%.1f x %.1f mm" % (width, depth, env["width"], env["depth"]))
