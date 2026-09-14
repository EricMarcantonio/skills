import json
import os
import shutil
import tempfile
import unittest

from woodbuild import cli_main

try:                                    # `python3 -m unittest tests.test_cli`
    from tests.woodbuild_spec_fixture import SPEC
except ImportError:                     # discovered with tests/ itself on the path
    from woodbuild_spec_fixture import SPEC  # type: ignore


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.spec_path = os.path.join(self.dir, "spec.json")
        with open(self.spec_path, "w") as fh:
            json.dump(SPEC, fh)
        self.prices = os.path.join(self.dir, "prices.json")
        with open(self.prices, "w") as fh:
            json.dump({"store": "7011", "province": "ON", "fetched": "2026-09-12",
                       "items": {"2x4": {"price": 4.25, "sku": "222",
                                         "source": "search"}}}, fh)
        self.adapter = os.path.join(self.dir, "adapter.py")
        with open(self.adapter, "w") as fh:
            fh.write(ADAPTER_PY)
        self.out = os.path.join(self.dir, "out")

    def tearDown(self):
        shutil.rmtree(self.dir)

    def test_run_produces_workbook_and_reports_numbers(self):
        rc = cli_main(["--spec", self.spec_path, "--prices", self.prices,
                       "--out", self.out, "--today", "2026-09-12"])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(os.path.join(self.out, "budget.html")))
        self.assertTrue(os.path.exists(os.path.join(self.out, "cart.csv")))

    def test_invalid_spec_returns_two(self):
        bad = json.loads(json.dumps(SPEC))
        bad["roof"]["build_up"] = 171.0
        with open(self.spec_path, "w") as fh:
            json.dump(bad, fh)
        rc = cli_main(["--spec", self.spec_path, "--prices", self.prices,
                       "--out", self.out])
        self.assertEqual(rc, 2)

    def test_missing_prices_file_is_offline_but_not_fatal(self):
        rc = cli_main(["--spec", self.spec_path, "--prices", self.prices + ".nope",
                       "--out", self.out, "--today", "2026-09-12"])
        self.assertEqual(rc, 0)
        self.assertIn("unpriced", open(os.path.join(self.out, "budget.html")).read())

    def test_compare_prints_delta(self):
        old = os.path.join(self.dir, "old.json")
        with open(old, "w") as fh:
            json.dump({"items": {"2x4": {"price": 3.99}}}, fh)
        rc = cli_main(["--spec", self.spec_path, "--prices", self.prices,
                       "--out", self.out, "--compare", old, "--today", "2026-09-12"])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(os.path.join(self.out, "price-deltas.txt")))

    def _stub_server(self):
        import sys
        path = os.path.join(self.dir, "stub-mcp.py")
        with open(path, "w") as fh:
            fh.write(self.STUB_MCP)
        return path

    def test_set_price_mode_records_a_verified_match(self):
        server = self._stub_server()
        rc = cli_main(["--spec", self.spec_path, "--prices", self.prices, "--out", self.out,
                       "--server", server, "--adapter", self.adapter,
                       "--set-price", "2x4", "1000123456",
                       "--why", "the 8 ft SPF stud", "--today", "2026-09-12"])
        self.assertEqual(rc, 0)
        entry = json.load(open(self.prices))["items"]["2x4"]
        self.assertEqual(entry["sku"], "1000123456")
        self.assertEqual(entry["matched_by"], "agent")

    def test_set_price_records_the_pack_size(self):
        server = self._stub_server()
        rc = cli_main(["--spec", self.spec_path, "--prices", self.prices, "--out", self.out,
                       "--server", server, "--adapter", self.adapter,
                       "--set-price", "2x4", "1000123456",
                       "--pack", "1000 count", "--why", "the bulk stud box",
                       "--today", "2026-09-12"])
        self.assertEqual(rc, 0)
        entry = json.load(open(self.prices))["items"]["2x4"]
        self.assertEqual(entry["pack"], "1000 count")

    def test_candidates_mode_lists_what_needs_matching(self):
        server = self._stub_server()
        rc = cli_main(["--spec", self.spec_path, "--prices", self.prices, "--out", self.out,
                       "--server", server, "--adapter", self.adapter,
                       "--candidates", "--today", "2026-09-12"])
        self.assertEqual(rc, 0)
        data = json.load(open(os.path.join(self.out, "candidates.json")))
        self.assertIn("2x4", data)
        self.assertEqual(data["2x4"][0]["sku"], "1000123456")

    def test_offline_run_without_an_adapter_reports_zero_tax(self):
        rc = cli_main(["--spec", self.spec_path, "--prices", self.prices,
                       "--out", self.out, "--today", "2026-09-12"])
        self.assertEqual(rc, 0)
        html = open(os.path.join(self.out, "budget.html")).read()
        self.assertIn("tax 0.0%", html)

    def test_adapter_supplies_the_tax_rate(self):
        rc = cli_main(["--spec", self.spec_path, "--prices", self.prices,
                       "--out", self.out, "--adapter", self.adapter,
                       "--today", "2026-09-12"])
        self.assertEqual(rc, 0)
        html = open(os.path.join(self.out, "budget.html")).read()
        self.assertIn("tax 25.0%", html)   # the test adapter declares a 25% rate

    STUB_MCP = '''
import json, sys
def send(o):
    sys.stdout.write(json.dumps(o) + "\\n"); sys.stdout.flush()
for line in sys.stdin:
    msg = json.loads(line)
    if msg.get("method") == "initialize":
        send({"jsonrpc": "2.0", "id": msg["id"], "result": {"serverInfo": {"name": "stub"}}})
    elif msg.get("method") == "tools/call":
        name = msg["params"]["name"]
        if name == "verify":
            text = json.dumps({"sku": msg["params"]["arguments"]["sku"],
                               "name": "2x4x8 SPF Stud", "price": 4.25,
                               "url": "https://example/x"})
        else:
            text = json.dumps({"products": [{"sku": "1000123456", "name": "2x4x8 SPF Stud",
                                             "price": 4.25, "url": "https://example/x"}]})
        send({"jsonrpc": "2.0", "id": msg["id"], "result": {"content": [{"type": "text", "text": text}]}})
'''

ADAPTER_PY = '''
from woodbuild.adapters import StoreAdapter

class A(StoreAdapter):
    name = "test-store"
    search_tool = "find"
    product_tool = "verify"
    source_search = "search"
    source_product = "product"
    default_store = "7011"
    server_path = None

    def tax_rate(self, province):
        return 0.25

ADAPTER = A()
'''


if __name__ == "__main__":
    unittest.main()
