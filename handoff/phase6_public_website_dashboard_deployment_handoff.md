# Phase 6 Public Website, Dashboard, and Deployment Readiness Handoff

Saved: 2026-07-10  
Scope: turn the verified Phase 5G forecasting system into a public portfolio product — a public-safe data export layer, a Next.js website (Vercel-ready), a Streamlit analytics dashboard, fail-capable public validations, GitHub repository readiness, and deployment documentation. No secrets included; no backend forecasting logic was duplicated or changed.

## 1. Objective

GitHub as source of truth → Vercel website (polished landing) + Streamlit dashboard (deep analytics), both consuming stable public-safe JSON contracts generated from the existing Python/XGBoost/Monte Carlo backend.

## 2. Starting state (Phase 5G) and repository audit findings

- Backend verified through Phase 5G (all validations passing, 245s→1.7s feature build, run manifests/freshness/history artifacts in place).
- **Audit finding:** the project directory was *not* a git repository — earlier "untracked" checks were actually "no repo". Fixed: `git init -b main`, `.gitignore` hardened, initial commit `3e240d4` (421 files, largest 30 MB, secret scan of every tracked file: 0 hits).
- Node v24 + npm 11 available locally, so the website production build was actually run (not assumed). Streamlit 1.58 / Plotly 6.8 already in requirements.txt.
- Tournament state had advanced during Phase 5G: France beat Morocco 2-0 (QF1). All exports/pages read current files; nothing is hardcoded.

## 3. Public data contract and export layer

New package `src/public_export/`:

- `build_public_exports.py` — transforms backend outputs into 13 stable JSON contracts in `public_data/` (see `PUBLIC_DATA_CONTRACT.md` for the full schema table). Includes the **team lifecycle engine** (status from real bracket state: unplayed known matchup teams + completed-match winners − completed-match losers; champion/runner-up from a completed final; group-stage eliminations for teams never reaching the knockout bracket) and the **team statistics engine** (completed real fixtures only, deduplicated by fixture_id, no future matches, no fabricated stats).
- `team_mapping.py` — controlled slug/ISO-code/flag mapping for all 48 teams (England/Scotland via Unicode tag sequences); unmapped names render as plain text rather than guessing.
- `export_validation.py` — `validate-public-exports` (31 fail-capable checks: required keys, probability ranges/sums, eliminated-team exclusions, TBD-not-a-team, source vocabulary, XGBoost-backed predictions, overview/manifest consistency, parseable timestamps, secret scan, private-path scan) and `validate-dashboard` (exports + dashboard inputs + completed-only stats + duplicate identities).
- `deployment_readiness.py` — `validate-deployment-readiness` reporting `public_data_ready`, `dashboard_data_ready`, `python_dependencies_ready`, `streamlit_startup_ready`, `deployment_configuration_ready`, `local_build_ready`, `secret_scan_ready`, `relative_paths_safe`. It never claims a platform deployment occurred.

New CLI: `build-public-exports`, `validate-public-exports`, `validate-dashboard`, `validate-deployment-readiness`. The live forecast pipeline now rebuilds public exports automatically at the end of each run (guarded; never blocks the forecast), so the matchday command leaves everything render-ready.

## 4. Forecast-history persistence (new, backend-written)

`run_audit.append_forecast_history` writes append-safe, run_id-deduplicated snapshots after every forecast run: `champion_probability_history.csv`, `finalist_probability_history.csv`, `finalist_pair_probability_history.csv` (schema: run_id, timestamp, phase, team(s), probability, simulation_count, provider, forecast_mode). No backfill was invented; history starts with the first post-Phase-6 run. Frontends never write history.

## 5. Streamlit dashboard (`dashboard/`)

`streamlit run dashboard/app.py` — entry page (Tournament Overview) + 8 pages: Live Bracket (round filter, source legend), Champion Forecast (Plotly ranked bars: champion/reach-final/top finals), Matchup Predictions (human labels + expandable raw technical panel), Team Explorer (search/status/group filters, 6 sort options, full team detail with record/journey/forecast/history chart), Forecast Evolution (champion/finalist lines over recorded runs, stacked source-progression area with the explicit "not an accuracy metric" note, phase transitions), Model & Methodology (real registry metrics, 28 features grouped, top-10 XGBoost importances, leakage explanation, source ladder), System Health (freshness, gate, validation pass/warn/fail with warning explanations), Technical Audit (full manifest, source counts, public artifact download buttons). Shared cached loaders (`dashboard/data/loaders.py`); reads saved outputs only — no API access, no ML reruns on interaction; every missing file degrades to an honest notice. Theme: `.streamlit/config.toml` (dark navy + cyan, matching the website).

## 6. Next.js website (`website/`)

Next.js 15 (App Router) + TypeScript + Tailwind CSS 4. **Fully static:** all pages prerendered at build time from `../public_data/*.json` via `fs` (`lib/data.ts`, server-only; client-safe types/helpers in `lib/types.ts`). No client fetching, no API key, no backend duplication.

