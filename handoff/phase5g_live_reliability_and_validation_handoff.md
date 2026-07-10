# Phase 5G Live Pipeline Reliability, Validation Cleanup, Performance, and Automation Hardening Handoff

Saved: 2026-07-09  
Scope: resolve the three long-standing data validation failures, harden the one-command matchday workflow, add phase-transition/freshness/source-progression/run-manifest auditability, and optimize live knockout feature generation with proven equivalence. No secrets are included. No dashboard was built.

## 1. Objective

Make the live forecasting system reliable, transparent, reproducible, efficient, and auditable for the rest of the knockout tournament, so that after every real round one command refreshes state, predicts newly resolved matchups with XGBoost, reruns the Monte Carlo forecast, validates it, and leaves an audit trail:

```bash
python main.py update --mode matchday --run-live-forecast --n-simulations 10000 --no-retrain
```

## 2. Previous State (Phase 5F)

- Live forecast worked end to end; 4 QF matchups predicted by XGBoost; Elo fallback share 42.35% (down from 99.63%).
- Broader refresh validation always reported `failed` (3 pre-existing checks).
- Live knockout feature build took roughly 4 minutes per run.
- No phase-transition tracking, no provider freshness metadata, no source-usage history, no run manifests.

## 3. Workstream A — The Three Validation Failures (root causes and fixes)

Full audit: `outputs/reports/data_validation_failure_audit.md`.

| Failure | Root cause | Severity | Fix | Final status |
|---|---|---|---|---|
| `matches_master / duplicate_same_date_same_teams` (868 rows) | Outdated assumption: the two Kaggle feeds intentionally both contribute rows (853 cross-feed World Cup duplicates + 15 same-day feed quirks; 110 with conflicting scores). Phase 3 deliberately dedupes downstream into `matches_master_feature_clean.csv` (verified: 0 duplicates). The check enforced zero duplicates at the wrong layer. | Low | Raw-master duplicates demoted to `warn` with explanation; **new fail-capable check** `feature_clean_no_duplicates` on the file features actually consume. | warn (expected) + new pass gate |
| `fixtures_2026 / non_null_team_a` (32) | Expected placeholder condition: exactly the 32 pre-tournament knockout template slots (`status=scheduled`), which Phase 3 explicitly preserves. | Low | `_check_fixture_team_names`: missing names on group-stage or completed fixtures still **fail**; scheduled knockout placeholders become a `warn` with count. | pass + warn (expected) |
| `fixtures_2026 / non_null_team_b` (32) | Same. | Low | Same. | pass + warn (expected) |

Validation was **not weakened**: both failure conditions were relocated to where they are genuine defects, and the expected conditions remain visible as warnings. `python main.py validate` now reports 22 pass / 3 warn / 0 fail, and the matchday update reports `validation: passed` for the first time.

**Related lineage defect fixed:** the Phase 5F live feature history read the raw `matches_master.csv` (with the 868 duplicates) while training features were built from the deduplicated feature-clean file. `_build_combined_history` now prefers `matches_master_feature_clean.csv` (raw master only as fallback), so live Elo/form replay no longer double-counts duplicated matches. The Phase 5F NaN-goal placeholder drop and (team, date±1) live-result dedup are preserved unchanged.

## 4. Workstream B — Matchday Workflow Hardening

Audited actual execution order of the matchday command: backup → refresh cleaners → rebuild master → broader validation → detect new completed matches → refresh fixture predictions (`--no-retrain` skips training) → live forecast pipeline (provider selection/fetch/normalize with last-good preservation → freshness metadata → live state build → quality gate → identify matchups → build features → predict with XGBoost → refresh remaining-match probabilities → Monte Carlo simulation → aggregation → validation → knockout prediction report/validation → phase transition → source history → manifest → reports). This matches the expected workflow; the audit found no ordering defects.

**New integration check (sandboxed, production data never modified):**

```bash
python main.py validate-live-matchup-flow
```

Simulates the quarterfinals completing and the semifinal pairings becoming known inside a temp directory, then verifies the full chain: newly resolved matchups detected → features built (predictable) → XGBoost predictions generated → simulator returns `live_model_exact` / `live_model_reversed` → Elo only when no prediction exists → completed matches locked with real winners. All 8 checks pass. Report: `outputs/reports/live_state/live_matchup_flow_integration_report.md`.

## 5. Workstream C — Phase-Transition Awareness

