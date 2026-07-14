# Current Status — 2026-07-12

Snapshot of everything done in this working session, plus the live results. `origin/main` and local `main` are in sync at **`aa7e411`**.

## 1. What shipped (in order)

| Commit | What | Pushed? | Deployed |
|---|---|---|---|
| `2f2ff93` | **Phase 5H-A** — Zafronix World Cup enrichment (challenger evaluated, **REJECTED**) | ✅ pushed | CI ✅ · Vercel READY |
| `1d12337` | **Matchday** — locked Norway 1-2 England, re-forecast to semifinal | ✅ pushed | Vercel READY |
| `d569f58` | **Phase 6C** — "Floodlit Night Stadium" website + dashboard redesign | ✅ pushed | Vercel READY |
| `ef7f47c` | **WC26 crest** on the website nav (original artwork) | ✅ pushed | Vercel READY |
| `aa7e411` | **WC26 crest** in the dashboard header (matches website) | ✅ pushed | Streamlit auto-reboot |

Base before the session: `de1e2dc` (Phase 5G).

## 2. Phase 5H-A — Zafronix enrichment (headline result)

Added the real **Zafronix World Cup API** as a *secondary* historical/squad enrichment provider (football-data.org remains the sole live-truth source). Fetched all 23 tournaments in ~25 sanitized, ETag-cached requests; resolved **91/91** team names (1 alias, no silent merges); engineered **17 leakage-safe** features (World Cup pedigree, squad age/positional depth, player prior-WC experience).

**Decision: REJECT the challenger — production XGBoost retained, byte-identical.**

| Metric | Production XGBoost (baseline) | Zafronix challenger (E3) |
|---|---|---|
| Accuracy | **0.6075** | 0.6075 (+0.0000) |
| Macro F1 | **0.4511** | 0.4511 |
| Log loss | **0.8607** | 0.8610 (slightly worse) |
| Brier | **0.5056** | 0.5058 |
| ECE | **~0.0053** | 0.0053 |

Paired-bootstrap 95% CI on the accuracy difference = **[−0.0013, +0.0013]** (includes zero → no real gain). Only 2.1% of training matches are World Cup finals, and pedigree signal overlaps Elo — so the model *uses* the features (`z_pedigree_available` ranks #8/42 by gain) but they add no new held-out signal. Honest, acceptable outcome. Zafronix pipeline retained for descriptive/analytical use only; it does **not** power production predictions.

Full detail: [`PHASE_5H_A_REPORT.md`](../PHASE_5H_A_REPORT.md), [`handoff/phase5h_a_zafronix_enrichment_handoff.md`](phase5h_a_zafronix_enrichment_handoff.md), artifacts under `outputs/reports/enrichment/zafronix/`.

## 3. Live tournament state (current forecast)

Latest result **fetched from football-data.org** (never hand-typed) and locked: **Norway 1-2 England** (quarterfinal). Tournament phase advanced **quarterfinal → semifinal**.

- **Semifinals:** France vs Spain (2026-07-14) · England vs Argentina (2026-07-15)
- **Champion probabilities** (four semifinalists, sum = 100%, 10k Monte Carlo sims):
  - Argentina **31.6%** · Spain **28.6%** · France **22.8%** · England **17.0%**

Completed matches remain locked; production model unchanged; exports republished and validated.

## 4. Phase 6C — visual redesign (now live)

Premium "Floodlit Night Stadium" redesign of the website (Next.js) and Streamlit dashboard: cinematic hero, semantic palette, card system, inline-SVG icons, probability rings/meters, shared dark charts, and **real country flags** via the open-source `flag-icons` library (public-domain flags), replacing emoji.

**Brand-safety event:** the working-tree draft embedded an **official FIFA World Cup 2026 emblem** in the site nav. That violates the project's no-official-artwork rule and poses trademark risk, so it was **removed before publishing**. In its place is an **original WC26 crest** — a medallion badge (trophy · star · pitch arc) drawn as inline SVG in the project palette — now used identically on the **website nav** (`website/components/Crest.tsx`) and the **dashboard header** (`dashboard/theme.py` `crest_svg()`). No FIFA logos/emblems or trademarked artwork exist anywhere in the repo or on either deployed surface; the "independent — not affiliated with FIFA" disclaimer stands.

## 5. Verification (all green)

- Backend: `pytest tests -q` → **35 passed**; `compileall` clean; `validate-public-exports` (31), `validate-dashboard` (10), `validate-live-forecast` all **pass**.
- Website: `npm run lint` clean; `npm run build` → **55/55 static pages** (verified after every website change).
- Dashboard: Streamlit `AppTest` → all pages render, **0 failures**.
- Production model + registry: **byte-identical** (untouched in every pushed commit; working tree clean).
- Secret hygiene: no `.env`, no API keys, no partial key prefixes in any tracked artifact (Zafronix `keyPrefix` stripped).
- GitHub Actions `Validate` workflow for `2f2ff93`: **success** (offline, no secrets required).
- CI is offline-safe: does not require `ZAFRONIX_API_KEY`.

## 6. Deployment state

- **GitHub:** `origin/main` = `aa7e411` (0 ahead / 0 behind).
- **Vercel (website):** auto-deploys on push; latest production deployment **READY** at `dynamic-fifa-2026-predictor.vercel.app`.
- **Streamlit Cloud (dashboard):** watches `main`, auto-reboots on push; last change (`aa7e411`) will appear on its next rebuild (no queryable status API from here).
- **Portfolio Refresh workflow:** manual-dispatch only; **not triggered**.

## 7. Branches / safety nets

- `main` — current, pushed.
- `phase6c-redesign` (`1d676db`) — the originally-reviewed Phase 6C snapshot, preserved (superseded by the live version).
- `backup-main-509f759` (`509f759`) — pre-rebase backup of the local restore point. Safe to delete once you're comfortable.

## 8. Open items / notes

- The dashboard shows the new crest — give Streamlit Cloud a minute to reboot, then eyeball the live site + dashboard (I verified they build/render, but did not do a visual QA pass).
- New website dependency: `flag-icons` (MIT).
- Possible next steps: surface Zafronix World Cup pedigree/squad-depth as **descriptive** team intelligence on team pages (honest, leakage-safe); optional licensed hero photography; a true team-vs-team match predictor.
