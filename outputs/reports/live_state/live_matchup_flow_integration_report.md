# Live Matchup Flow Integration Check

- Generated: 2026-07-10T06:19:19+00:00
- Status: pass

Synthetic scenario: all four real quarterfinals are marked completed (team_a advances)
and the two semifinal pairings become known. Run in an isolated sandbox; production
live-state files are never modified.

| Check | Result | Detail |
|---|---|---|
| newly_resolved_matchups_detected | pass | 2 of 2 synthetic semifinals detected; 2 matchups total |
| completed_matches_excluded | pass | 0 completed QFs leaked into matchups |
| features_built_for_new_matchups | pass | 2 semifinal feature rows, predictable: [True, True] |
| model_predictions_generated | pass | 2 of 2 semifinals predicted by xgboost |
| simulator_uses_live_model_exact | pass | source for France vs Spain: live_model_exact |
| simulator_uses_live_model_reversed | pass | source for Spain vs France: live_model_reversed |
| elo_only_without_prediction | pass | source for pair without live prediction: elo_fallback |
| completed_results_locked_in_simulator | pass | completed QF returned winner=France, source=completed_result |