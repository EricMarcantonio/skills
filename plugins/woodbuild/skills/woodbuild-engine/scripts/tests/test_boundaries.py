"""The split, enforced. A store name outside homedepot-catalogue is a regression.

These tests are the reason the refactor stays done: prose drifts, and a helpful
sentence about Home Depot in the framing rules would re-couple the two concerns
without anyone noticing.
"""

import pathlib
import re
import unittest

from woodbuild.adapters import load_adapter

# This file lives at plugins/woodbuild/skills/woodbuild-engine/scripts/tests/, so
# parents[5] is already the plugins directory. The guard scans the whole plugins tree: a
# store name is a regression anywhere outside the homedepot plugin, and every plugin this
# migration owns must have well-formed skill dirs.
PLUGINS = pathlib.Path(__file__).resolve().parents[5]
STORE_WORDS = ("Home Depot", "homedepot.ca", "homedepot.com", "hd_search",
               "hd_product", "HD_DEFAULT_STORE", "MicroPro")
# The plugin that owns the store's knowledge. The bare skill slug is allowed anywhere;
# the store's own names are not.
STORE_OWNER = "homedepot"
# The five visible skills of the woodbuild plugin. Every one of them must name the engine
# it uses. The freecad plugin's skills use no engine; they are only scanned for store
# knowledge.
ENGINE_USERS = {"building-from-reference", "wood-framing", "sheet-and-board-nesting",
                "build-pricing", "freecad-model-to-spec"}
# The two files whose job is to name the store in order to check the seam.
STORE_NAMING_ALLOWED = {"test_boundaries.py", "test_adapters.py"}
EXPECTED_PLUGINS = {"woodbuild", "freecad", "homedepot"}
ENGINE_SKILL = PLUGINS / "woodbuild" / "skills" / "woodbuild-engine"


def skill_dirs():
    # Only the three plugins this migration owns. The repo also carries unrelated
    # pre-existing marketplace plugins whose frontmatter names are namespaced for
    # Claude Code (e.g. "ericmarcantonio:clean-code"); they are out of scope here.
    return sorted(p for plugin in EXPECTED_PLUGINS
                  for p in (PLUGINS / plugin).glob("skills/*/SKILL.md"))


def plugin_dirs():
    return {p.name for p in PLUGINS.iterdir() if p.is_dir()}


class TestStoreKnowledgeIsContained(unittest.TestCase):
    def test_the_three_plugins_exist(self):
        missing = EXPECTED_PLUGINS - plugin_dirs()
        self.assertEqual(missing, set(), "missing plugin directories: %s" % sorted(missing))

    def test_no_other_plugin_or_engine_file_names_the_store(self):
        offenders = []
        for path in PLUGINS.rglob("*"):
            if not path.is_file() or path.suffix not in (".py", ".md"):
                continue
            if STORE_OWNER in path.parts or path.name in STORE_NAMING_ALLOWED:
                continue
            text = path.read_text(errors="ignore")
            for word in STORE_WORDS:
                if word in text:
                    offenders.append("%s contains %r" % (path, word))
        self.assertEqual(offenders, [], "store knowledge escaped its plugin")

    def test_only_the_two_seam_tests_are_exempt(self):
        exempt = sorted(p.name for p in PLUGINS.rglob("*") if p.name in STORE_NAMING_ALLOWED)
        self.assertEqual(exempt, ["test_adapters.py", "test_boundaries.py"])

    def test_the_engine_has_no_tax_numbers(self):
        offenders = []
        for path in (ENGINE_SKILL / "scripts" / "woodbuild").rglob("*.py"):
            text = path.read_text(errors="ignore")
            if "TAX_RATES" in text or "tax_rate_for" in text:
                offenders.append(str(path))
        self.assertEqual(offenders, [], "the engine must not carry a tax table")

    def test_the_store_adapter_is_loadable_and_offline_safe(self):
        path = (PLUGINS / STORE_OWNER / "skills" / "homedepot-catalogue"
                / "scripts" / "homedepot_adapter.py")
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
            path = PLUGINS / "woodbuild" / "skills" / name / "SKILL.md"
            with self.subTest(skill=name):
                self.assertTrue(path.exists(), "missing skill %s" % name)
                self.assertIn("woodbuild-engine", path.read_text(),
                              "%s does not name the engine it depends on" % path)

    def test_the_unrelated_freecad_skills_are_left_out_of_the_engine_rule(self):
        for name in ("freecad-model-hygiene", "freecad-render-views"):
            path = PLUGINS / "freecad" / "skills" / name / "SKILL.md"
            self.assertTrue(path.exists())
            self.assertNotIn(name, ENGINE_USERS)


if __name__ == "__main__":
    unittest.main()
