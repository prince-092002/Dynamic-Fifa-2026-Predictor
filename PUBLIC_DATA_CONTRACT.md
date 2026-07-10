# Public Data Contract

Stable, public-safe JSON contracts under `public_data/`, produced by `python main.py build-public-exports` (also run automatically at the end of every live forecast). Consumed by the Vercel website (build-time `fs` reads) and the Streamlit dashboard (cached loaders). Validated by `python main.py validate-public-exports`.

Every file carries `_meta` with `generated_at` (ISO UTC) and `source_files` (repo-relative backend sources); forecast-bearing files also carry `provider`, `forecast_mode`, `current_phase`, and `run_id`. No secrets, credentials, or absolute local paths ever appear (enforced by validation). Files that cannot be sourced are **not written** — consumers must handle absence gracefully.

| File | Purpose | Producer source | Required | Missing behavior |
|---|---|---|---|---|
| `latest_overview.json` | Homepage/dashboard snapshot: phase, counts, favorite, mode, freshness, validation | forecast summary + quality gate + freshness + manifest | yes | apps show "run pipeline first" notice |
| `knockout_bracket.json` | Bracket rounds with per-match `state` (`completed` / `scheduled_known` / `tbd`), scores, winners, advance probabilities, `source` + `source_label` | merged bracket + fixtures + live predictions | yes | bracket section hidden with notice |
| `champion_forecast.json` | `entries[]: {team, slug, champion_probability}` + `simulations` | live champion probabilities CSV | yes | forecast section shows notice |
| `finalist_forecast.json` | `entries[]: {team, slug, reach_final_probability}` | reach-final probabilities CSV | yes | section hidden |
| `finalist_pairs.json` | `entries[]: {finalist_team_1/2, finalist_pair_key, probability}` | finalist pair probabilities CSV | yes | section hidden |
| `matchup_predictions.json` | `matchups[]` with advance probabilities, favorite, `prediction_status`, raw `probability_source` + human `source_label` | live knockout predictions CSV | yes | "no unresolved matchups" notice |
| `teams.json` | `teams[]`: identity (slug/code/flag/group), lifecycle `status` (`alive`/`eliminated`/`champion`/`runner_up`/`third_place`), stage reached, elimination info, record, forecast probabilities, next matchup | teams + bracket lifecycle + stats engine | yes | team pages unavailable notice |
| `team_stats.json` | per-slug record + full match list (completed real matches only, deduplicated by fixture_id) | provider fixtures | yes | journey table shows notice |
| `forecast_history.json` | champion/finalist/pair probability snapshots per recorded run | append-safe history CSVs | optional | "history will appear after additional runs" |
| `probability_source_history.json` | per-run source counts + model-driven/fallback shares | probability_source_history.csv | optional | progression chart hidden |
| `system_health.json` | provider freshness, quality gate, validation pass/warn/fail counts | freshness + gate + validation reports | yes | health page shows notice |
| `latest_run_manifest.json` | complete audit manifest of the latest forecast run | run manifest | yes | audit page shows notice |
| `model_insights.json` | model comparison metrics, 28 feature columns, global XGBoost feature importances | model registry + selected model artifact | optional | methodology omits metrics/importance |

Probability conventions: stored unrounded (6 dp); display-side rounding only. Eliminated teams carry `champion_probability: 0.0` and `next_matchup: null` (validated). TBD bracket slots never carry team names (validated). Source vocabulary is closed: `completed_result`, `live_model(_exact/_reversed)`, `model_exact/_reversed/_prediction_file`, `elo_fallback`, `neutral_fallback`, `unresolved_tbd` (validated).

Freshness: regenerate via the matchday command after each completed real match. `_meta.generated_at` plus `latest_overview.json.data_age_minutes` tell consumers exactly how fresh the data is; the website additionally displays `data_source_mode` so cached/snapshot data is never presented as fresh.
