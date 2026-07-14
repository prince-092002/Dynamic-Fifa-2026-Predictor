# Handoff — Website Design Phase (FIFA 2026 poster hero + About rewrite)

**Date:** 2026-07-12 · **Status:** implemented, built, previewed locally, **committed locally as `2eb8863` — NOT pushed** (`origin/main` = `56fd786`). Awaiting your review.

## A. Executive summary
Website-only visual + content phase. The homepage now opens on a **fixed "poster" hero** — floodlit backdrop with **original footballer silhouettes** and a large centered **FIFA 2026** wordmark, content scrolling over a fixed background. The **About page** was rebuilt from a thin blurb into a full explanatory product page (data, models, how-it-works, live behaviour, limitations, and a 12-item FAQ). No prediction/pipeline logic changed.

## B. What changed
| Area | Change |
|---|---|
| Homepage hero (`website/app/page.tsx`) | Centered poster layout; giant gold-gradient **FIFA 2026**; "Dynamic Tournament Intelligence" kicker; live chips, CTAs, tech badges, scroll cue. Rest of homepage unchanged. |
| Hero backdrop (`website/components/HeroBackdrop.tsx`, **new**) | Fixed, homepage-only: twin floodlight beams, pitch-light pool, 4 original SVG player silhouettes (varied scale/facing, one with a ball), centre vignette for readability, lower fade-out. |
| About page (`website/app/about/page.tsx`) | Full rewrite — sections A–I + FAQ (see C). |
| Global CSS (`website/app/globals.css`) | Added fixed-hero backdrop system, poster type (`.poster-title`), numbered step rail, FAQ accordion, About thematic backgrounds. |
| `docs/design/ASSET_INVENTORY.md` | Documented the silhouettes + an optional **licensed-photo** slot. |

## C. About page content (all facts verified against the real project)
- **Overview** — end-to-end live sports-analytics system; live not static.
- **Why built** — can we estimate finalists/champion from the current tournament state; a live decision system.
- **Data sources** — ~50k historical matches (training) · **football-data.org = primary live truth** · **Zafronix = secondary enrichment, not production**; + "what live truth means" note.
- **Model inputs** — 25 leakage-safe, pre-match, team-level features in 5 families (Elo strength, recent form, goal-based form, head-to-head, tournament context).
- **How it works** — 6-step rail (train → estimate → lock results → predict next → simulate → read odds) + plain-language Monte Carlo explainer (10,000 sims).
- **Models** — XGBoost (production; acc **0.6075**, macro-F1 **0.4511**, log loss **0.8607**) · Logistic Regression (baseline; acc **0.5752**, macro-F1 **0.5273**) · Monte Carlo (simulation layer) + honest **Zafronix challenger rejected** note (95% CI on accuracy diff spanned zero).
- **Live behaviour** — completed matches locked · eliminated teams removed · new matchups predicted · bracket re-simulated.
- **Limitations** — team-level not player-level; no injuries/lineups/tactics; probabilities are forecasts not guarantees; numbers move with new results.
- **FAQ (12)** — Macro F1 vs accuracy · recent-win effect · recency bias · why probs change · rival-eliminated effect · current team status · injuries/lineups/tactics · Monte Carlo · probabilities ≠ guarantees · why keep XGBoost · Zafronix's role · official FIFA product? (all answered concisely & accurately).

## D. Brand / rights safety
- **No real player photos.** Photos of Messi/Mbappé/Lamine Yamal/Kane are copyrighted and the players hold likeness/publicity rights → not used. The hero uses **original, generic SVG silhouettes** (no identifiable person depicted).
- **No FIFA logos/artwork.** Logo mark remains the original WC26 crest. "Independent — not affiliated with FIFA" disclaimer retained.
- A documented **licensed-photo drop-in slot** exists for later, with an explicit note that player photos additionally need publicity/likeness clearance.

## E. Verification
- `npm run lint` **clean**; `npm run build` **✓ 55/55 static pages**.
- Local production + dev server render: home & `/about` return **HTTP 200** with expected content (FIFA 2026 poster + `hero-backdrop`/`figures`; all About sections + 12 `.faq` items).
- **Screenshots not captured** (no headless browser in the build environment) — visual QA is for the reviewer.
- No new dependencies; no binary assets added.

## F. How to preview
```
cd website && npm run dev      # http://localhost:3000  and  /about
```

## G. Repository / deployment state
- `origin/main` = **`56fd786`** (last deployed; Vercel READY).
- Local `main` = **`2eb8863`** — this phase, **1 commit ahead, NOT pushed / NOT deployed**.
- Preservation branches: `phase6c-redesign` (`1d676db`), `backup-main-509f759` (`509f759`).
- Production ML model + live pipeline untouched this phase.

## H. Current live forecast (already deployed at 56fd786)
Phase **semifinal**. Semifinals: **France vs Spain**, **England vs Argentina**. Champion odds ≈ **Argentina 30.7% · Spain 28.6% · France 22.9% · England 17.7%** (sum = 1). Matchup list shows only the two real semifinals (Mexico–England provider-status bug fixed in `56fd786`).

## I. Open items / next steps
- **Review the local preview**, then either approve the **push** (Vercel redeploys the new hero + About) or request iterations (hero silhouettes, wording, FAQ, spacing).
- Optional: licensed hero photography via the documented slot.
- Uncommitted elsewhere: prior session handoffs (`session_status_2026-07-12.md`, etc.) and volatile data/outputs remain local; not part of this commit.

## J. Push status
**Nothing pushed in this phase.** Local restore-point commit `2eb8863` only.
