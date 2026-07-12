# Phase 6C — Premium Visual Redesign (Website + Dashboard) Handoff

Saved: 2026-07-11  
Scope: transform the visual experience of the public website and the Streamlit dashboard into a premium, football-tournament-inspired product ("Floodlit Night Stadium"), without changing any analytics, data wiring, model, simulation, live pipeline, or deployment behavior. **Not pushed — local restore-point commit only, pending review.**

## 1. Objective & guardrails

Make both apps feel like *a serious football intelligence platform* — cinematic hero, real visual hierarchy, premium cards, professional icons (no emoji-as-design), immersive atmosphere, disciplined motion — while remaining credible to a technical reviewer and **honest** (no fabricated data, no official-FIFA implication, completed-match locking and probability-source honesty preserved). Analytics/methodology untouched.

## 2. Design system created

Full spec in `docs/design/DESIGN_SYSTEM.md`; assets in `docs/design/ASSET_INVENTORY.md`; pre-redesign audit in `docs/design/UI_AUDIT.md`. Highlights: midnight-navy canvas with **CSS/SVG floodlit-stadium atmosphere** (no photos → zero licensing risk), semantic palette (pitch-green = success, gold = championship, cyan = model/data, crimson = elimination), **Space Grotesk + Inter** typography, a multi-variant **card system**, an inline-SVG **icon set**, probability **rings/meters**, filter **chips**, **W/D/L** form chips, and a shared dark **Plotly** template. Website and dashboard share the same tokens so the transition is seamless.

## 3. Imagery / licensing

Football atmosphere is generated in CSS + inline SVG (floodlight glows + pitch geometry), not stock photos — deliberately, to eliminate licensing risk and external requests. A documented optional `website/public/images/` slot lets licensed hero photos be added later (`ASSET_INVENTORY.md`). No FIFA logos/artwork used; visible "Independent — not affiliated with FIFA" disclaimer retained on hero, footer, about.

## 4. Before / after