- Routes: `/` (hero + badges + disclaimer, 12-tile live snapshot, champion forecast with CSS probability bars, most-likely finals, live matchup predictions, full knockout bracket, engineering highlights), `/teams` (client-side explorer: search, status/group filters, 6 sorts, team cards), `/team/[slug]` (48 SSG pages: identity, record, forecast, journey table, elimination info), `/methodology` (architecture, real model metrics, grouped features, importances, leakage, source ladder), `/about`.
- Components: `Nav` (responsive, accessible collapsible menu, active states), `Footer` (required disclaimer), `Bracket` (horizontal-scroll rounds, per-state cards, `SourceBadge` with symbol+text — never color alone — and legend), `TeamExplorer`, `ProbBar` (accessible CSS bars).
- Design tokens as CSS variables in `globals.css` (deep navy background, cyan/blue/magenta/red/green accents), `prefers-reduced-motion` respected, focus-visible outlines.
- Optional env vars `NEXT_PUBLIC_DASHBOARD_URL` / `NEXT_PUBLIC_GITHUB_URL` drive the outbound buttons; the site renders fully without them.
- One build issue found and fixed: the client TeamExplorer importing the `fs`-bearing data module — resolved by splitting `lib/types.ts` (client-safe) from `lib/data.ts` (server-only).

## 7. Explainability

Implemented: model comparison table from the real Phase 4 registry (accuracy/log-loss/Brier/macro-F1) and **global XGBoost feature importances** extracted from `selected_model.joblib` (top 10 shown on both apps, with the required "does not explain a specific matchup" note). Not implemented: SHAP/local explainability — deliberately skipped (dependency weight and pipeline-compat validation not justified for this phase); no per-matchup feature claims are made anywhere.

## 8. Verification results (all actually run)

```text
python -m compileall src main.py scripts dashboard   -> pass
python main.py validate                              -> 0 failures (22 pass / 3 expected warns)
python main.py validate-features                     -> pass (incl. leakage)
python main.py validate-simulation / validate-bracket-> pass / pass
python main.py validate-live-feature-equivalence     -> pass (original 5.6s, fast 1.7s)
python main.py validate-live-matchup-flow            -> pass (8/8 sandbox checks)
python main.py validate-live-forecast                -> pass (19 checks)
python main.py build-public-exports                  -> 13/13 files written
python main.py validate-public-exports               -> pass (31 checks, 0 failed)
python main.py validate-dashboard                    -> pass (6 checks, 0 failed)
python main.py validate-deployment-readiness         -> ready (8/8 yes)
cd website && npm run lint                           -> clean
cd website && npm run build                          -> pass (Next 15.5.20, 55 static pages, 106 kB first load)
streamlit run dashboard/app.py (headless)            -> health endpoint "ok"; all 9 scripts parse
Secret scan (4 .env values vs all 421 tracked files) -> 0 hits; .env/.kaggle ignored
git: initialized, initial commit 3e240d4, tree clean
```

## 9. Current live forecast shown by the applications (actual export values)

```text
Provider: football_data_org (fresh_api) | Forecast mode: true_live_forecast | Quality score: 100
Phase: quarterfinal | Completed matches: 97 | Teams alive: 7 | Eliminated: 41
Known unresolved matchups: 3 (Spain-Belgium, Norway-England, Argentina-Switzerland) — all live-XGBoost predicted
Simulations: 10,000 | Top champion: France 29.49% | Top projected final: Argentina vs France 26.07%
Probability sources: completed_result 10,000 · live_model_exact 30,000 · elo_fallback 29,510 · model_reversed 490
Live validation: pass | Broader validation: pass
```

## 10. Deployment instructions (remaining manual platform steps)

1. Create a GitHub repository and push (`git remote add origin … && git push -u origin main`).
2. Vercel: import repo, **Root Directory = `website`**, optional `NEXT_PUBLIC_*` env vars, deploy.
3. Streamlit Community Cloud: new app → `dashboard/app.py`, no secrets needed, deploy.
4. Paste both live URLs into README "Live demo" and set the `NEXT_PUBLIC_*` vars in Vercel.
5. After every real match: run the matchday command, `git add -A && git commit && git push` — both apps update.

Full steps: README.md and website/README.md.

## 11. Known limitations

- **Expected:** SF/final simulation branches use Elo until real participants are known; forecast-history charts need ≥2 recorded runs; `teams_alive` counts knockout survivors (7 right now: France + 6 not-yet-played QF teams).
- **Data limitation:** player-level statistics are not in the verified pipeline and are explicitly stated as unavailable, not fabricated.
- **Deployment limitation:** actual Vercel/Streamlit deployments require the user's accounts; readiness is local-verified only. No license file yet (documented in README; user decision).
- **Technical debt:** `state_builder.py` cosmetic stub remains (unused by exports — lifecycle engine reads real bracket state); website `/live` page folded into the homepage rather than a separate route.
- **Future enhancement:** GitHub Action for post-match automation (Phase 6B candidate); SHAP-based local explainability; bracket connector lines.

## 12. Recommended next step

Push to GitHub and complete the two platform connections (15 minutes of clicking), then operate the tournament through the semifinals/final — each matchday run will visibly shrink Elo fallback and grow the forecast-history charts. After the tournament: **Phase 7 — post-tournament backtesting and calibration analysis** (compare recorded forecasts against actual outcomes run-by-run using the append-safe history files; a natural, honest capstone). Phase 6B (GitHub Action automation) is optional before that.
