# woodbuild/pricing.py
"""Cache-first pricing. Never invents a number: a missing price is reported."""

import collections
import json
import os
import subprocess
import threading
from datetime import date

from .adapters import NullAdapter

# An agent match older than this must be re-judged, not silently trusted.
MATCH_MAX_AGE_DAYS = 30


class PriceError(Exception):
    """The cache and the spec disagree about which store the prices belong to."""


class PricingTransportError(Exception):
    """The MCP server could not answer a price lookup."""


class PriceCache:
    def __init__(self, path):
        self.path = path
        self.data = {"store": None, "storeName": None, "province": None,
                     "currency": "CAD", "fetched": None, "items": {}, "unpriced": {}}

    def load(self):
        if os.path.exists(self.path):
            with open(self.path) as fh:
                self.data = json.load(fh)
        return self.data

    def save(self):
        with open(self.path, "w") as fh:
            json.dump(self.data, fh, indent=2, sort_keys=True)
            fh.write("\n")

    # accessors
    @property
    def store(self):
        return self.data.get("store")

    @property
    def province(self):
        return self.data.get("province")

    @property
    def fetched(self):
        return self.data.get("fetched")

    @property
    def unpriced(self):
        return self.data.get("unpriced", {})

    def get(self, cls):
        return self.data.get("items", {}).get(cls)

    def put(self, cls, entry):
        self.data.setdefault("items", {})[cls] = entry

    def mark_unpriced(self, cls, reason, tried):
        self.data.setdefault("unpriced", {})[cls] = {"reason": reason, "tried": tried}

    def is_stale(self, cls, days=7, today=None):
        entry = self.get(cls)
        if not entry or not entry.get("fetched"):
            return True
        ref = date.fromisoformat(today) if today else date.today()
        got = date.fromisoformat(entry["fetched"])
        return (ref - got).days > days


class StdioMCP:
    """Minimal MCP stdio client: enough for tools/call on a store MCP server.

    Responses are matched by id, because a server notification arriving between
    request and reply is not the reply. stderr is drained on a thread so a chatty
    server cannot fill the pipe and deadlock. Protocol errors raise instead of
    looking like an empty result, which would otherwise be reported as an unpriced
    line with a misleading reason.
    """

    def __init__(self, command, args, env=None):
        self.proc = subprocess.Popen([command] + list(args), stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True, bufsize=1,
                                     env=env or os.environ.copy())
        self._id = 0
        self.stderr_lines = collections.deque(maxlen=20)
        self._drain = threading.Thread(target=self._drain_stderr, daemon=True)
        self._drain.start()
        self._send({
            "jsonrpc": "2.0", "id": self._next(), "method": "initialize",
            "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                       "clientInfo": {"name": "woodbuild", "version": "0.1.0"}}})
        self._read(self._id)
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized",
                    "params": {}})

    def _drain_stderr(self):
        try:
            for line in self.proc.stderr:
                self.stderr_lines.append(line.rstrip())
        except Exception:
            pass

    def _next(self):
        self._id += 1
        return self._id

    def _send(self, obj):
        self.proc.stdin.write(json.dumps(obj) + "\n")
        self.proc.stdin.flush()

    def _read(self, want_id=None):
        """Next message, ignoring anything that is not the reply we are waiting for."""
        while True:
            line = self.proc.stdout.readline()
            if not line:
                return None
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if want_id is not None and msg.get("id") != want_id:
                continue
            return msg

    def call(self, tool, arguments):
        rid = self._next()
        self._send({"jsonrpc": "2.0", "id": rid, "method": "tools/call",
                    "params": {"name": tool, "arguments": arguments}})
        reply = self._read(rid)
        if reply is None:
            raise PricingTransportError("%s got no reply; stderr: %s"
                                        % (tool, " | ".join(self.stderr_lines)))
        if reply.get("error"):
            raise PricingTransportError("%s failed: %s" % (tool, reply["error"]))
        content = (reply.get("result") or {}).get("content") or []
        for block in content:
            if block.get("type") == "text":
                try:
                    payload = json.loads(block["text"])
                except ValueError:
                    return {"text": block["text"]}
                if isinstance(payload, dict):
                    return payload
                if isinstance(payload, list):
                    return {"products": payload}
                return {"value": payload}
        return {}

    def close(self):
        try:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass
        for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
            try:
                stream.close()
            except Exception:
                pass


def put_matched(cache, cls, entry, why, today=None, pack=None, source="product"):
    """Record an agent's match. Requires a sku; stamps provenance.

    `pack` is the pack size the price is for, e.g. "50 count" or "295 ml". It
    travels with the match because a per-pack price may only price a pack, never
    a count of pieces. A missing pack is honestly "unknown", never guessed.
    `source` is the label the adapter calls a verified product.
    """
    if not entry or not entry.get("sku"):
        raise ValueError("an agent match needs a sku for class %r" % (cls,))
    today = today or date.today().isoformat()
    rec = dict(entry)
    rec["matched_by"] = "agent"
    rec["matched_on"] = today
    rec["why"] = why
    rec.setdefault("source", source)
    rec.setdefault("fetched", today)
    if pack:
        rec["pack"] = pack
    cache.put(cls, rec)
    cache.data.setdefault("unpriced", {}).pop(cls, None)
    return rec


def _is_agent_matched(entry):
    return bool(entry and entry.get("sku") and entry.get("matched_by") == "agent")


def needs_match(spec, cache, days=MATCH_MAX_AGE_DAYS, today=None):
    """[class] with no agent match, or one older than `days`."""
    ref = date.fromisoformat(today) if today else date.today()
    out = []
    for cls in sorted(spec.search_terms()):
        entry = cache.get(cls)
        if not _is_agent_matched(entry):
            out.append(cls)
            continue
        raw = entry.get("matched_on")
        if not raw or (ref - date.fromisoformat(raw)).days > days:
            out.append(cls)
    return out


