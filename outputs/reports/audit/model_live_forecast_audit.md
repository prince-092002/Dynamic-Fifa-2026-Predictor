# Model + Live Forecast Audit — FIFA 2026 Tournament Outcome Predictor

- Audit date: 2026-07-08 (America), 2026-07-09 UTC
- Auditor: automated phase check (Claude Code)
- Scope: live data pipeline, model prediction pipeline, Monte Carlo finalist/champion forecast, matchday update integration, report consistency, secret hygiene.

---

## 1. Executive Summary

The live forecast pipeline is **running correctly and honestly**. football-data.org is selected on merit (it is the only provider returning real 2026 rows), the quality gate reports `true_live_forecast` with a source quality score of 100, all 96 completed real results are locked and never re-simulated, and the Monte Carlo simulator starts from the actual current quarterfinal bracket (France–Morocco, Spain–Belgium, Norway–England, Argentina–Switzerland). Probability outputs are internally consistent (finalist pairs and champion probabilities each sum to exactly 1.0), reproducible under a fixed seed, and stable between 1,000- and 10,000-run tests. No API keys or tokens appear in any output or report file, and `.env` is gitignored and untracked.

Two issues were found. One small reporting bug (a phase-label mismatch between the validation report and every other artifact) was fixed during the audit with a 4-line change. One cosmetic data quality issue (the tournament state snapshot marks all 48 teams "still_alive") was documented but not fixed because it does not feed the forecast. Details in sections 11–13.

**Headline results (current bracket state):**

| Test | Top finalist pair | Top champion |
|---|---|---|
| 1,000 runs (seed 42) | Argentina vs France — 0.1600 | Argentina — 0.2090 |
| 10,000 runs | Argentina vs France — 0.1512 | Argentina — 0.2359 |

The 1,000-run results match the handoff exactly (0.1600 / 0.2090), confirming reproducibility of the previously reported numbers.

---

## 2. Pass/Fail Checklist

| Check | Result |
|---|---|
| Compile passes (`compileall src main.py scripts`) | **yes** |
| football-data.org selected | **yes** (score 105 vs 0 for all others) |
| true_live_forecast mode | **yes** |
| Completed results locked | **yes** (96/96 locked at probability 1/0, source `completed_result`) |
| Selected model exists | **yes** (`selected_model.joblib`, 1.7 MB, XGBoost) |
| Prediction probabilities valid | **yes** (51 predicted rows sum to exactly 1.0, all in [0,1]) |
| Feature validation passed | **yes** |
| Leakage checks passed | **yes** |
| Live forecast 1,000-run passed | **yes** (validation: pass) |
| Live forecast 10,000-run passed | **yes** (validation: pass) |
| Finalist probabilities sum to 1 | **yes** (1.0000 exactly) |
| Champion probabilities sum to 1 | **yes** (1.0000 exactly) |
| No eliminated teams simulated | **yes** (only the 8 live QF teams appear as finalists/champions) |
| Matchday update works | **yes** (live forecast: success; see section 10 for the separate refresh-validation caveat) |
| Fallback usage reported | **yes** (9.68%, clearly labeled as bracket-template mapping for TBD slots) |
| No secrets exposed | **yes** (0 files contain any `.env` value; `.env` untracked and gitignored) |

---

## 3. Live Provider Status

All five diagnostics commands ran successfully.

| Provider | Status | Fixtures | Completed | Standings | Bracket | Score |
|---|---|---:|---:|---:|---:|---:|
| football_data_org | available_true_live | 104 | 96 | 144 | 32 | 105 |
| api_football | no_2026_rows | 0 | 0 | 0 | 0 | 0 |
| sportmonks | credentials_missing | 0 | 0 | 0 | 0 | 0 |
| fifa_official | endpoint_error | 0 | 0 | 0 | 0 | 0 |
| manual_live | no_2026_rows | 0 | 0 | 0 | 0 | 0 |

- Diagnostics report *token present: True* without printing the token value.
- Selection is data-driven (`src/live_state/provider_registry.py::_selection_score`): points for fixtures, completed results, standings, bracket, and true-live capability; penalties for missing credentials / no 2026 rows / endpoint errors. football-data.org wins because it is the only provider returning real 2026 data — exactly the intended behavior. API-Football remains registered (priority 1) but scores 0 due to `no_2026_rows`, so it would automatically take over only if it started returning data and outscored football-data.org.

### Live data quality (normalized files)

