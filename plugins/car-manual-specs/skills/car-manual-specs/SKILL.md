---
name: car-manual-specs
description: Extract and permanently save key maintenance and torque specs from a car service manual PDF. Use this skill whenever the user has a service manual PDF (factory service manual, Haynes, Chilton, ALLDATA, etc.) and wants to pull out specs like oil capacity, torque values, lug nut torque, brake specs, or suspension torques. Trigger any time someone says "extract specs from this manual", "save the torque specs", "get the oil capacity from the PDF", "look up torque in the service manual", "I downloaded a car manual and want to get the specs", or describes wanting to build a reference from a vehicle's PDF documentation. Works for any make, model, and year.
---

# Car Manual Spec Extractor

Extract key maintenance specs from a service manual PDF and save them for future reference. The goal is a persistent spec file at `~/.claude/car-specs/<year>-<make>-<model>.md` that any future Claude session can read without re-searching the PDF.

## Standard Target Specs

Extract all of these (report "not found" if not locatable after reasonable effort):

**Engine / Maintenance**
- Oil capacity with filter change (liters and quarts)
- Oil pan drain plug torque
- Spark plug torque

**Wheels**
- Lug nut / wheel nut torque

**Rear Brakes**
- Caliper bracket bolt torque (large mounting bolts, bracket to knuckle)
- Caliper slide pin / lock pin bolt torque

**Rear Suspension**
- Wheel hub bearing bolt torque (hub component to hub support/knuckle)
- Shock absorber upper mount torque (body side)
- Shock absorber lower mount torque (knuckle side)

Add any additional specs the user requests beyond these defaults.

---

## Step 1: Verify Dependencies and PDF Info

```bash
# Check tools
which pdftotext pdftoppm pdfinfo || echo "Missing: brew install poppler"

# PDF metadata
pdfinfo "<pdf_path>"
```

Note the page count — it affects how you interpret later results.

---

## Step 2: Extract All Text

```bash
pdftotext "<pdf_path>" /tmp/manual_text.txt
wc -l /tmp/manual_text.txt
```

If the result is fewer than ~500 lines for a multi-hundred-page manual, it's a scanned/image-only PDF — skip to Step 4 for all specs.

---

## Step 3: Search Extracted Text

Torque values appear in several formats depending on the publisher:
- `XX—XX N·m {X.X—X.X kgf·m, XX—XX ft·lbf}` — OEM factory manuals (Mazda, Toyota, Honda)
- `XX Nm` / `XX N.m` / `XX ft-lb` / `XX ft·lbf` — Haynes/Chilton
- Table rows with a spec name and value — ALLDATA/Mitchell

### Search commands

```bash
# Oil capacity
grep -n -i "oil.*capacity\|with filter\|w\/filter\|engine oil.*liter\|engine oil.*qt\|oil.*quart\|filling.*capacity" /tmp/manual_text.txt | head -30

# Oil pan / drain plug
grep -n -i "oil pan\|drain plug\|sump bolt\|oil pan.*bolt" /tmp/manual_text.txt | head -20

# Lug nut
grep -n -i "lug nut\|wheel nut\|wheel bolt\|hub nut\|wheel.*torque" /tmp/manual_text.txt | head -20

# Spark plug
grep -n -i "spark plug" /tmp/manual_text.txt | head -20

# Rear hub bearing
grep -n -i "hub.*bolt\|wheel hub\|hub.*support\|hub.*component\|hub.*bearing\|bearing.*hub" /tmp/manual_text.txt | head -20

# Caliper bracket
grep -n -i "caliper.*bracket\|mounting.*caliper\|caliper.*mount\|brake.*bracket" /tmp/manual_text.txt | head -20

# Slide pin
grep -n -i "slide pin\|lock pin\|guide pin\|caliper.*pin" /tmp/manual_text.txt | head -20

# Shock absorber
grep -n -i "shock absorb\|strut.*mount\|damper.*mount\|shock.*upper\|shock.*lower" /tmp/manual_text.txt | head -20

# Torque spec tables (broad sweep)
grep -n "N·m\|N\.m\|ft.lb\|kgf" /tmp/manual_text.txt | head -50
```

For each hit, read ±20 surrounding lines for context and the actual value.

### Estimating PDF page numbers from text position

`pdftotext` uses form-feed characters (`\f`) as page breaks. Count form-feeds before a line to estimate the PDF page — but this is imprecise, especially in manuals with blank pages or non-standard layouts. Treat it as a rough starting point only; verify by rendering.

```bash
head -n <LINE_NUMBER> /tmp/manual_text.txt | grep -c $'\f'
```

---

