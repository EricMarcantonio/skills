---
name: create-presentation
description: Create a fully animated, narrated video presentation for any project, topic, or idea. Use this skill whenever the user wants to present a project, demo an app, create a slide deck, make a video walkthrough, pitch an idea, or needs a presentation for a class, client, or conference. Triggers on phrases like "make a presentation", "create slides", "build a video presentation", "I need to present my project", "record a demo", or any request to showcase work visually. Always invoke this skill proactively when a user is preparing to demo or present anything.
---

# Presentation Creation Skill

Build animated, narrated video presentations using **Remotion** (React-based video renderer) and **Kokoro TTS** (local neural TTS). Output is an MP4 file — no external services, no fees.

---

## Phase 1: Gather Requirements

Before writing any code, ask the user for:

1. **Topic** — What is the presentation about?
2. **Audience & purpose** — Who is watching and why? (professor, client, conference, job interview)
3. **Key points** — Required topics, rubric, or specific things to showcase?
4. **Assets** — Screenshots, diagrams, logos, images available to include?
5. **Voice preference** — Run a voice test (see Phase 6) before committing
6. **Target length** — Rough duration in minutes

Draft a slide outline and confirm it with the user before building anything.

---

## Phase 2: Project Setup

Create a `presentation/` directory at the project root with this structure:

```
presentation/
├── package.json
├── tsconfig.json
├── remotion.config.ts        ← production config (4K, all cores)
├── remotion.config.test.ts   ← test config (low-res, fast)
├── generate_narration.py
├── src/
│   ├── index.ts
│   ├── Root.tsx
│   ├── Video.tsx
│   ├── components/
│   │   ├── SlideLayout.tsx
│   │   ├── BulletList.tsx
│   │   └── CodeBlock.tsx
│   └── slides/
│       ├── 01-Title.tsx
│       └── ...
└── public/
    ├── audio/
    └── <assets>/
```

### package.json

```json
{
  "name": "presentation",
  "scripts": {
    "studio": "remotion studio",
    "render:test": "remotion render src/index.ts MainComposition out/test.mp4 --config remotion.config.test.ts --concurrency $(sysctl -n hw.logicalcpu 2>/dev/null || nproc)",
    "render:final": "remotion render src/index.ts MainComposition out/presentation_4k.mp4 --concurrency $(sysctl -n hw.logicalcpu 2>/dev/null || nproc)"
  },
  "dependencies": {
    "remotion": "^4.0.0",
    "@remotion/cli": "^4.0.0",
    "react": "^18.0.0",
    "react-dom": "^18.0.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "@types/react": "^18.0.0"
  }
}
```

### remotion.config.ts — production (4K)

```ts
import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setJpegQuality(100);
Config.setCrf(10);
Config.setScale(2);            // renders at 3840×2160
Config.setOverwriteOutput(true);
Config.setCodec("h264");
```

### remotion.config.test.ts — fast iteration

```ts
import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setJpegQuality(80);
Config.setCrf(23);
Config.setScale(0.5);          // renders at 960×540 — ~16× faster than 4K
Config.setOverwriteOutput(true);
Config.setCodec("h264");
```

Always develop with the test config. Switch to production only for the final export.

---

## Phase 3: Design System

### SlideLayout.tsx — color tokens + base frame

Define a `C` object as a single source of truth. Adapt colors to match the project's brand:

```tsx
export const C = {
  bg:      "#0a0e1a",
  surface: "#111827",
  border:  "#1e2d40",
  text:    "#e2e8f0",
  subtext: "#64748b",
  codeBg:  "#0d1117",
  codeText:"#c9d1d9",
  // accent colors — customize as needed
  blue:    "#3b82f6",
  blueL:   "#93c5fd",
  purple:  "#7c3aed",
  purpleL: "#a78bfa",
  green:   "#10b981",
  orange:  "#f59e0b",
};
```

