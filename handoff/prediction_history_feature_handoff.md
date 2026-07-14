# Handoff — Prediction History (forecast audit trail)

**Date:** 2026-07-14 · **Status:** implemented, tested, previewed locally. **NOT pushed / NOT deployed** — awaiting review. No commit made yet.

## A. What this adds
A new **Prediction History** dashboard tab plus an automatic snapshot mechanism that preserves every meaningful production forecast. Viewers can see what the model predicted *before* a matchday, the tournament-level forecast at that moment, the per-match predictions, and — once matches complete — whether each prediction was correct, without ever altering the original probabilities.

It **only consumes and preserves existing forecast outputs**; it does not change how any prediction is produced.

## B. Architecture
- **Snapshot = the published `public_data` forecast at a point in time** (tournament-level odds + the then-upcoming matchday predictions + provenance metadata), assembled by `src/prediction_history/snapshot.py::build_snapshot`.
- **When archived:** inside `run_portfolio_refresh` — once **before** the update overwrites `public_data` (preserve the previous forecast) and once **after** a successful publish (capture the new one). Both idempotent; wrapped in try/except so archival can never break a refresh; skipped on `--dry-run`.
- **Dedup / "meaningful":** each snapshot carries a `state_hash` over `{phase, completed_matches, matchday predictions (teams + advance prob + method), champion probability table}`. Identical state → same hash → not re-archived. A new completed match, phase change, or materially different probabilities → new hash → new snapshot. (A trivial no-op re-simulation therefore does **not** create a duplicate.)
- **Storage (Git-friendly, append-only):** `data/prediction_history/manifest.json` (index) + `data/prediction_history/snapshots/<snapshot_id>.json` (one human-readable file per snapshot). `schema_version: "1.0"`. Resilient to a single malformed file.
- **Immutability + actual results:** snapshots are never mutated. At render time, `enrich_snapshot` joins each matchday prediction against the immutable committed `public_data/knockout_bracket.json` (completed winners) to derive `actual_winner` and `correct | incorrect | pending`.
- **Backfill:** `src/prediction_history/backfill.py` recovers **genuine** past forecasts by reading the exact `public_data` committed at each matchday commit (`git show <commit>:public_data/*.json`) — nothing is recomputed with today's model. Recovered snapshots are tagged `recovered_from_committed_output`; live-archived ones are `genuine_archived_forecast`.

## C. Files
**New**
- `src/prediction_history/__init__.py`, `config.py`, `snapshot.py`, `backfill.py`
- `dashboard/pages/9_Prediction_History.py`
- `tests/test_prediction_history.py` (10 tests)
- `data/prediction_history/manifest.json` + `snapshots/*.json` (5 backfilled snapshots)

**Modified (small, isolated)**
- `src/public_export/portfolio_refresh.py` — pre/post archival hook + `dry_run` param + manifest field.
- `dashboard/app.py` — registers the new page + nav pill (`Prediction History`, url `/history`).
- `main.py` — CLI: `archive-prediction-snapshot`, `backfill-prediction-history`, `prediction-history-summary`; `--dry-run` on `refresh-portfolio`.
- `src/public_export/commit_safety.py` — allowlists `data/prediction_history/manifest.json` and `snapshots/*.json` so the automated refresh workflow commits new snapshots.
- `.github/workflows/portfolio-refresh.yml` — passes `--dry-run` through so dry runs don't archive production snapshots.

**Untouched:** model, features, Elo, Monte Carlo, completed-match locking, live provider logic, `public_data/*`, `outputs/models/*`, and all other dashboard tabs.