## Step 4: Image Rendering (for diagram-embedded values)

Factory service manuals embed most torque specs as callouts on exploded-view diagrams. When text search fails or returns no value, render the relevant section pages visually.

### Locate the right section

```bash
# Find section headers to estimate page ranges
grep -n -i "REAR BRAKE\|REAR SUSPENSION\|WHEEL HUB\|SHOCK ABSORBER\|LUBRICATION SYSTEM\|OIL AND FILTER\|SPARK PLUG\|WHEEL AND TIRE" /tmp/manual_text.txt | head -40
```

Use the form-feed count as a starting estimate, then scan a ±30-page window around it.

### Render pages

```bash
# Single page
pdftoppm -r 220 -f <PAGE> -l <PAGE> "<pdf_path>" /tmp/manual_page

# Range (e.g., pages 100-105)
pdftoppm -r 220 -f 100 -l 105 "<pdf_path>" /tmp/manual_pages
```

### Convert PPM to JPEG (macOS — sips is built-in)

```bash
# Single file
sips -s format jpeg /tmp/manual_page-001.ppm --out /tmp/manual_page-001.jpg

# Batch
for f in /tmp/manual_pages-*.ppm; do
  sips -s format jpeg "$f" --out "${f%.ppm}.jpg"
done
```

Then use the Read tool to view the JPEG files visually.

### Resolution guide

| DPI | Use case |
|-----|----------|
| 150 | Quick scan to find the right page |
| 220 | Default — readable torque callouts |
| 300 | Small diagram text or unclear values |
| 400 | Scanned/low-quality PDFs |

### Reading diagram callouts

Exploded-view diagrams number components (1, 2, 3…) with torque values listed separately as arrows or text near each item. Match callout numbers to part names in the parts list on the same page. If a torque value has no obvious arrow target, it's the only unassigned value — likely the primary component being removed/installed.

**OEM duplicate sections**: Factory manuals for global markets often duplicate entire sections for LHD (left-hand drive) and RHD (right-hand drive). The torque values are identical — you only need one.

---

## Step 5: Save Results

Create `~/.claude/car-specs/<year>-<make>-<model>.md`:

```markdown
# <Year> <Make> <Model> — Key Specs
Source: <PDF filename>
Extracted: <date>
Engine: <displacement, e.g., 2.5L 4-cylinder>

## Engine / Maintenance
- Oil capacity (with filter): X.X L / X.X qt
- Oil pan drain plug torque: XX—XX Nm (XX—XX ft·lbf) [pg. XXXX]
- Spark plug torque: XX—XX Nm (XX—XX ft·lbf) [pg. XXXX]

## Wheels
- Lug nut torque: XX—XX Nm (XX—XX ft·lbf) [pg. XXXX]

## Rear Brakes
- Caliper bracket bolt torque: XX—XX Nm (XX—XX ft·lbf) [pg. XXXX]
- Caliper slide pin bolt torque: XX—XX Nm (XX—XX ft·lbf) [pg. XXXX]

## Rear Suspension
- Wheel hub bearing bolt torque: XX—XX Nm (XX—XX ft·lbf) [pg. XXXX] ⚠ see notes if uncertain
- Shock absorber upper mount torque: XX—XX Nm (XX—XX ft·lbf) [pg. XXXX]
- Shock absorber lower mount torque: XX—XX Nm (XX—XX ft·lbf) [pg. XXXX]

## Notes
- <Caveats, alternate values, diagram-only specs, or context about conflicting values>
```

Use `⚠` to flag values that were inferred (e.g., only unassigned callout in diagram) rather than explicitly labeled.

---

## Step 6: Report to User

Present all found specs in a clean table with:
- Value in both Nm and ft·lbf
- Source page number
- PDF filename
- Brief quote or context for verification

For anything not found after a thorough search, say so explicitly: "Not found — likely embedded in a diagram page I couldn't locate" or "Not applicable for this vehicle (e.g., no rear disc brakes)."

---

## Format Reference

| Publisher | Torque format | Oil capacity format |
|-----------|--------------|-------------------|
| Mazda OEM | `XX—XX N·m {X.X—X.X kgf·m, XX—XX ft·lbf}` | `X.X L {X.X US qt, X.X lmp qt}` |
| Toyota OEM | `XX N·m (XX kgf·cm, XX ft·lbf)` | Listed in "Lubricant" table |
| Honda OEM | `X.X N·m (X.X kgf·cm, X in·lbf)` | "Engine oil capacity" table |
| Haynes | `XX Nm (XX ft lb)` | Simple table near front |
| Chilton | `XX ft. lbs.` | "Fluid capacities" section |