| Page | Before | After |
|---|---|---|
| **Website — Home** | Gradient headline + text + flat badge row + `<pre>` "how it works"; no imagery | Cinematic floodlit hero (live badge, phase/locked/sims chips, gradient headline, reveal motion), broadcast **live snapshot** row, **featured champion** ring card, **contender cards** (#1 gold-emphasized, champion rings + reach-final meters), most-likely-finals bars, **visual engine pipeline** (7 icon steps + connectors), credibility stat wall + principle chips, upgraded **bracket**, project-story panel, immersive dashboard **CTA** |
| **Website — Teams** | Plain title + basic filter selects + card grid | Floodlit header, **chip filters** (status) + **sort chips** + search, premium team cards (flag, status pill, W-D-L, champion-odds meter, next-match) |
| **Website — Team dossier** | Metric grid + plain journey table | Team **hero** (flag, status pills, champion+final **rings**), **W/D/L form strip**, **strength-profile meters**, **journey match cards**, tasteful future squad-intel placeholder (no fake data) |
| **Website — Methodology → Analytics Lab** | Tables + ASCII | "Inside the Prediction Engine" lab: architecture cards, model-comparison **cards + table** (production highlighted), Phase 5G **diagnostics** (per-class table + calibration + draw explanation), feature-importance **bars**, grouped feature families, validation **badges**, probability-source **ladder** |
| **Website — About** | Plain text | Floodlit header, architecture card, honesty-principle list with icons, CTAs |
| **Website — Nav / Footer** | Text link row / basic | Sticky glass nav with **SVG icons + active states + primary Dashboard CTA**; richer footer with glow + disclaimer |
| **Dashboard — global** | Visible default Streamlit chrome, `st.metric`, default charts | Injected **stadium theme**: hidden default chrome, floodlit background, styled sidebar/tabs/buttons/inputs/tables/expanders, premium metric cards, dark Plotly template — applied to **all 9 pages** |
| **Dashboard — Overview** | Title + 12 default metrics + markdown | **Command center**: live header, custom **KPI card grid**, **featured champion** card (flag + big %), **top-contender bars**, system-flow |
| **Dashboard — Forecast / Match Predictor / Team Intelligence / Bracket / Forecast Evolution / Analytics Lab / System Health / Technical Audit** | Emoji titles, default components | Themed headers (kicker + icon + sub, no emoji), dark charts, restyled cards/metrics/tables; sharper microcopy ("The Road to the Title", "Match Predictor", "Inside the Prediction Engine") |

## 5. Interactions added

Reveal-on-load hero, hover card elevation, filter/sort **chips**, probability **rings**, semantic **meters**, pulsing **live badge**, connected **pipeline**, navigation-as-CTA cards, active nav states, gradient headlines — all `prefers-reduced-motion`-safe.

## 6. Files

**Added:** `website/components/icons.tsx`, `website/components/ui.tsx`, `dashboard/theme.py`, `docs/design/UI_AUDIT.md`, `docs/design/DESIGN_SYSTEM.md`, `docs/design/ASSET_INVENTORY.md`, this handoff.
**Modified (presentation only):** `website/app/globals.css`, `website/app/layout.tsx`, `website/app/page.tsx`, `website/app/teams/page.tsx`, `website/app/team/[slug]/page.tsx`, `website/app/methodology/page.tsx`, `website/app/about/page.tsx`, `website/components/Nav.tsx`, `website/components/Footer.tsx`, `website/components/Bracket.tsx`, `website/components/TeamExplorer.tsx`; `dashboard/app.py` + `dashboard/pages/1..8`; `.streamlit/config.toml`. **Data getters, schemas, and all Python analytics/pipeline code unchanged.** `ProbBar.tsx`/`SourceBadge.tsx` retained (SourceBadge still used by Bracket).

## 7. Verification (all run locally)

- Website: `npm run lint` clean, `npm run build` **55/55 static pages**.
- Dashboard: `compileall` OK; **Streamlit AppTest ran all 9 pages → 0 failures**; headless startup healthy; `validate-dashboard` pass.
- Backend regression: `pytest` **24 passed**; `validate-public-exports` / `validate-live-forecast` pass; production model + live pipeline untouched.
- No new Python dependencies. Two OFL web fonts added to the website (next/font) — no font files committed.

## 8. Screenshots

Not captured from this environment — there is no headless browser / screenshot tool available here. Rendering was verified via the production `next build` (all pages prerender with data) and Streamlit `AppTest` (all pages execute without exception). **Visual screenshots are for the user to capture in a browser during review** (`npm run dev` for the site; `streamlit run dashboard/app.py` for the dashboard).

## 9. Responsive & accessibility

Responsive: hero/type scale down, grids collapse to 1–2 cols, bracket scrolls horizontally, pipeline wraps, dashboard stacks. Accessibility: focus-visible outlines, aria-labels, `role="meter"`, semantic headings, color never the sole signal, reduced-motion honored.

## 10. Known limitations & future opportunities

- No real photographs (by design); optional documented slot exists for licensed hero images.
- Dashboard CSS targets Streamlit `data-testid`/`data-baseweb` selectors — robust today but re-check on major Streamlit upgrades (cosmetic-only; no logic depends on it).
- Screenshots pending user capture.
- Figma/Canva/Webflow are connected but were **not** used to generate throwaway design files — the shippable deliverable is the in-repo code, which is where the final implementation must live. They remain available for future iteration.
- Match Predictor page keeps the existing (list-based) matchup UX rather than a full team-vs-team selector — a strong future enhancement, but out of scope for a presentation-only pass.

## 11. Status

**Nothing pushed. Nothing deployed.** A single local restore-point commit was created on `main`. Awaiting the user's review of screenshots, code, and functionality before any push.

## 12. Recommended next step

User reviews locally (`npm run dev`, `streamlit run dashboard/app.py`), captures screenshots, then approves the push — after which the normal auto-deploy (Vercel + Streamlit Cloud) applies. Optional follow-ups: licensed hero imagery, a true team-vs-team Match Predictor, and Phase 5H (player/squad intelligence) to fill the team-dossier placeholder.