**Always use `AbsoluteFill` as the root element** — `width: "100%", height: "100%"` does not reliably fill the frame in Remotion's render environment. Import `AbsoluteFill` from `"remotion"` and use it as the outermost element of `SlideLayout`:

```tsx
import { AbsoluteFill } from "remotion";

export const SlideLayout: React.FC<Props> = ({ children, slideNum, totalSlides, vCenter }) => (
  <AbsoluteFill style={{ background: C.bg, flexDirection: "column", fontFamily: "..." }}>
    {/* top accent bar */}
    <div style={{ height: 10, background: C.accent, flexShrink: 0 }} />
    {/* content area fills all remaining space */}
    <div style={{
      flex: 1, padding: "48px 80px 40px",
      display: "flex", flexDirection: "column",
      justifyContent: vCenter ? "center" : "flex-start",
      minHeight: 0, overflow: "hidden",
    }}>
      {children}
    </div>
    {/* bottom bar */}
    <div style={{ height: 52, background: C.accent, flexShrink: 0, ... }} />
  </AbsoluteFill>
);
```

**`vCenter` prop** — pass `vCenter` to `SlideLayout` on title and conclusion slides to vertically center their content. Do NOT try to center by wrapping children in a `flex: 1` div — that pattern fails without `AbsoluteFill`.

**`SlideHeading` shared component** — extract the label + title block that every slide repeats into a single exported component in `SlideLayout.tsx`. This avoids copy-paste drift and makes font/spacing changes apply everywhere:

```tsx
export const SlideHeading: React.FC<{ label: string; title: string; opacity?: number }> = ({ label, title, opacity = 1 }) => (
  <div style={{ opacity, flexShrink: 0, marginBottom: 36 }}>
    <div style={{ fontSize: 17, fontWeight: 700, letterSpacing: 4, color: C.accent, marginBottom: 12, textTransform: "uppercase" }}>
      {label}
    </div>
    <div style={{ fontSize: 66, fontWeight: 900, color: C.text, lineHeight: 1.05 }}>{title}</div>
  </div>
);
```

**Filling dead space** — fixed margins cause content to cluster at the top with the bottom half empty. Use these patterns so content always fills the available height:
- Flex lists: wrap items in `<div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "space-evenly" }}>` 
- Grids: use `gridTemplateRows: "repeat(N, 1fr)"` so rows distribute evenly
- The content area below `SlideHeading` should always receive `flex: 1` so it expands to fill remaining space

### Reusable components

**BulletList** — staggered spring animations, one item per delay interval

**CodeBlock** — syntax-highlighted code panel. Key implementation note: mark number tokens with placeholders *before* injecting any HTML `<span>` tags, then materialise the number spans last. This prevents keyword regexes (which inject CSS like `font-weight:600`) from being matched by the number regex.

---

## Phase 4: Slide Architecture

### Root.tsx

```tsx
import { Composition } from "remotion";
import { MainVideo, TOTAL_FRAMES } from "./Video";

export const RemotionRoot = () => (
  <Composition
    id="MainComposition"
    component={MainVideo}
    durationInFrames={TOTAL_FRAMES}
    fps={30}
    width={1920}
    height={1080}
  />
);
```

### Video.tsx — slide registry with audio

```tsx
import { Audio, Sequence, Series, staticFile } from "remotion";

const SLIDES = [
  { component: TitleSlide,    frames: 480  },
  { component: ContentSlide1, frames: 600  },
  // one entry per slide — set frames AFTER generating audio (see Phase 7)
];

export const TOTAL_FRAMES = SLIDES.reduce((sum, s) => sum + s.frames, 0);

export const MainVideo = () => (
  <Series>
    {SLIDES.map(({ component: Component, frames }, i) => (
      <Series.Sequence key={i} durationInFrames={frames}>
        {/* 12-frame delay lets animations start before narration begins */}
        <Sequence from={12}>
          <Audio src={staticFile(`audio/slide_${String(i + 1).padStart(2, "0")}.wav`)} />
        </Sequence>
        <Component />
      </Series.Sequence>
    ))}
  </Series>
);
```