- New `outputs/live_state/tournament_phase_transition.json` written every forecast run: previous/current phase, `phase_changed`, `newly_resolved_matchups`, `newly_completed_matches` (all derived from actual state; the first recorded run is a baseline).
- End-of-matchday summary now states phase before/after, transition detected, newly completed matches, newly resolved matchups, and new XGBoost predictions generated.

## 6. Workstream D — Provider Rate-Limit Resilience

Audit findings: last-good normalized CSVs were already protected (`_write_normalized_csv` never overwrites non-empty files with empty frames); 429s were detected and cached normalized data used; snapshots sanitized. Gaps fixed:

- `Retry-After` header now honored once per request, capped at 15s (429 responses).
- New `outputs/live_state/live_provider_freshness.json` with `request_status`, `data_source_mode` (`fresh_api` / `cached_normalized` / `saved_snapshot` / `unavailable`), `fetched_at`, `normalized_at`, row counts, `cache_used`, `snapshot_used`, `data_age_minutes`, `rate_limited`.
- Observed live during verification: core matches request succeeded (200 → `fresh_api`, age 0.0 min) while a secondary diagnostic endpoint hit 429 → `rate_limited: true` disclosed honestly. Stale data can no longer pass silently as fresh; the quality gate remains the sole authority on forecast mode.

## 7. Workstream E — Feature Generation Performance (measured, equivalence-proven)

Root cause of the ~4-minute build was **not** primarily the Phase 3 row loop: `standardize_team_name()` without explicit mappings re-reads `team_name_map.csv` from disk on every call, and `_build_combined_history` made ~99k such calls.

Changes (no feature definitions, imputation, or model schema touched):

1. `_make_standardizer()` — loads the name map once, memoizes conversions (identical mapping function).
2. `_fast_team_match_history()` — vectorized equivalent of Phase 3 `calculate_team_match_history` (same rows, columns, ordering).
3. H2H/schedule inputs restricted to rows those functions can actually read (same pair / same team) — provable input-equivalence reductions.
4. The original path is preserved (`build_live_knockout_features(use_fast=False)`) and the fast path is default **only because equivalence passes**.

Equivalence + benchmark (`python main.py validate-live-feature-equivalence`, report `outputs/reports/live_state/live_feature_cache_validation.md`):

```text
Rows compared: 4 (all current matchups) x 28 model feature columns = 112 values
Exact matches: 112 | Tolerance-only: 0 | Mismatches: 0 | Max abs diff: 0.0
Measured runtime, Phase 5F as shipped:   245.3s
Measured runtime, original path + map fix: 4.9s
Measured runtime, fast path (default):     1.7s   (~144x vs as-shipped)
```

Leakage safety re-verified after optimization: only completed matches enter history (NaN-goal placeholders dropped), the target matchup never enters its own history (placeholder rows are excluded by shift(1)), rest days come from the latest legitimate completed match, and `validate-features` leakage checks still pass.

## 8. Workstream F — Probability-Source Progression

- Append-safe `outputs/live_state/probability_source_history.csv`: one row per forecast run (run_id-deduplicated) with phase, simulation count, matchups, per-source counts, model-driven %, fallback %.
- `outputs/reports/live_state/probability_source_progression.md`: per-run table + previous-vs-current comparison + the fixed 99.63% Phase 5E reference baseline. Only observed values are recorded; nothing is projected.

## 9. Workstream G — Strengthened Live Integrity Validation

`validate-live-forecast` grew from 9 to 19 checks, all with genuine failure conditions, including: completed results locked (probabilities fixed, source `completed_result`, never simulated); probability-source vocabulary enforced (fallback can never masquerade as a model label); `live_model_*` labels must be backed by actual prediction rows; resolved matchups with live predictions must actually use them; no eliminated team as champion/finalist (survivors = unplayed known matchup teams + completed-match winners − completed-match losers); no placeholder teams in outputs; probabilities in [0,1]; forecast mode agrees with the quality gate; provider freshness disclosed. Machine-readable CSV + Markdown reports as before.

Two of the new checks initially fired false positives when France's quarterfinal completed mid-verification (a team whose next slot is TBD was counted as eliminated; the gate cross-check ran mid-pipeline before the enriched summary existed). Both were fixed and the checks now pass against the real transitioned state — a genuine live-fire test of the validation suite.

## 10. Workstream H — Run Manifests

`outputs/live_state/latest_live_run_manifest.json` written on every forecast run with actual values: run_id, start/end timestamps, provider, forecast mode, quality score, phase, simulation count, seed, selected model, matchup/prediction counts, both validation statuses, phase transition, data_source_mode, provider data age, rate-limit flag, broader refresh validation status, top pair/champion, and per-source probability counts.

