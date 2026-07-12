# UI/UX Audit — pre-redesign (2026-07-11)

Audit of the current public website (Next.js 15 / Tailwind 4, static from `public_data/`) and Streamlit analytics dashboard (`dashboard/app.py` + 8 pages), before the premium football-intelligence visual transformation.

## Current inventory

- **Website pages:** `/` (home), `/teams`, `/team/[slug]` (48 SSG), `/methodology`, `/about`. Components: `Nav`, `Footer`, `Bracket`, `TeamExplorer`, `ProbBar` (CSS bar), `SourceBadge`.
- **Dashboard pages:** Overview (`app.py`), Live Bracket, Champion Forecast, Matchup Predictions, Team Explorer, Forecast Evolution, Model Methodology, System Health, Technical Audit. Plotly charts, `st.metric`, `st.dataframe`.
- **Design tokens today:** a small CSS-variable set (navy bg, cyan/blue/magenta/green accents) in `globals.css`; system fonts only; no imagery; no icon system (emoji used in page titles).

## Findings — what looks plain / weak

| Area | Problem |
|---|---|
| Hero | Home is a gradient headline + text + flat badge chips — reads like a resume header, not a product launch. No atmosphere, no depth, no imagery. |
| Imagery | **Zero imagery anywhere.** No stadium/pitch/floodlight atmosphere; pages are flat dark rectangles. |
| Cards | One generic `.card` (flat border, no depth, no variants). KPI tiles, contenders, matches, insights all look identical. No hierarchy by importance. |
| Icons | **Emoji as the icon language** (⚽ 🏆 🎯 🌍 🧠 🩺 🔍) in both apps — the exact "student-project" tell the brief calls out. |
| Contenders | Champion forecast is plain CSS bars / a Plotly bar — no ranked contender cards, no probability rings, no visual emphasis on the favorite. |
| Engine/pipeline | "How it works" is a `<pre>` ASCII block — not an interactive/visual flow. |
| Navigation | Website nav is a plain text link row; dashboard uses default Streamlit page list. No icons, weak active state, no personality. |
| Charts | Default Plotly light-ish styling; inconsistent; not a cohesive dark broadcast theme. |
| Streamlit chrome | Default Streamlit header/menu/footer, default `st.metric`, default `st.dataframe`, default sidebar — visibly "a Streamlit app." |
| Hierarchy/whitespace | Uniform spacing, no sectional rhythm, no featured vs supporting distinction. |
| Microcopy | Generic headings ("Champion Forecast", "Model Methodology", "System Health"). |
| Motion | None — no reveal, hover elevation, or number count-up. |
| Mobile | Functional (Tailwind responsive / Streamlit stacking) but bracket + architecture read as plain scrollable lists. |

## Direction (implemented in this redesign)

A shared **"floodlit night stadium"** identity across both apps: midnight-navy canvas, layered floodlight glows + pitch-geometry line art (CSS/SVG, zero licensing risk), **pitch-green / tournament-gold / data-cyan / elimination-crimson** semantic accents, a strong display typeface (Space Grotesk) + clean body (Inter), a **multi-variant card system**, an **inline SVG icon set** (no emoji), probability **rings**, a visual **engine pipeline**, broadcast-style **live snapshot**, and disciplined motion (reveal-on-load, hover elevation, count-up) that respects `prefers-reduced-motion`. Full spec: `docs/design/DESIGN_SYSTEM.md`.
