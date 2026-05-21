# car-manual-specs

Extracts and saves key maintenance and torque specs from any car service manual PDF.

## Overview

This plugin gives Claude a structured workflow for pulling torque specs and maintenance data out of factory service manuals (FSM), Haynes, Chilton, ALLDATA, or any other PDF format. Results are saved to `~/.claude/car-specs/<year>-<make>-<model>.md` so future sessions can reference them without re-searching the PDF.

Developed from real-world extraction of a 13,696-page Mazda 6 GH factory service manual, including techniques for handling OEM diagram-embedded callouts, LHD/RHD duplicate sections, and scanned PDFs.

## Installation

```
/plugin install EricMarcantonio/skills/plugins/car-manual-specs
```

## Default Specs Extracted

| Category | Specs |
|----------|-------|
| Engine | Oil capacity (with filter), oil pan drain plug torque, spark plug torque |
| Wheels | Lug nut torque |
| Rear Brakes | Caliper bracket bolt torque, caliper slide pin torque |
| Rear Suspension | Wheel hub bearing bolt torque, shock absorber upper mount, shock absorber lower mount |

## Core Techniques

- `pdftotext` for full text extraction with grep-based search
- `pdftoppm` + `sips` (macOS) to rasterize and visually read diagram pages
- Form-feed counting to estimate PDF page numbers from text positions
- Pattern matching for OEM (`N·m {kgf·m, ft·lbf}`), Haynes, Chilton, and ALLDATA torque formats

## Works With

- OEM factory service manuals (Mazda, Toyota, Honda, Ford, GM, etc.)
- Haynes and Chilton repair manuals
- ALLDATA / Mitchell exports
- Scanned PDFs (falls back to image rendering)

## Requirements

- `poppler` for `pdftotext` and `pdftoppm` (`brew install poppler` on macOS)
- `sips` for PPM→JPEG conversion (built into macOS)

## Related Plugins

Check the [marketplace](../../README.md) for other available plugins.