**Frame sizing rule:** after generating audio, set each slide's frames to `ceil(duration_seconds * 30) + 60` (2-second buffer after narration ends).

---

## Phase 5: Slide Patterns

| Pattern | When to use |
|---|---|
| Title | Opening: name, tagline, key details |
| Bullet list | Motivation, key decisions, feature overview |
| Two-column | Code/diagram on right, explanation on left |
| Three-column | Architecture layers, side-by-side comparison |
| Screenshot grid | UI demo — 2–3 screenshots side by side |
| Full-width image | Diagrams, charts, wireframes |
| Stats/conclusion | Summary with metric boxes |

### Animation conventions

- Use `spring()` for entrances (elements slide up and settle)
- Use `interpolate()` for opacity fades keyed to specific frames
- Stagger delays: `delay={20 + i * 10}` for lists, `delay={20 + i * 20}` for cards
- Keep animations in the first 60–80% of slide duration so content is fully visible during narration

---

## Phase 6: Voice Selection

Test voices before generating all narration. Install kokoro: `pip install kokoro soundfile`.

```python
from kokoro import KPipeline
import soundfile as sf, numpy as np

pipeline = KPipeline(lang_code='a')
text = "This is a quick voice test for the presentation."
samples = [a for _, _, a in pipeline(text, voice='am_michael', speed=1.0)]
sf.write("voice_test.wav", np.concatenate(samples), 24000)
# Play: afplay voice_test.wav (macOS) or aplay voice_test.wav (Linux)
```

Available voices:

| ID | Character |
|---|---|
| `af_heart` | American female, warm |
| `af_sky` | American female, lighter |
| `am_adam` | American male |
| `am_michael` | American male, deeper |
| `bf_emma` | British female |
| `bm_george` | British male |

Have the user confirm the voice before generating all slides.

---

## Phase 7: Narration Generation

### Step 1 — Clarify pronunciation of technical terms BEFORE writing scripts

TTS engines mispronounce many technical words silently — the audio will sound wrong and there is no warning. Before writing any narration:

1. Scan all slide content for: product names, acronyms, abbreviations, domain jargon, version numbers, and any word that is not plain English.
2. List every ambiguous term and ask the user how each one should sound. Example prompt:

> Before I write the narration, I need to confirm how a few technical terms should be pronounced. How should each of these sound when spoken aloud?
> - `PostgreSQL` — "post-gres-Q-L"? "post-gress"? "postgres"?
> - `SQLAlchemy` — "S-Q-L Alchemy"? "sequel Alchemy"?
> - `CRUD` — spelled out "C-R-U-D"? or said as a word?
> - `v3.1` — "version three point one"? "three one"?

3. Once the user confirms, encode each term's spoken form directly in the script strings. Do not rely on the TTS engine to infer pronunciation — spell it how it should sound (e.g. `"Postgress"` for a "gress" ending, `"C R U D"` with spaces to force individual letters).

### Writing scripts

- ~2.8 words/second at `speed=1.0` — use this to estimate script length per slide
- Write conversationally — avoid reading symbols or code verbatim
- Add 0.4s lead silence and 0.2s tail silence around each clip

### generate_narration.py

```python
from kokoro import KPipeline
import soundfile as sf, numpy as np, os

pipeline = KPipeline(lang_code='a')
VOICE = 'am_michael'   # set from user's confirmed choice
SAMPLE_RATE = 24000
OUT_DIR = "public/audio"
os.makedirs(OUT_DIR, exist_ok=True)

SCRIPTS = [
    "Slide one narration...",
    "Slide two narration...",
    # one string per slide, in order
]

lead = np.zeros(int(SAMPLE_RATE * 0.4), dtype=np.float32)
tail = np.zeros(int(SAMPLE_RATE * 0.2), dtype=np.float32)

for i, script in enumerate(SCRIPTS, 1):
    samples = [a for _, _, a in pipeline(script, voice=VOICE, speed=1.0)]
    audio = np.concatenate([lead] + samples + [tail])
    sf.write(f"{OUT_DIR}/slide_{i:02d}.wav", audio, SAMPLE_RATE)
    print(f"slide_{i:02d}.wav  {len(audio)/SAMPLE_RATE:.2f}s")
```

