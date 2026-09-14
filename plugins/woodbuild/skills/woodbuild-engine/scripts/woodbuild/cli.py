"""woodbuild CLI: build spec in, workbook + CSVs out."""

import argparse
import os
import sys

from . import adapters, bom, frame, optimise, pricing, report, stock
from .optimise import NestError
from .spec import BuildSpec, SpecError


def _build_transport(server, adapter, spec, cache):
    """The MCP stdio client, or None when this run needs no lookups."""
    server = server or getattr(adapter, "server_path", None)
    if not server or not os.path.exists(server):
        return None, server
    store = str(spec.data.get("pricing", {}).get("store")
                or cache.store or adapter.default_store or "")
    env = dict(os.environ, **(adapter.env(store) if store else {}))
    if server.endswith(".py"):
        command, server_args = sys.executable, [server]
    else:
        command, server_args = "node", [server]
    return pricing.StdioMCP(command, server_args, env=env), server


def cli_main(argv=None):
    ap = argparse.ArgumentParser(prog="woodbuild")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--prices", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--fetch", action="store_true",
                    help="refresh missing/stale prices over MCP stdio")
    ap.add_argument("--candidates", action="store_true",
                    help="write search candidates for every class needing an agent match")
    ap.add_argument("--set-price", nargs=2, metavar=("CLASS", "SKU"),
                    help="verify an agent-chosen SKU over MCP and record the match")
    ap.add_argument("--pack", default=None, metavar="TEXT",
                    help="pack size the matched price is for, e.g. '50 count' or '295 ml'")
    ap.add_argument("--why", default=None, help="why the agent chose that product")
    ap.add_argument("--compare", help="old prices.json to diff against")
    ap.add_argument("--today", default=None)
    ap.add_argument("--server", default=None,
                    help="MCP server entry point; defaults to the adapter's server_path")
    ap.add_argument("--adapter", default=None,
                    help="python file defining an ADAPTER StoreAdapter instance")
    args = ap.parse_args(argv)

    try:
        spec = BuildSpec.load(args.spec)
        spec.validate()
    except SpecError as exc:
        print("spec error: %s" % exc, file=sys.stderr)
        return 2

    cache = pricing.PriceCache(args.prices)
    cache.load()
    try:
        adapter = adapters.load_adapter(args.adapter) if args.adapter else adapters.NullAdapter()
    except adapters.AdapterError as exc:
        print("adapter error: %s" % exc, file=sys.stderr)
        return 2
    province = (spec.data.get("pricing", {}).get("province")
                or cache.data.get("province") or "")
    tax_rate = adapter.tax_rate(province)
    uses_transport = args.fetch or args.candidates or args.set_price
    transport, server_path = _build_transport(args.server, adapter, spec, cache) \
        if uses_transport else (None, None)
    if uses_transport and transport is None:
        print("pricing error: no MCP server; pass --server or use an adapter with "
              "server_path (looked at %s)" % (args.server or adapter.server_path),
              file=sys.stderr)
        return 2
    try:
        if args.set_price:
            cls, sku = args.set_price
            if cls not in spec.search_terms():
                print("warning: %s is not in the spec's pricing.search map, so it "
                      "will never appear in a budget" % cls, file=sys.stderr)
            try:
                pricing.set_price(cache, cls, sku, args.why or "", transport,
                                  adapter=adapter,
                                  store=spec.data.get("pricing", {}).get("store"),
                                  today=args.today, pack=args.pack)
            except (pricing.PriceError, pricing.PricingTransportError) as exc:
                print("pricing error: %s" % exc, file=sys.stderr)
                return 2
            cache.save()
            entry = cache.get(cls)
            print("agent-matched %s -> %s %s ($%.2f)%s" %
                  (cls, entry.get("sku"), entry.get("desc") or "", entry.get("price") or 0.0,
                   " [%s]" % entry["pack"] if entry.get("pack") else ""))
            return 0
        if args.candidates:
            pending = pricing.needs_match(spec, cache, today=args.today)
            found = pricing.candidates(spec, transport, adapter=adapter, classes=pending)
            if not os.path.isdir(args.out):
                os.makedirs(args.out)
            path = os.path.join(args.out, "candidates.json")
            import json
            with open(path, "w") as fh:
                json.dump(found, fh, indent=2, sort_keys=True)
                fh.write("\n")
            print("%d class(es) need an agent match; candidates written to %s"
                  % (len(pending), path))
            return 0
        prices = pricing.resolve(spec, cache, transport=transport, adapter=adapter,
                                 refresh=args.fetch, today=args.today)
    except pricing.PriceError as exc:
        print("pricing error: %s" % exc, file=sys.stderr)
        return 2
    finally:
        if transport:
            transport.close()
    cache.save()

    parts = frame.derive(spec)
    # the two optimisers each reject foreign stock classes, so partition first
    sheet_parts = [p for p in parts if stock.is_sheet(p.stock)]
    board_parts = [p for p in parts if not stock.is_sheet(p.stock)]
    try:
        sheet_plans, unplaced_sheets = optimise.pack_sheets(sheet_parts)
        board_plans, unplaced_boards = optimise.cut_boards(board_parts, prices=prices)
    except NestError as exc:
        print("nesting error: %s" % exc, file=sys.stderr)
        return 3
    unplaced = unplaced_sheets + unplaced_boards
    if unplaced:
        for p in unplaced:
            print("unplaced: %s (%s)" % (p.id, p.stock), file=sys.stderr)
        return 3

    lines = bom.build_bom(parts, sheet_plans, board_plans, prices=prices, spec=spec.data)
    paths = report.write_report(spec, parts, sheet_plans, board_plans, lines, cache,
                                args.out, adapter=adapter, tax_rate=tax_rate,
                                today=args.today)

    t = bom.totals(lines, tax_rate)
    if tax_rate == 0.0:
        print("note: tax reported as 0.0%; no store rate applied",
              file=sys.stderr)
    print("%s: %d parts, %d sheet plan(s), %d board plan(s)" %
          (spec.data.get("build"), len(parts), len(sheet_plans), len(board_plans)))
    print("subtotal $%.2f + tax $%.2f = $%.2f (%d lines, %d unpriced, tax rate %.3f)" %
          (t["subtotal"], t["tax"], t["total"], t["lines"], t["unpriced"], tax_rate))
    pending = pricing.needs_match(spec, cache, today=args.today)
    print("agent-matched: %d, unmatched: %d" %
          (len(spec.search_terms()) - len(pending), len(pending)))
    matched = sum(1 for l in lines if adapter.is_candidate(l.source))
    if matched:
        print("unverified description-matched lines: %d (verify SKUs before ordering)"
              % matched)
    for key in ("html", "cutlist", "cart", "sku_qty"):
        print("  %s" % paths[key])

    if args.compare and os.path.exists(args.compare):
        import json
        with open(args.compare) as fh:
            old = json.load(fh)
        deltas = pricing.compare(old, cache.data)
        out = os.path.join(args.out, "price-deltas.txt")
        with open(out, "w") as fh:
            for cls, a, b, d in deltas:
                fh.write("%s %s -> %s (%+.2f)\n" % (cls, a, b, d))
        print("  %s (%d changes)" % (out, len(deltas)))
    return 0