## 11. Files Added / Modified

Added:
- `src/live_state/run_audit.py` — transitions, source history, progression report, manifests
- `src/live_state/integration_checks.py` — sandboxed resolved-matchup flow check
- `outputs/reports/data_validation_failure_audit.md`

Modified:
- `src/validation/validate_data.py` — duplicate check demoted to warn + new feature-clean fail gate; fixture team-name check split (placeholders warn, real gaps fail)
- `src/live_state/live_matchup_features.py` — feature-clean lineage, cached standardizer, fast history path, H2H/schedule input restrictions, equivalence validator
- `src/live_state/live_validation.py` — 10 new integrity checks
- `src/live_state/live_pipeline.py` — run_id/timing, transition + history + manifest wiring
- `src/live_state/live_reports.py` — end-of-matchday phase-transition lines
- `src/live_state/providers/football_data_org_provider.py` — Retry-After handling, freshness metadata
- `main.py` — new commands

CLI added:

```bash
python main.py validate-live-feature-equivalence
python main.py validate-live-matchup-flow
```

## 12. Verification Run (all executed, exact results)

```text
python -m compileall src main.py scripts               -> pass
python main.py validate                                -> 22 pass / 3 warn / 0 fail
python main.py validate-features                       -> pass (incl. leakage checks)
python main.py validate-simulation / validate-bracket  -> pass / pass
python main.py identify-live-knockout-matchups         -> 4 matchups (pre-QF1), then 3 after France completed
python main.py build-live-knockout-features            -> complete features, 0 missing values
python main.py predict-live-knockout                   -> all remaining matchups predicted (xgboost), 0 failed
python main.py live-knockout-prediction-summary        -> pass (all checks)
python main.py validate-live-feature-equivalence       -> pass (112/112 exact, 245.3s -> 1.7s)
python main.py validate-live-matchup-flow              -> pass (8/8 sandbox checks)
python main.py run-live-forecast --n-simulations 1000 --seed 42 (x2) -> success; outputs byte-identical (seed reproducibility)
python main.py run-live-forecast --n-simulations 10000 -> success; validate-live-forecast pass (19/19 checks)
python main.py update --mode matchday --run-live-forecast --n-simulations 1000 --no-retrain
                                                       -> validation: passed, live forecast: success
Secret scan (all .env values vs outputs/src/handoff/scripts) -> 0 hits; .env untracked
```

## 13. Current Forecast State (real tournament moved during this phase)

France defeated Morocco 2-0 in the first quarterfinal during verification — a live test of the whole system:

```text
Provider: football_data_org (fresh_api, data age 0 min; one secondary endpoint rate-limited and disclosed)
Forecast mode: true_live_forecast | Source quality score: 100
Current phase: quarterfinal | Completed fixtures: 97
Known unresolved knockout matchups: 3 (Spain-Belgium, Norway-England, Argentina-Switzerland)
Live XGBoost predictions available: 3 of 3
10,000-run: top champion France 0.2949; top finalist pair Argentina vs France 0.2607
1,000-run source counts: completed_result 1000, live_model_exact 3000, elo_fallback 2945, model_reversed 55
Model-driven share ~43.6%; fallback ~42.1%; completed-result locked share ~14.3%
Live forecast validation: pass (19 checks) | Broader refresh validation: passed
```

The France result was automatically locked as a completed result (never re-simulated), Morocco no longer appears as a possible finalist/champion, and France's completed match is excluded from prediction — all confirmed by the validation suite.

## 14. Known Limitations

- **Expected limitation:** semifinal/final pairings inside simulation branches use Elo until real participants are known; fallback share shrinks automatically each round (observable in the progression report).
- **Expected limitation:** `newly_completed_matches` counts runs against the previous forecast run's baseline; the first recorded run establishes the baseline.
- **Technical debt:** the state snapshot stub (`state_builder.py`, all teams "still_alive") remains cosmetic-only and unfixed (documented since the Phase 5F audit).
- **Technical debt:** diagnose makes ~15 provider requests per cycle; on the free tier some secondary endpoints 429 (disclosed in freshness metadata; core data unaffected).
- **Requires new real-world data:** further fallback reduction requires the remaining quarterfinals/semifinals to be played.

## 15. Recommended Next Step

Operate the tournament: run `python main.py update --mode matchday --run-live-forecast --n-simulations 10000 --no-retrain` after each remaining knockout round; the transition JSON, progression report, and manifest now document each step automatically. When the tournament completes, consider the dashboard phase — the pipeline is now stable and auditable enough to present.