- **Fixtures (104 rows):** 96 `FINISHED` + 8 `TIMED` (4 QF with named teams, 2 SF, 1 third-place, 1 final as TBD). No missing team names, goals, or winners on any completed match. All 96 winners agree with the recorded scores (draws labeled `Draw`; knockout ties resolved by the penalty-goal columns).
- **Teams (48 rows):** no empty names, no duplicates.
- **Standings (144 rows):** 48 teams × 3 rows each — these are the provider's TOTAL/HOME/AWAY splits (verified: France 3 played total = 2 home + 1 away). The `group` column carries the provider's `GROUP_STAGE` label rather than per-group letters; per-group tables are computed separately into `current_group_standings.csv`. Usable, with one cosmetic caveat (see Remaining Risks).
- **Bracket (32 rows):** 16 R32 + 8 R16 + 4 QF + 2 SF + 1 third-place + 1 final. All completed knockout rows carry winners; the 4 scheduled QFs have real team names; SF/third-place/final are correctly TBD.
- **Knockout representation:** the 32 `is_knockout` fixture rows match the bracket file one-for-one.

## 4. Quality Gate Status

`live_forecast_quality_gate.json`:

- forecast_mode: `true_live_forecast`; public label: "True live forecast from current tournament state"
- source_quality_score: 100 (level: high)
- current_phase: `quarterfinal` (correct — R16 finished, QFs scheduled)
- fixture coverage 1.0, completed-result coverage 1.0, standings coverage 1.0, bracket live coverage 0.9032
- fallback_usage_rate: 0.0968 — fully explained: the merged bracket used by the simulator has 31 rows (third-place playoff excluded, which is why the gate says 31 while the raw provider bracket has 32); 28 rows come from `football_data_org_live` and the 3 still-TBD slots (2 semifinals + final) come from the fallback bracket template. 3/31 = 9.68%. The fallback is a *structure mapping* for unresolved slots, not fabricated results, and is never labeled as live data.
- The gate blocks fallback-only forecasts by default; `--allow-fallback-forecast` exists as an explicit opt-in for testing only.

## 5. Model Prediction Status

- `outputs/models/selected_model.joblib` exists; selected model is **XGBoost**, matching the modeling summary. Test metrics: accuracy 0.607, log loss 0.861, Brier 0.506 — reasonable for 3-class football prediction. (Known weakness: draw recall ≈ 0.01; the model almost never predicts draws, which matters less in knockout simulation where draws convert to advancement probability.)
- `fixture_2026_match_predictions.csv`: 104 rows. Required columns all present (`prob_team_a_loss`, `prob_draw`, `prob_team_a_win`, `predicted_result_label`, `confidence`, `model_name`, `prediction_status`).
- 51 rows predicted — probabilities all in [0,1] and sum to exactly 1.0 per match.
- 53 rows unpredictable (pre-tournament playoff placeholders like "Winner UEFA Playoff A" and `TBD_Team_A/B` knockout slots) — **kept in the file** and explicitly flagged `not_predictable_tbd_or_missing_features`, not silently removed.
- `predict-fixtures` re-ran cleanly during the audit (51 predicted rows, unchanged).

### Model vs Elo fallback in the live simulation

The live simulator's probability ladder is: (1) completed result → locked; (2) exact `match_id` in the prediction file with status `predicted`; (3) team-pair lookup in the prediction file (including reversed order); (4) Elo/rating fallback. Source counts from the 10,000-run test: ~99.6% `elo_fallback`, ~0.4% `model_reversed`. This is **correct behavior, not a bug**: the prediction file was generated from the pre-tournament fixture template, whose knockout rows are TBD placeholders, so no exact model prediction exists for the resolved QF pairings (none of the four QF pairs met earlier in the tournament either). The rare `model_reversed` hits are simulated SF/Final pairings that happen to replicate a predicted group-stage matchup (e.g., Norway vs France). Elo fallback is used only where model probabilities are genuinely unavailable — as specified. See Recommended Next Step for how to raise model usage.

## 6. Feature / Leakage Status

- `validate-features`: **pass** (both the feature validation and the leakage check).
- Leakage checks (`src/features/leakage_checks.py`) verify: no target columns in the model feature list, no suspicious post-match/future column names, pre-match Elo columns present, no current-ratings columns in historical training data.
- Rolling/form features verified directly in code: `form_features.py` and `goal_features.py` sort by `team, date, match_id` and apply `shift(1)` **before** rolling windows — features are strictly pre-match and chronological.
- Completed 2026 results enter the live forecast only as locked current-state outcomes; they are not fed back into model features for future-match predictions (the model was trained pre-tournament and is not retrained by the matchday flow when `--no-retrain` is used).

## 7. Simulation Status

