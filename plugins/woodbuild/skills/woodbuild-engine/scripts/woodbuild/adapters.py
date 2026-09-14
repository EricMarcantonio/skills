"""Store adapter: the only seam between the engine and a shop.

The engine names no store, no MCP tool, no store id and no tax rate. An adapter
supplies all four. `homedepot-catalogue` ships the only real adapter; the tests
ship fakes. With no adapter the engine prices from the cache alone and taxes at
zero, which is the honest answer rather than a guessed store.
"""

import importlib.util
import os


class AdapterError(Exception):
    """A store adapter could not be loaded or does not look like one."""


class StoreAdapter:
    """What a store must supply. Subclass it; no registration is needed."""

    name = "none"
    server_path = None          # entry point for the MCP stdio server, or None
    search_tool = None          # MCP tool used for candidate search
    product_tool = None         # MCP tool used to verify a chosen sku
    source_search = "search"    # label written for a search hit
    source_product = "product"  # label written for a verified product
    candidate_sources = ("search",)   # labels meaning "not yet verified"
    default_store = None

    def tax_rate(self, province):
        """Tax rate for a province code, or 0.0 when the store has no answer."""
        return 0.0

    def env(self, store=None):
        """Extra environment for the MCP subprocess."""
        return {}

    def is_candidate(self, source):
        """True when a price line's source means it still needs verifying."""
        return source in self.candidate_sources


class NullAdapter(StoreAdapter):
    """No store: cached agent-matched prices only, tax 0.0, no lookups."""


def load_adapter(path):
    """Load the `ADAPTER` instance from a python file. Raise AdapterError."""
    if not path or not os.path.exists(path):
        raise AdapterError("adapter file not found: %s" % path)
    spec = importlib.util.spec_from_file_location("woodbuild_adapter", path)
    if spec is None or spec.loader is None:
        raise AdapterError("adapter file is not importable: %s" % path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:                      # a broken adapter is not a store
        raise AdapterError("adapter %s failed to import: %s" % (path, exc))
    adapter = getattr(module, "ADAPTER", None)
    if adapter is None:
        raise AdapterError("adapter %s defines no ADAPTER" % path)
    if not isinstance(adapter, StoreAdapter):
        raise AdapterError("adapter %s is not a StoreAdapter" % path)
    return adapter
