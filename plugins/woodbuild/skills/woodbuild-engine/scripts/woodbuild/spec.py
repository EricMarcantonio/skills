"""The build spec: the only seam between reasoning and computation.

A spec describes an envelope, a wall build-up, openings, roof and floor
structure, known substitutions and price search terms. Everything downstream
(frame, optimise, bom, report) reads the spec and nothing else.
"""

import json
from dataclasses import dataclass

from . import stock


class SpecError(Exception):
    """Raised when a spec cannot produce a closed, buildable envelope."""


@dataclass
class BuildSpec:
    data: dict

    # ---- io -----------------------------------------------------------
    @classmethod
    def load(cls, path):
        with open(path) as fh:
            return cls(json.load(fh))

    def save(self, path):
        with open(path, "w") as fh:
            json.dump(self.data, fh, indent=2, sort_keys=False)
            fh.write("\n")

    # ---- accessors ----------------------------------------------------
    @property
    def envelope(self):
        return self.data["envelope"]

    def openings(self, wall=None):
        items = self.data.get("openings", [])
        return [o for o in items if wall is None or o["wall"] == wall]

    def substitutions(self):
        return self.data.get("substitutions", [])

    def search_terms(self):
        return self.data.get("pricing", {}).get("search", {})

    def option(self, key, default=None):
        return self.data.get("options", {}).get(key, default)

    # ---- derived dimensions -------------------------------------------
    def wall_build_up(self):
        total = 0.0
        for layer in self.data["wall"]["layers_out_to_in"]:
            if layer in stock.SHEETS or layer in stock.BOARDS:
                total += stock.thickness(layer)
            elif layer.startswith(("siding_", "osb_", "stud_")):
                total += float(layer.split("_")[-1])
            else:
                raise SpecError("unknown wall layer: %s" % layer)
        return total

    def roof_build_up(self):
        return float(self.data["roof"]["build_up"])

    def wall_top_front(self):
        """Top of the wall panels on the tall side (roof underside at the front)."""
        return self.envelope["height_tall"] - self.roof_build_up()

    def band_top(self):
        band = [o for o in self.openings("front") if o["kind"] == "band"]
        if not band:
            return None
        return float(band[0]["sill"]) + float(band[0]["height"])

    def band_sill(self):
        band = [o for o in self.openings("front") if o["kind"] == "band"]
        return None if not band else float(band[0]["sill"])

    def door_head(self):
        doors = [o for o in self.openings("front") if o["kind"] == "door"]
        if not doors:
            return 0.0
        return float(doors[0]["sill"]) + float(doors[0]["height"])

    # ---- validation ---------------------------------------------------
    def _check_stock_classes(self, problems):
        fields = [("wall.stud", self.data["wall"].get("stud")),
                  ("roof.rafter", self.data["roof"].get("rafter")),
                  ("roof.deck", self.data["roof"].get("deck")),
                  ("floor.joist", self.data["floor"].get("joist")),
                  ("floor.deck", self.data["floor"].get("deck")),
                  ("floor.skids", self.data["floor"].get("skids"))]
        for name, cls in fields:
            if cls is None:
                continue
            if cls not in stock.SHEETS and cls not in stock.BOARDS:
                problems.append("%s: unknown stock class %s" % (name, cls))
        for o in self.openings():
            if o.get("header") and o["header"] not in stock.BOARDS:
                problems.append("opening header: unknown stock class %s" % o["header"])

    def validate(self):
        problems = []
        self._check_stock_classes(problems)

        known_walls = ("front", "back", "left", "right")
        for o in self.openings():
            if o["wall"] not in known_walls:
                problems.append("opening on unknown wall: %s" % o["wall"])

        env = self.envelope
        try:
            build_up = self.wall_build_up()
        except SpecError as exc:
            problems.append(str(exc))
            build_up = 0.0
        if 2 * build_up >= env["width"]:
            problems.append("wall build-up %.1f mm does not fit inside width %.1f mm"
                            % (build_up, env["width"]))
        if 2 * build_up >= env["depth"]:
            problems.append("wall build-up %.1f mm does not fit inside depth %.1f mm"
                            % (build_up, env["depth"]))

        for wall, span in (("front", env["width"]), ("back", env["width"]),
                           ("left", env["depth"]), ("right", env["depth"])):
            # an opening spans between the corner assemblies, not the interior clear
            limit = span - 2 * float(self.data["wall"].get("corner_width", 89.0))
            for o in self.openings(wall):
                if float(o["width"]) > limit:
                    problems.append("%s %s opening %.1f mm is wider than the %s wall "
                                    "allows between corners (%.1f mm)"
                                    % (wall, o["kind"], float(o["width"]), wall, limit))
                if float(o["sill"]) + float(o["height"]) > self.wall_top_front():
                    problems.append("%s %s opening tops out above the wall top"
                                    % (wall, o["kind"]))
                if o["kind"] == "door" and wall in ("left", "right"):
                    problems.append("doors belong on the front or back wall")

        if self.data["floor"].get("below_datum") and float(self.data["floor"]["build_up"]) <= 0:
            problems.append("floor build-up must be positive to sit below the datum")
        if not self.data["floor"].get("below_datum"):
            problems.append("floor structure must sit below the datum "
                            "(floor.below_datum is false)")

        # band must clear the door head and fit under the roof build-up
        if self.band_top() is not None:
            if self.band_top() > self.wall_top_front():
                problems.append("band does not fit under the roof build-up: band top "
                                "%.1f mm exceeds wall top %.1f mm"
                                % (self.band_top(), self.wall_top_front()))
            if self.band_sill() < self.door_head():
                problems.append("band does not fit: band sill %.1f mm is below the door "
                                "head %.1f mm" % (self.band_sill(), self.door_head()))

        if problems:
            raise SpecError("; ".join(problems))
        return None