- 1,000-run (seed 42): top pair Argentina vs France 0.1600; top champion Argentina 0.2090 — **identical to the handoff figures**.
- Reproducibility: two consecutive seed-42 runs produced byte-identical pair and champion probability files.
- 10,000-run: top pair Argentina vs France 0.1512; top champion Argentina 0.2359. Champion probabilities move by at most 0.027 between 1k and 10k — consistent with expected Monte Carlo noise at n=1,000 (σ ≈ 1.3%), i.e., 10k results are more stable, no systematic disagreement.
- `validate-live-forecast`: **pass** after both runs.
- Finalist pair probabilities sum: 1.0000. Champion probabilities sum: 1.0000. Reach-final probabilities sum: 2.0000 (correct — two finalist slots).
- Champion order at 10k: Argentina 0.236, France 0.191, England 0.187, Spain 0.187, Morocco 0.071, Belgium 0.070, Switzerland 0.040, Norway 0.019.
- **No eliminated or invalid team appears** in any output — finalists, reach-final, and champion tables contain only the 8 live quarterfinalists.
- Top pairs are bracket-plausible: every high-probability pair crosses the two bracket halves (SF1 = W(Fra/Mor) vs W(Spa/Bel); SF2 = W(Nor/Eng) vs W(Arg/Sui)), verified against the per-simulation match sample.

## 8. Completed Result Locking Check

- Completed matches: **96**. All 96 appear in `remaining_match_probabilities.csv` with `probability_source = completed_result`, probabilities fixed at 1/0 (0.5/0.5 advancement only for group-stage draws, which is correct), and `is_simulated = False`.
- Simulated remaining matches per simulation run: **7** (4 QF + 2 SF + 1 Final; the third-place playoff is not simulated because it does not affect finalist/champion outputs).
- Completed matches incorrectly simulated: **0** — the per-simulation match sample contains only Quarterfinal/Semifinal/Final rows, and `_simulate_or_lock_knockout_match` returns the recorded winner for any row with `is_completed` and a known winner.
- Missing winners on completed matches: **0**.
- Eliminated teams never advance: the forward simulator starts from the deepest bracket stage where all teams are known (currently the QF row set), so eliminated teams are structurally excluded.

## 9. Finalist Prediction Logic Check

Code inspected: `src/live_state/finalist_simulator.py`, `src/live_state/finalist_aggregation.py`.

- **Order-insensitive pairs:** finalist pair keys are built from `sorted([finalist_1, finalist_2])` joined with " vs " — Argentina vs France and France vs Argentina count as one pair. Verified: zero duplicate unordered pairs in the output.
- **Pair probability = count / simulations** (`finalist_aggregation.py` line 18). ✔
- **Reach-final counts both slots** (both `finalist_1` and `finalist_2` columns are pooled). ✔
- **Champion probability = champion count / simulations.** ✔
- **Runner-up** = the final's loser (`_simulate_live_bracket_forward` returns `runner_up = final["loser"]`). ✔
- **Semifinal/final handling:** QF winners are paired in bracket-row order into semis, SF winners into the final; a separate `_simulate_known_semis_or_final` path handles states where semis or the final are already known, locking a completed final's winner.
- **Starts from current state:** the simulator scans Final → Semifinal → Quarterfinal → … and starts at the deepest stage with a full set of known teams — currently the 4 live QF matchups, **not** the pre-tournament state. The pre-tournament group-stage simulation path exists only as a fallback when no live bracket is resolvable, and did not trigger in any test run.

## 10. Matchday Update Integration Check

`python main.py update --mode matchday --run-live-forecast --n-simulations 1000 --no-retrain`:

- **Live forecast status: success** (mode `true_live_forecast`, phase quarterfinal, top pair Argentina vs France 0.16, top champion Argentina 0.209).
- End-of-matchday report written: `outputs/reports/live_state/end_of_matchday_update_summary.md`.
- The normalized football-data.org files were refreshed in place (same 104/96/48/32 row counts after the run) — the update did **not** erase good live data.
- Broader refresh validation reported **failed (3 checks)**, and this is correctly **separated** from live forecast validation (which passed). The 3 failures are pre-existing, non-live issues:
  1. `matches_master`: 868 duplicate same-date team rows in the historical dataset.
  2–3. `fixtures_2026`: 32 missing `team_a`/`team_b` — these are the pre-tournament template's TBD knockout rows; the check does not exempt knockout placeholders.
  Neither affects the live forecast, which reads the normalized live fixture/bracket files. They should still be cleaned up (see Remaining Risks).
- Note: API-Football returned 0 fixture rows during the refresh (expected, no 2026 access), so the update fell back to existing processed CSVs for the historical/master refresh while the live forecast used football-data.org — the intended division of labor.

## 11. Output Consistency Check

Compared `live_forecast_summary.json`, `finalist_prediction_summary.md`, `live_validation_report.md`, `live_forecast_quality_gate.json`, `provider_selection_report.md`:

| Field | Consistent? |
|---|---|
| Selected provider (football_data_org) | yes |
| Current phase (quarterfinal) | **yes after fix** — validation report previously said `round_of_16` (bug, fixed; see section 12) |
| Forecast mode (true_live_forecast) | yes |
| Fixture counts (104 / 96 completed) | yes |
| Fallback usage (9.68%) | yes (gate reports 31 merged-bracket rows vs 32 raw provider rows — explained, not a conflict: the merged bracket excludes the third-place playoff) |
| Top finalist pair / top champion | yes (all artifacts reflect the most recent 1,000-run: Argentina vs France 0.1600 / Argentina 0.2090) |
| Finalist prediction active (true) | yes |

## 12. Bugs Found and Fixes Made

**Bug 1 (fixed): phase-label mismatch in the live validation report.**
`src/live_state/live_validation.py` read the current phase from `current_tournament_state.csv`, which is populated by a *different* phase detector (`live_config.detect_current_phase`) that returns the deepest stage with a **completed** match ("round_of_16") instead of the stage currently being played ("quarterfinal", as the quality gate's detector reports). The validation report therefore contradicted every other artifact.
*Fix applied:* the validation now reads `current_phase` from `live_forecast_quality_gate.json` (the authoritative source), falling back to the state CSV only if the gate file is missing. Re-ran `validate-live-forecast`: pass, `phase=quarterfinal`. Four lines changed; no model or simulation logic touched.

**Bug 2 (documented, not fixed): tournament state snapshot is a stub.**
`src/live_state/state_builder.py` hardcodes `current_status="still_alive"`, `eliminated=False`, `still_alive=True` for all 48 teams, labels every group "STAGE", and takes per-team stats from the last (away-split) standings row, so `matches_played`/`points` are wrong. **This does not affect forecasts** — the simulator uses `merged_bracket_state.csv` and the quality gate uses its own detector; the state file feeds only cosmetic report fields. Left unfixed because a correct implementation (deriving elimination from knockout results) is a real feature, not a small bug fix.

**Not bugs (investigated and cleared):**
- Heavy Elo fallback in simulation (~99.6%) — correct given the prediction file only covers pre-tournament resolvable fixtures (section 5).
- Quality gate `bracket_rows: 31` vs provider bracket 32 — different files by design (merged bracket excludes third-place playoff).
- Standings 144 rows for 48 teams — provider TOTAL/HOME/AWAY splits, not duplication.

## 13. Remaining Risks

1. **Semifinal pairing depends on bracket-row order.** QF winners are paired `winners[0] vs winners[1]`, `winners[2] vs winners[3]` in merged-bracket row order rather than via explicit progression links. The order currently matches football-data.org's fixture-id sequence and produces the correct halves, but a provider re-ordering would silently scramble semifinal pairings. Low likelihood, high impact — worth an explicit progression mapping or an ordering assertion.
2. **Model is underused in the knockout forecast.** Champion probabilities are effectively Elo-driven right now. If the model is meant to drive the live forecast, regenerate fixture features/predictions for the resolved knockout matchups after each round.
3. **State snapshot stub** (Bug 2) could mislead anyone reading `current_tournament_state.csv` directly.
4. **Pre-existing refresh-validation failures** (868 historical duplicates; TBD-placeholder team-name checks) will keep flagging every matchday update as "validation: failed", which risks alert fatigue and masking a real future failure.
5. **Draw recall ≈ 0.01** in the classifier — acceptable for knockout advancement, but group-stage simulations (used only in the fallback path) would under-produce draws from model probabilities.
6. **Mojibake in team names** ("Curaçao" renders as "Cura?ao") in some CSVs — encoding, cosmetic only.

## 14. Recommended Next Step

Regenerate model predictions for the resolved knockout bracket after each completed round — i.e., build fixture features for the actual QF/SF/Final matchups from the live bracket and run `predict-fixtures` on them — so the live forecast uses XGBoost probabilities instead of Elo fallback for the matches that decide the championship. This is the single highest-leverage improvement; the pipeline plumbing (probability-source ladder) already prefers model predictions whenever they exist.

---

*Audit runs executed: `compileall`, `diagnose-football-data-org`, `diagnose-live-providers`, `select-live-provider`, `live-source-summary`, `live-quality-gate`, `modeling-summary`, `predict-fixtures`, `validate-features`, `run-live-forecast` (1,000 × 2 for seed reproducibility, then 10,000), `validate-live-forecast` (×3), `live-forecast-summary`, `update --mode matchday --run-live-forecast --n-simulations 1000 --no-retrain`. No secrets printed at any point; no completed real result was overwritten.*