After running, **update frame counts in Video.tsx** based on actual durations before rendering.

---

## Phase 8: Rendering Workflow

### Check a single slide (fastest feedback)

```bash
# Frame N = sum of all prior slides' frame counts + offset into that slide
./node_modules/.bin/remotion still src/index.ts MainComposition out/check.png --frame=<N>
open out/check.png
```

### Test render (low-res, all cores)

```bash
npm run render:test
# or manually:
./node_modules/.bin/remotion render src/index.ts MainComposition out/test.mp4 \
  --config remotion.config.test.ts \
  --concurrency $(sysctl -n hw.logicalcpu 2>/dev/null || nproc)
```

### Final 4K render (all cores)

```bash
npm run render:final
# or manually:
./node_modules/.bin/remotion render src/index.ts MainComposition out/presentation_4k.mp4 \
  --concurrency $(sysctl -n hw.logicalcpu 2>/dev/null || nproc)
```

Optionally compress to 1080p after:

```bash
ffmpeg -y -i out/presentation_4k.mp4 \
  -vf "scale=1920:1080:flags=lanczos+accurate_rnd" \
  -c:v libx264 -crf 10 -preset slow -movflags +faststart \
  out/presentation_1080p.mp4
```

---

## Phase 9: Common Pitfalls

**Content stuck in top-left corner / `height: "100%"` not working**
`width: "100%", height: "100%"` does not reliably fill the frame in Remotion. Always use `AbsoluteFill` from `"remotion"` as the root of `SlideLayout`. Without it, percentage heights resolve to zero and all content collapses to the top-left.

**Dead space below content**
Fixed font sizes and margins cause items to fill only the top 30–40% of a slide. Wrap list content in a flex column with `justifyContent: "space-evenly"` and give the container `flex: 1` so it expands to fill the space between the heading and the bottom bar. For grids, use `gridTemplateRows: "repeat(N, 1fr)"`.

**Screenshots cropped or zoomed**
Two separate issues that are easy to confuse:
1. *Playwright captures only the viewport* — always pass `full_page=True` to `page.screenshot()`, otherwise anything below ~900px is cut off.
2. *`objectFit: "cover"` zooms in* — use `objectFit: "contain"` so the full screenshot is visible. Set a background color on the container so letterbox areas don't show as black bars.

```python
# Playwright — always full page
page.screenshot(path="out.png", full_page=True)
```

```tsx
// Remotion — always contain, not cover
<Img src={staticFile("screenshots/foo.png")}
     style={{ width: "100%", height: "100%", objectFit: "contain", background: "#fff" }} />
```

**Image cut off inside a flex container**
Add `minHeight: 0` to every flex ancestor of the image container, and use `width: "100%", height: "100%", objectFit: "contain"` on `<Img>` — not `maxWidth`/`maxHeight`, which don't work without a concrete parent height.

**Narration longer than slide duration**
Log actual WAV durations after generation and recalculate frame counts before rendering.

**Numbers appearing inside code blocks**
If keyword highlighting injects `font-weight:600` as inline CSS before numbers are highlighted, the number regex will match "600". Fix: tokenise numbers with placeholders first, inject all other HTML spans, materialise number spans last.

**Rendering is slow**
Always pass `--concurrency $(sysctl -n hw.logicalcpu 2>/dev/null || nproc)` — the default is half your cores. Use the test config (`setScale(0.5)`) during iteration; only switch to `setScale(2)` for the final export.

---

## Final Render Checklist

- [ ] All slides spot-checked via test stills
- [ ] Narration durations logged; frame counts updated in Video.tsx
- [ ] All assets copied into `public/`
- [ ] Final render uses `remotion.config.ts` (scale 2) and all cores
- [ ] Output opened and reviewed after render