def _adapter(adapter):
    return adapter if adapter is not None else NullAdapter()


def candidates(spec, transport, adapter=None, classes=None):
    """{class: [{sku, name, price, url}]} from the adapter's search tool.

    A search hit is a candidate, never a price: this never touches the cache.
    """
    adapter = _adapter(adapter)
    terms = spec.search_terms()
    chosen = sorted(terms) if classes is None else list(classes)
    store = spec.data.get("pricing", {}).get("store") or adapter.default_store
    out = {}
    for cls in chosen:
        query = terms.get(cls)
        if not query or not adapter.search_tool:
            continue
        try:
            payload = transport.call(adapter.search_tool,
                                     {"query": query, "storeId": store, "pageSize": 5})
        except PricingTransportError:
            out[cls] = []
            continue
        out[cls] = [{"sku": p.get("sku"), "name": p.get("name"),
                     "price": p.get("price"), "url": p.get("url")}
                    for p in ((payload or {}).get("products") or [])
                    if p.get("sku")]
    return out


def set_price(cache, cls, sku, why, transport, adapter=None, store=None, today=None,
              pack=None):
    """Verify the SKU with the adapter's product tool, then record the match.

    `store` must come from the spec: a cache that has never been written has no
    store of its own, and querying a national id would record a price that later
    gets labelled with the spec's store. `adapter.default_store` is for search
    candidates only (see `candidates`), never for pricing a class.
    """
    adapter = _adapter(adapter)
    today = today or date.today().isoformat()
    store_id = str(store or cache.store or "")
    if not store_id:
        raise PriceError("set_price needs a store: pass the spec's store")
    payload = transport.call(adapter.product_tool, {"sku": sku, "storeId": store_id})
    if not payload or payload.get("price") is None:
        raise PricingTransportError("%s returned no price for sku %s"
                                    % (adapter.product_tool, sku))
    entry = {"sku": sku, "desc": payload.get("name"),
             "price": float(payload["price"]), "url": payload.get("url"),
             "source": adapter.source_product, "fetched": today}
    return put_matched(cache, cls, entry, why, today=today, pack=pack,
                       source=adapter.source_product)


def resolve(spec, cache, transport=None, adapter=None, refresh=False, today=None):
    """Return {stock class: price entry} for agent-matched classes only.

    A script may never accept a search hit as a price: an unmatched class stays
    `unpriced` with reason 'not agent-matched'. With a transport, refresh
    re-verifies the price of an already-matched sku; a stale match is a
    re-matching prompt, never silent trust. A cache priced for a different store
    than the spec is a hard error. With no store id anywhere, a stale class is
    marked unpriced rather than queried against a guessed store.
    """
    adapter = _adapter(adapter)
    today = today or date.today().isoformat()
    cache.load()                 # a cache handed in cold reads its file first
    want_store = spec.data.get("pricing", {}).get("store")
    want_prov = spec.data.get("pricing", {}).get("province")
    if cache.store and want_store and str(cache.store) != str(want_store):
        raise PriceError("price cache is for store %s but the spec says store %s; "
                         "re-point the spec or delete the cache" % (cache.store, want_store))
    if cache.province and want_prov and cache.province != want_prov:
        raise PriceError("price cache is %s but the spec says %s"
                         % (cache.province, want_prov))
    if want_store and not cache.data.get("store"):
        cache.data["store"] = want_store
    if want_prov and not cache.data.get("province"):
        cache.data["province"] = want_prov

    terms = spec.search_terms()
    unpriced = cache.data.setdefault("unpriced", {})
    result = {}
    for cls in terms:
        entry = cache.get(cls)
        if not _is_agent_matched(entry):
            cache.mark_unpriced(cls, "not agent-matched", [])
            continue
        if refresh and transport is not None and cache.is_stale(cls, days=7, today=today):
            store_id = str(cache.store or "")
            if not store_id:
                cache.mark_unpriced(cls, "no store configured for a refresh", [])
                continue
            try:
                payload = transport.call(adapter.product_tool,
                                         {"sku": entry["sku"], "storeId": store_id})
            except PricingTransportError as exc:
                cache.mark_unpriced(cls, "transport error: %s" % exc,
                                    [adapter.product_tool])
                continue
            price = (payload or {}).get("price")
            if price is None:
                cache.mark_unpriced(cls, "null price returned", [adapter.product_tool])
                continue
            entry = dict(entry)
            entry.update({"price": float(price),
                          "desc": payload.get("name", entry.get("desc")),
                          "url": payload.get("url", entry.get("url")),
                          "source": adapter.source_product, "fetched": today})
            cache.put(cls, entry)
        unpriced.pop(cls, None)
        result[cls] = entry

    if not terms:                # a spec with no search terms prices every match
        result = {cls: e for cls, e in cache.data.get("items", {}).items()
                  if _is_agent_matched(e)}
    cache.data["fetched"] = today
    return {cls: e for cls, e in result.items() if cls in terms or not terms}


def compare(old, new):
    """Price deltas, sorted by class. Returns [(class, old, new, delta)]."""
    out = []
    for cls in sorted(set(old.get("items", {})) | set(new.get("items", {}))):
        a = (old.get("items", {}).get(cls) or {}).get("price")
        b = (new.get("items", {}).get(cls) or {}).get("price")
        if a is None and b is None:
            continue
        if a != b:
            out.append((cls, a, b, round((b or 0) - (a or 0), 2)))
    return out
