"""Overlap auditing for FreeCAD assemblies.

Audit DAG roots, not every object with a shape: tools overlap their base by
construction, so a naive sweep reports guaranteed false positives. `check_disjoint`
proves overlap exists, `pairwise_overlap` names the pairs, and
`cut_removed_material`/`bite` catch a boolean that removed nothing.
"""

TOLERANCE_MM3 = 1e-3          # OCCT multiFuse round-off is 3e-6..7e-6 mm3 on a disjoint model
DEFAULT_PAIR_THRESHOLD = 1.0  # mm3; lower it when hunting small interpenetrations


def dag_roots(doc_or_parts):
    """Final parts: objects no other object references via Base, Tool or Shapes.

    Also tracks replacements for free — a superseded base stops being a root and
    the new boolean result becomes one, which name-prefix filters miss.
    """
    objs = doc_or_parts.Objects if hasattr(doc_or_parts, "Objects") else list(doc_or_parts)
    referenced = set()
    for o in objs:
        for attr in ("Base", "Tool"):
            link = getattr(o, attr, None)
            if link is not None:
                referenced.add(link.Name)
        for link in getattr(o, "Shapes", None) or []:
            if link is not None:
                referenced.add(link.Name)
    return [o for o in objs
            if o.Name not in referenced
            and getattr(o, "Shape", None) and not o.Shape.isNull()]


def check_disjoint(parts):
    """(sum_of_volumes, fused_union_volume, overlap). Compare overlap to TOLERANCE_MM3.

    `parts` is a list of objects or a {role: object} dict.
    """
    objs = list(parts.values()) if isinstance(parts, dict) else list(parts)
    objs = [o for o in objs if getattr(o, "Shape", None) and not o.Shape.isNull()]
    if not objs:
        return 0.0, 0.0, 0.0
    total = sum(o.Shape.Volume for o in objs)
    union = objs[0].Shape.multiFuse([o.Shape for o in objs[1:]]).Volume
    return total, union, total - union


def pairwise_overlap(parts, threshold=DEFAULT_PAIR_THRESHOLD):
    """[(name_a, name_b, overlap_mm3)], worst first.

    Thresholded: an empty list means "none above the threshold", not "none".
    """
    objs = list(parts.values()) if isinstance(parts, dict) else list(parts)
    objs = [o for o in objs if getattr(o, "Shape", None) and not o.Shape.isNull()]
    out = []
    for i, a in enumerate(objs):
        for b in objs[i + 1:]:
            if not a.Shape.BoundBox.intersect(b.Shape.BoundBox):
                continue
            try:
                vol = a.Shape.common(b.Shape).Volume
            except Exception:
                vol = 0.0
            if vol > threshold:
                out.append((a.Name, b.Name, vol))
    return sorted(out, key=lambda t: -t[2])


def bite(cutter, part):
    """Volume a boolean would remove. Check this BEFORE creating the Part::Cut:
    it is the only way to catch a cutter that sits in an existing opening."""
    return cutter.Shape.common(part.Shape).Volume


def cut_removed_material(before_volume, after_volume, tolerance=TOLERANCE_MM3):
    """Assert-style check: a tangent or in-air cutter removes nothing."""
    removed = before_volume - after_volume
    if removed <= tolerance:
        raise AssertionError(
            "the cut removed no material (%.3f -> %.3f, %.6f removed). Either the "
            "cutter is tangent to the surface (extend it 1 mm past the face) or it "
            "sits inside a pre-existing opening (check bite() first)."
            % (before_volume, after_volume, removed))
    return removed
