# create-presentation

Build animated, narrated video presentations using **Remotion** (React-based video renderer) and **Kokoro TTS** (local neural TTS). Output is an MP4 file — no external services, no fees.

## Overview

This plugin gives Claude a complete workflow for producing video presentations from scratch: gathering requirements, scaffolding a Remotion project, building slides with a design system, generating voiceover with Kokoro TTS, and rendering to MP4.

Invoke it directly with `/create-presentation`, or it will trigger automatically when you ask Claude to present a project, make slides, record a demo, or showcase work visually.

## Installation

```
/plugin install EricMarcantonio/skills/plugins/create-presentation
```

## Core Capabilities

- **Requirements gathering:** Audience, key points, assets, voice preference, target length
- **Project scaffolding:** Full Remotion project with TypeScript, design system, and reusable components
- **Design system:** NYU-inspired dark theme with color tokens, `SlideLayout`, `SlideHeading`, `BulletList`, `CodeBlock`
- **Slide patterns:** Title, bullet list, two-column, three-column, screenshot grid, full-width image, stats/conclusion
- **Narration:** Kokoro TTS with pronunciation clarification workflow before script writing
- **Rendering:** Test config (0.5× scale, fast) and production config (4K, all cores)

## When to Use

- Presenting a course or work project
- Creating a video walkthrough or demo
- Building an animated slide deck
- Recording a pitch or conference talk

## Requirements

- Node.js + npm (for Remotion)
- Python 3.9+ with `kokoro` and `soundfile` installed (`pip install kokoro soundfile`)
- ffmpeg (optional, for 1080p downscale after 4K render)

## Related Plugins

Check the [marketplace](../../README.md) for other available plugins.
