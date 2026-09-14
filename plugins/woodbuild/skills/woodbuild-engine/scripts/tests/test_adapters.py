import os
import tempfile
import unittest

from woodbuild.adapters import AdapterError, NullAdapter, StoreAdapter, load_adapter


class TestNullAdapter(unittest.TestCase):
    def test_null_adapter_invents_nothing(self):
        a = NullAdapter()
        self.assertIsNone(a.search_tool)
        self.assertIsNone(a.product_tool)
        self.assertIsNone(a.server_path)
        self.assertIsNone(a.default_store)
        self.assertEqual(a.tax_rate("ON"), 0.0)
        self.assertEqual(a.env("7011"), {})

    def test_null_adapter_knows_search_labels_are_candidates(self):
        a = NullAdapter()
        self.assertTrue(a.is_candidate(a.source_search))
        self.assertFalse(a.is_candidate(a.source_product))
        self.assertFalse(a.is_candidate(None))


class TestLoadAdapter(unittest.TestCase):
    def _write(self, source):
        fd, path = tempfile.mkstemp(suffix="-adapter.py")
        with os.fdopen(fd, "w") as fh:
            fh.write(source)
        self.addCleanup(os.unlink, path)
        return path

    def test_loads_an_adapter_instance_from_a_file(self):
        path = self._write(
            "from woodbuild.adapters import StoreAdapter\n"
            "class A(StoreAdapter):\n"
            "    name = 'fake'\n"
            "    search_tool = 'find'\n"
            "    product_tool = 'verify'\n"
            "    source_search = 'search'\n"
            "    source_product = 'product'\n"
            "    default_store = '0001'\n"
            "    def tax_rate(self, province):\n"
            "        return 0.25\n"
            "ADAPTER = A()\n")
        a = load_adapter(path)
        self.assertEqual(a.name, "fake")
        self.assertEqual(a.search_tool, "find")
        self.assertEqual(a.tax_rate("ON"), 0.25)
        self.assertEqual(a.default_store, "0001")

    def test_a_file_without_an_adapter_is_an_error(self):
        path = self._write("x = 1\n")
        with self.assertRaises(AdapterError):
            load_adapter(path)

    def test_a_missing_file_is_an_error(self):
        with self.assertRaises(AdapterError):
            load_adapter("/nonexistent/adapter.py")

    def test_an_adapter_value_that_is_not_a_store_adapter_is_an_error(self):
        path = self._write("ADAPTER = object()\n")
        with self.assertRaises(AdapterError):
            load_adapter(path)

    def test_an_adapter_that_raises_on_import_is_an_error(self):
        path = self._write("raise RuntimeError('broken adapter import')\n")
        with self.assertRaises(AdapterError):
            load_adapter(path)

    def test_the_shipped_store_adapter_satisfies_the_protocol(self):
        import json
        import pathlib
        repo = pathlib.Path(__file__).resolve().parents[4]
        path = repo / "skills" / "homedepot-catalogue" / "scripts" / "homedepot_adapter.py"
        self.assertTrue(path.exists(), "the store adapter must exist at %s" % path)
        a = load_adapter(str(path))
        self.assertEqual(a.search_tool, "hd_search")
        self.assertEqual(a.product_tool, "hd_product")
        self.assertEqual(a.default_store, "7011")
        self.assertAlmostEqual(a.tax_rate("ON"), 0.13)
        self.assertAlmostEqual(a.tax_rate("ZZ"), 0.0)
        self.assertTrue(a.is_candidate("hd_search"))
        self.assertFalse(a.is_candidate("hd_product"))
        self.assertTrue(str(a.server_path).endswith("index.js"))
        self.assertEqual(a.env("7011"), {"HD_DEFAULT_STORE": "7011"})
        json.dumps({})          # the module must not need a config file to load

    def test_legacy_candidate_labels_come_from_the_adapter(self):
        path = self._write(
            "from woodbuild.adapters import StoreAdapter\n"
            "class A(StoreAdapter):\n"
            "    candidate_sources = ('search', 'legacy_search')\n"
            "ADAPTER = A()\n")
        a = load_adapter(path)
        self.assertTrue(a.is_candidate("legacy_search"))
        self.assertFalse(a.is_candidate("product"))


if __name__ == "__main__":
    unittest.main()
