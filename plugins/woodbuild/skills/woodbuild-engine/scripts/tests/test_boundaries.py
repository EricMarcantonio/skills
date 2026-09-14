"""The split, enforced. A store name outside homedepot-catalogue is a regression.

These tests are the reason the refactor stays done: prose drifts, and a helpful
sentence about Home Depot in the framing rules would re-couple the two concerns
without anyone noticing.
"""

import pathlib
import re
import unittest

from woodbuild.adapters import load_adapter

SKILLS = pathlib.Path(__file__).resolve().parents[4] / "skills"
# The store's identity, not the skill's directory name: the visible skills must be
# able to point at `homedepot-catalogue/scripts/homedepot_adapter.py`, so the bare
# skill slug is deliberately not a banned token. The store's own names are.
STORE_WORDS = ("Home Depot", "homedepot.ca", "homedepot.com", "hd_search",
               "hd_product", "HD_DEFAULT_STORE", "MicroPro")
STORE_OWNER = "homedepot-catalogue"
# The six visible skills this split owns. Every one of them must name the engine it
# uses. The two pre-existing FreeCAD skills are deliberately absent: they use no
# engine, they are only scanned for store knowledge.
ENGINE_USERS = {"building-from-reference", "wood-framing", "sheet-and-board-nesting",
                "build-pricing", "homedepot-catalogue", "freecad-model-to-spec"}
# The two files whose job is to name the store in order to check the seam. Their
# names are the whole exemption: any other file naming it is a regression.
STORE_NAMING_ALLOWED = {"test_boundaries.py", "test_adapters.py"}


def skill_dirs():
    return sorted(p for p in SKILLS.rglob("SKILL.md"))


class TestStoreKnowledgeIsContained(unittest.TestCase):
    def test_no_other_skill_or_engine_file_names_the_store(self):
        offenders = []
        for path in SKILLS.rglob("*"):
            if not path.is_file() or path.suffix not in (".py", ".md"):
                continue
            if STORE_OWNER in path.parts or path.name in STORE_NAMING_ALLOWED:
                continue
            text = path.read_text(errors="ignore")
            for word in STORE_WORDS:
                if word in text:
                    offenders.append("%s contains %r" % (path, word))
        self.assertEqual(offenders, [], "store knowledge escaped its skill")

    def test_only_the_two_seam_tests_are_exempt(self):
        exempt = sorted(p.name for p in SKILLS.rglob("*") if p.name in STORE_NAMING_ALLOWED)
        self.assertEqual(exempt, ["test_adapters.py", "test_boundaries.py"])

    def test_the_engine_has_no_tax_numbers(self):
        engine = SKILLS / "woodbuild-engine" / "scripts" / "woodbuild"
        offenders = []
        for path in engine.rglob("*.py"):
            text = path.read_text(errors="ignore")
            if "TAX_RATES" in text or "tax_rate_for" in text:
                offenders.append(str(path))
        self.assertEqual(offenders, [], "the engine must not carry a tax table")

    def test_the_store_adapter_is_loadable_and_offline_safe(self):
        path = SKILLS / STORE_OWNER / "scripts" / "homedepot_adapter.py"
        adapter = load_adapter(str(path))
        self.assertFalse(adapter.is_candidate(adapter.source_product))
        self.assertGreater(adapter.tax_rate("ON"), 0.0)


class TestSkillsAreWellFormed(unittest.TestCase):
    def test_every_skill_declares_its_own_name_and_a_usable_description(self):
        for path in skill_dirs():
            with self.subTest(skill=path.parent.name):
                text = path.read_text()
                front = re.search(r"^---\n(.*?)\n---\n", text, re.S)
                self.assertIsNotNone(front, "%s has no frontmatter" % path)
                front = front.group(1)
                name = re.search(r"^name: (.+)$", front, re.M)
                desc = re.search(r"^description: (.+)$", front, re.M)
                self.assertIsNotNone(name, "%s has no name" % path)
                self.assertIsNotNone(desc, "%s has no description" % path)
                self.assertEqual(name.group(1).strip(), path.parent.name)
                self.assertGreater(len(desc.group(1).strip()), 20)
                self.assertLessEqual(len(desc.group(1).strip()), 1024)

    def test_only_the_engine_is_hidden(self):
        hidden = set()
        for path in skill_dirs():
            if "disable-model-invocation: true" in path.read_text():
                hidden.add(path.parent.name)
        self.assertEqual(hidden, {"woodbuild-engine"})

    def test_every_skill_this_split_owns_points_at_the_engine(self):
        for name in sorted(ENGINE_USERS):
            path = SKILLS / name / "SKILL.md"
            with self.subTest(skill=name):
                self.assertTrue(path.exists(), "missing skill %s" % name)
                self.assertIn("woodbuild-engine", path.read_text(),
                              "%s does not name the engine it depends on" % path)

    def test_the_unrelated_freecad_skills_are_left_out_of_the_engine_rule(self):
        # They predate this split and use no engine; they are inside the store scan
        # above, and they hold no store tokens.
        for name in ("freecad-model-hygiene", "freecad-render-views"):
            self.assertTrue((SKILLS / name / "SKILL.md").exists())
            self.assertNotIn(name, ENGINE_USERS)


if __name__ == "__main__":
    unittest.main()
