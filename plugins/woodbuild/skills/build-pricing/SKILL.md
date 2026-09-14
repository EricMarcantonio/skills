---
name: build-pricing
description: Use when pricing a material list — turning stock classes into verified prices with provenance, deciding whether a search hit may become a price, or reporting a line as unpriced. Store-agnostic: it never names a retailer.
---

# Pricing a build

The method. Which shop answers, and how to reach it, is the store adapter's job
(`homedepot-catalogue` is one).

## The rule that matters

**A search hit is never a price.** A script may not convert a description match into
money. Only an agent's judgement, recorded with a reason, prices a class.

```bash
E=<repo>/skills/woodbuild-engine/scripts
cd <workspace>
# 1. what still needs a match, with candidates to read
python3 $E/woodbuild.py --spec spec.json --prices prices.json --out out --candidates \
  --adapter <store adapter>
# 2. judge, then record the decision and the reasoning
python3 $E/woodbuild.py --spec spec.json --prices prices.json --out out \
  --set-price 2x4 1001802962 --why "2x4x8 ft SPF standard stud" --today 2026-08-01 \
  --adapter <store adapter>
```

`--set-price` re-fetches the SKU through the store's product tool and writes the
name, url, price and your `--why` into the cache. The durable artifact is the
decision **and its justification**, not the SKU.

## Cache

`prices.json`: `store`, `storeName`, `province`, `currency`, `fetched`, `items`,
`unpriced`. Each item carries `sku`, `desc`, `price`, `url`, `source`, `fetched`,
`matched_by`, `matched_on`, `why`, and `pack` when the match recorded one.

- A cache priced for a different store than the spec is a hard error, not a merge.
- A match older than **30 days** must be re-judged, not trusted.
- A `null` price is a real answer: the line stays unpriced with that reason.

## Packs

Consumables are bought in packs. Record the pack size with the match
(`--pack "50 count"`), because a per-pack price may only price a pack, never a count
of pieces. Without a recorded pack the line stays unpriced. For consumables prefer
the **best value pack** — compare price per piece, not the first correct product.

## Reporting

Never invent a price or a pack size. Leave a class unpriced with a reason and report
it; the workbook prints every unpriced line with its reason, and the deviations table
is read before the totals for the same reason: constraints before costs.

## What this skill does not decide

- Tool names, store ids, tax rates, SKU availability — the store adapter.
- What the materials are — `building-from-reference` and `wood-framing`.
