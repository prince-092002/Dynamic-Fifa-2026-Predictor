# Design System — "Floodlit Night Stadium"

Shared visual language for the Vercel website and the Streamlit dashboard so they read as one product. Football-tournament-inspired; **independent project — no official FIFA branding, logos, or artwork.**

## Identity

Elite international football under stadium floodlights — midnight canvas, pitch-line geometry, broadcast-grade data. Disciplined, not decorative.

## Color system (semantic)

| Token | Hex | Meaning |
|---|---|---|
| `--bg` / `--bg-2` | `#05080f` / `#080d18` | Midnight-navy canvas |
| `--surface` / `--surface-elev` | `#131f31` / `#1a2942` | Cards, elevated panels |
| `--line` / `--line-strong` | `#223049` / `#33456a` | Hairline / structural borders |
| `--fg` / `--fg-2` / `--fg-3` | `#eef4fd` / `#9db0cc` / `#61728e` | Primary / secondary / faint text |
| **`--pitch`** | `#29d17f` | Positive form · qualify · winning probability · success |
| **`--gold`** | `#f5c451` | Championship · featured contender · prestige |
| **`--cyan`** | `#38bdf8` | Model / data / technical intelligence |
| `--amber` | `#fbbf24` | Caution / draw |
| **`--crimson`** | `#f4515f` | Elimination · negative · danger |
| `--blue` | `#4f8cff` | Supporting data series |

Accents are used **only where they carry meaning** — no rainbow interface. Website tokens live in `website/app/globals.css` (`@theme inline`); the dashboard mirrors them in `dashboard/theme.py`.

## Typography

- **Display / headings:** Space Grotesk (600–700) — geometric, sporty, technical. Website via `next/font/google` (OFL, self-hosted at build, no external runtime request); dashboard via Google Fonts `@import`.
- **Body:** Inter — highly readable.
- **Metrics/numbers:** Space Grotesk, tabular-nums, tight tracking (`.stat-num`).
- Utility classes: `.display`, `.kicker` (uppercase tracked eyebrow), `.stat-num`, `.text-gradient`. No font binaries are committed (OFL fonts fetched at build).

## Atmosphere (imagery via CSS/SVG — zero licensing risk)

Instead of copyrighted or generic stock photos, atmosphere is generated:
- `.bg-stadium` (fixed canvas): layered floodlight radial glows (blue/gold from the top, pitch-green from below) + an inline-SVG **pitch-geometry** overlay (halfway line, center circle, penalty boxes) masked to fade.
- `.bg-floodlight`, `.bg-grid`, `.bg-pitch-glow`: per-section treatments.
- Result reads as "night match / pitch / broadcast" with **no external image requests** and **no licensing exposure**. A documented `website/public/images/` slot exists to drop in licensed hero photos later (see `docs/design/ASSET_INVENTORY.md`).

## Card system (variation by importance)

| Class | Use |
|---|---|
| `.card` (+`.card-hover`) | Default KPI / content card, subtle lift on hover |
| `.card-feature` | Highest-emphasis (champion, #1 contender, CTA) — gold-tinted, glow |
| `.card-elev` | Elevated narrative panel |
| `.card-glass` | Selective translucent panel |
| `.rail` (`--accent`) | Insight card with a colored left rail |
| dashboard `.sk-card` / `.sk-feature` | Streamlit equivalents |

## Icon system

Inline stroke SVGs (`website/components/icons.tsx`, `dashboard/theme.py:icon()`): trophy, pitch, chart, bolt, shield, calendar, network, database, simulation, team, globe, tactics, lab, gauge, route, signal, lock, check, arrow, github. **No emoji** in the product UI (kept only as Streamlit page/tab favicons, which the platform requires).

## Components & interactions

Probability **rings** (`ProbRing`) and **meters** (`Meter`), **filter chips** + **sort chips** (Team Explorer), **live badge** with pulsing dot, **W/D/L form chips** (`.res`), horizontal **engine pipeline** with connectors, **reveal-on-load** hero (`.reveal`), hover elevation, `.text-gradient` headlines. All motion respects `prefers-reduced-motion`.

## Charts

Shared dark template (`apply_plotly()` in the dashboard): transparent backgrounds, Inter/Space Grotesk fonts, semantic `colorway` (cyan → pitch → gold → blue → crimson → amber), muted gridlines, dark tooltips. Charts used only where they add analytical value.

## Accessibility

High-contrast text on dark surfaces, visible `:focus-visible` outlines (cyan), semantic headings, `aria-label`s on nav/controls, meters expose `role="meter"` values, information never conveyed by color alone (source labels carry text + symbol). Reduced-motion honored globally.

## Website ↔ dashboard consistency

Identical palette, typography, card language, icon vocabulary, chip/button styles, and floodlit atmosphere — so moving from the marketing site into the live dashboard feels seamless.
