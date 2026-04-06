---
name: marketplace-listing
description: Create optimized Facebook Marketplace (or Kijiji/Craigslist) listings for items the user wants to sell. Use this skill whenever the user wants to sell something, post an item, create a listing, write an ad, or asks "help me sell my X". This includes cars, car parts, tires, rims, electronics, furniture, tools, or any physical item. The skill researches the item's retail value, finds accurate specs, and produces a clean, buyer-friendly listing with retail price references and source links. Always use this skill even if the user just describes an item casually — don't make them ask twice.
---

# Marketplace Listing Skill

Produces a complete, accurate, buyer-optimized listing for Facebook Marketplace (or other platforms) based on what the user tells you about their item.

---

## Step 1 — Gather Item Details

Extract from the conversation (or ask if missing):

- **What is the item?** (brand, model, part number, size, specs)
- **Condition?** (km driven, hours used, age, visible damage, box/accessories included)
- **Why selling?** (optional but humanizes the listing — "too big for my vehicle", "upgraded", "no longer needed")
- **Platform?** Facebook Marketplace, Kijiji, Craigslist, etc. (default: Facebook Marketplace)
- **Location?** (city/region for the listing footer)
- **Selling as a set or individually?**
- **Any fitment or compatibility details?** (bolt pattern, vehicle year/make/model, size constraints)

Do NOT ask multiple questions at once. If the user has already provided details in the conversation, extract them — don't re-ask.

---

## Step 2 — Research the Item

Use `web_search` to find:

1. **Retail price** — search "[brand] [model] [specs] price Canada" or "price CAD". Find a reputable Canadian retailer (canadawheels.ca, 1010tires.com, bestbuy.ca, canadiantire.ca, etc.). Note the price per unit AND for a set if applicable.

2. **Key specs and features** — search "[brand] [model] specs features". Pull:
   - Official spec sheet details
   - Notable selling points (warranty, certifications, performance claims)
   - Any compatibility or fitment information

3. **Compatibility list** (if applicable to wheels, tires, electronics, accessories) — search "compatible vehicles/devices for [spec/model]". For wheels/tires, always look up the bolt pattern compatibility list.

4. **Source links** — save the exact URLs of the retailer pages you find prices on. These go into the listing.

Be thorough. A well-researched listing sells faster and builds buyer trust.

---

## Step 3 — Write the Listing

### Formatting rules
- **No emojis** (unless user explicitly asks for them)
- **No mention of the specific vehicle/device it came from** unless the user wants it included — this limits the buyer pool. Instead, lead with broad compatibility.
- Use plain dashes for bullet points
- ALL CAPS for section headers
- Keep the tone factual and confident, not salesy

### Structure

```
[TITLE LINE — concise, spec-forward, condition]

[1-2 sentence intro: what it is, condition, why selling if helpful]

FITMENT / COMPATIBILITY  ← (only if applicable, e.g. wheels, tires, accessories)
[List of compatible makes/models/devices, organized by brand]
[Always include a disclaimer: "Bolt pattern alone does not guarantee fitment. Verify offset, center bore, and size for your specific vehicle."]

[ITEM TYPE] SPECS
- Key spec 1
- Key spec 2
- ...
- Retail: $X CAD each / $X for a set of [N]
  ([Retailer name]: [URL])

CONDITION
- [condition details, km/hours, what's included]

[Optional second item specs block if selling a bundle]

Combined retail value (before tax/mounting/etc.): ~$X CAD  ← (only for bundles)

Selling as [set of N / individually]. [Splitting or not.]

Location: [City, Province]
Price: [YOUR PRICE HERE]
Cash or e-Transfer
```

---

## Step 4 — Pricing Guidance

After delivering the listing, give the user a suggested price range based on:

- Combined retail value of items
- Condition (near-new = 60–75% of retail; used = 40–60%; heavily worn = 20–40%)
- Market context (in-demand items hold value better)

Example: "Retail is ~$2,240. For under 7,000 km of use, $1,300–$1,600 is a strong asking price — meaningful discount for buyers while reflecting the near-new condition."

---

## Step 5 — Offer Refinements

After delivering the listing, offer to:
- Add or remove the seller's vehicle/device reference
- Adjust tone (more casual, more technical)
- Add/remove emojis
- Swap platform format (Kijiji vs Facebook vs Craigslist)
- Update price once the user decides on one

---

## Key Principles

**Lead with compatibility, not origin.** Saying "fits Nissan, Honda, Toyota, Mazda, Hyundai, Kia, Ford Mustang..." sells more wheels than "came off my RAV4." Same applies to electronics, furniture, tools — lead with what it works with or what it does, not where it's been.

**Always include retail refs with links.** Buyers trust listings that show what something costs new. It justifies the asking price and signals the seller knows what they have.

**Fitment disclaimer is mandatory for wheels/tires/electronics accessories.** Bolt pattern, offset, center bore, and tire size must all be verified by the buyer. Say this clearly.

**Don't split unless asked.** Default to "selling as a complete set" for multi-piece items (tire+rim packages, matching sets, etc.).

**Keep specs accurate.** Don't paraphrase specs in a way that could mislead — use exact numbers from the manufacturer or retailer page.
