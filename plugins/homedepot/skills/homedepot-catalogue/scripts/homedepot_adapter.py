"""Home Depot Canada: the only file in this repository that names a store.

Everything store-specific lives here: the MCP tool names, the store id, the
machine-local server path, the provincial tax table and the availability labels.
The engine takes this as data through `woodbuild.adapters.StoreAdapter`, so a
different retailer is a different file like this one and no engine change.

Pass it to the CLI:  --adapter skills/homedepot-catalogue/scripts/homedepot_adapter.py
"""

import os

from woodbuild.adapters import StoreAdapter

# 2026 rates. A rate that is not listed returns 0.0: a guessed tax is worse than
# no tax, and the CLI prints a note when it reports zero.
TAX_RATES = {"ON": 0.13, "AB": 0.05, "BC": 0.12, "QC": 0.14975, "MB": 0.12,
             "SK": 0.11, "NS": 0.15, "NB": 0.15, "NL": 0.15, "PE": 0.15}

# Machine-local clone of the Home Depot MCP server; see README for how to restore it.
DEFAULT_SERVER = os.path.expanduser(
    "~/.pi/agent/mcp-servers/mcp_homedepot/dist/index.js")

PROVINCE_ALIASES = {"ONTARIO": "ON", "ALBERTA": "AB", "BRITISH COLUMBIA": "BC",
                    "QUEBEC": "QC", "QUÉBEC": "QC", "MANITOBA": "MB",
                    "SASKATCHEWAN": "SK", "NOVA SCOTIA": "NS",
                    "NEW BRUNSWICK": "NB", "NEWFOUNDLAND": "NL",
                    "PRINCE EDWARD ISLAND": "PE"}


class HomeDepotCanada(StoreAdapter):
    name = "homedepot-ca"
    server_path = os.environ.get("HD_SERVER_PATH") or DEFAULT_SERVER
    search_tool = "hd_search"
    product_tool = "hd_product"
    source_search = "hd_search"      # kept: existing caches carry this label
    source_product = "hd_product"
    candidate_sources = ("hd_search", "search")
    default_store = "7011"           # the store the shed build was priced against

    def tax_rate(self, province):
        code = (province or "").strip().upper()
        code = PROVINCE_ALIASES.get(code, code)
        return TAX_RATES.get(code, 0.0)

    def env(self, store=None):
        store = str(store or self.default_store)
        return {"HD_DEFAULT_STORE": store}


ADAPTER = HomeDepotCanada()