## D. Snapshot schema (v1.0, real example — commit `4e4eca6`)
```json
{ "schema_version":"1.0", "snapshot_id":"20260711T000243Z__quarterfinal__98_completed",
  "generated_at":"2026-07-11T00:02:43+00:00", "display_date":"2026-07-11", "timezone":"UTC",
  "tournament_phase":"quarterfinal", "completed_matches":98, "provider":"football_data_org",
  "forecast_mode":"true_live_forecast", "source_quality_score":100, "simulation_count":10000, "seed":42,
  "record_class":"recovered_from_committed_output", "state_hash":"4907fe9260529eeb",
  "provenance":{"git_commit":"4e4eca66c","commit_subject":"Update live forecast: Spain 2-1 Belgium…"},
  "main_forecast":{ "most_likely_champion":{"team":"Spain","probability":0.3162},
    "most_likely_final":{"team_1":"Argentina","team_2":"Spain","probability":0.2674},
    "champion_probabilities":[…], "finalist_probabilities":[…] },
  "matchday_predictions":[ {"match_id":537385,"stage":"Quarterfinal","scheduled_at":"2026-07-11T21:00:00Z",
    "team_a":"Norway","team_b":"England","team_a_win_probability":0.3619,"team_b_win_probability":0.6381,
    "predicted_winner":"England","prediction_method":"XGBoost","status_at_snapshot":"scheduled",
    "actual_winner":null,"prediction_outcome":"pending"} ] }
```

## E. Dashboard tab
- Date selector (newest default); one snapshot per date (latest for that date); honesty banner distinguishing **Confirmed result / Historical prediction / Current prediction**.
- **Current Update** and **Previous Matchday Update** sections, each with: forecast card (most likely champion, projected final, champion-probability bars), matchday-prediction cards (predicted winner, both probabilities, method, actual result + CORRECT/INCORRECT/PENDING badge), and champion-probability **movement** vs the previous update. Provenance badge (Genuine / Recovered) shown per snapshot.
- Page-scoped CSS only (does not affect other tabs). Fails gracefully on empty/one/malformed history.

## F. Verification
- New tests **10 passed**; full suite **49 passed** (39 prior + 10 new).
- Backfill recovered **5 genuine committed forecasts** (QF 97 → SF 101); **8/9 resolved historical predictions correct (89%)**.
- Dashboard AppTest: new page + Overview/Evolution/Matchups all render, **0 failures**.
- `validate-public-exports` pass · `validate-dashboard` pass.
- **Regression:** `public_data/` and `outputs/models/` byte-identical (unchanged); current prediction numbers untouched; workflows valid.
- UI preview screenshot: `C:\Users\abelp\Desktop\FIFA_LinkedIn_Screenshots\prediction_history_tab.png`.

## G. How to run
```
python main.py backfill-prediction-history      # recover genuine past forecasts from Git (idempotent)
python main.py prediction-history-summary       # list snapshots + historical accuracy
python main.py archive-prediction-snapshot      # manually archive the currently-published forecast
python main.py refresh-portfolio --n-simulations 10000 --no-retrain   # now auto-archives (pre + post)
streamlit run dashboard/app.py                  # then open the "Prediction History" tab (/history)
```
From now on, every real matchday `refresh-portfolio` automatically archives a new snapshot when the state changes.

## H. Known limitations / notes
- Deep-linking directly to `/history` can show a brief Streamlit "page not found" toast on cold load; navigating via the tab pill is clean (cosmetic Streamlit multipage behaviour).
- The pipeline forecasts champion odds, not a discrete final-winner call; `predicted_final_winner` is stored `null` and the UI derives the projected-final favourite from champion odds (honest).
- Snapshots capture the *upcoming* matches' predictions; a completed match's prediction lives in the snapshot taken before it was played (that's the audit trail).

## I. Rollout after approval
Commit the feature (`src/prediction_history/`, `dashboard/pages/9_Prediction_History.py`, `tests/test_prediction_history.py`, the 5 backfilled snapshots under `data/prediction_history/`, and the small hooks in `portfolio_refresh.py` / `app.py` / `main.py` / `commit_safety.py` / the workflow), push, and Streamlit Cloud redeploys with the new tab. No website/Vercel change is required (this is dashboard-only).

## J. Status
**Nothing pushed, deployed, committed, or refreshed. Awaiting review.**
