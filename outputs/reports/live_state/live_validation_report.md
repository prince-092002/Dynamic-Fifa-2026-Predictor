# Live Forecast Validation Report

| Check | Status | Message | Rows affected |
|---|---|---|---:|
| live_quality_gate_exists | pass | C:\Users\abelp\Desktop\Fifa Project\outputs\live_state\live_forecast_quality_gate.json | 0 |
| forecast_mode_clear | pass | mode=true_live_forecast; label=True live forecast from current tournament state | 0 |
| live_fixtures_file_exists | pass | C:\Users\abelp\Desktop\Fifa Project\outputs\live_state\live_fixtures_normalized.csv | 0 |
| current_state_exists | pass | C:\Users\abelp\Desktop\Fifa Project\outputs\live_state\current_tournament_state.csv | 0 |
| remaining_matches_have_probabilities | pass | 0 simulated rows missing probabilities | 0 |
| finalist_pair_probability_sum | pass | sum=1.0000 | 0 |
| champion_probability_sum | pass | sum=1.0000 | 0 |
| fallback_usage_reported | pass | C:\Users\abelp\Desktop\Fifa Project\outputs\reports\live_state\live_bracket_source_report.md | 0 |
| current_phase_detected | pass | phase=quarterfinal; relevance=finalist_prediction_active | 0 |
| completed_results_locked | pass | 97 completed rows; 0 marked simulated, 0 mislabeled sources, 0 without locked probabilities | 0 |
| probability_source_labels_valid | pass | all probability_source labels are from the declared vocabulary | 0 |
| live_model_labels_backed_by_predictions | pass | 0 rows labeled live_model_* without a matching predicted matchup | 0 |
| live_model_used_when_prediction_exists | pass | 0 resolved matchups with live predictions not using them | 0 |
| no_eliminated_team_as_champion | pass | all 7 champion candidates are in the surviving bracket (7 teams) | 0 |
| no_eliminated_team_as_finalist | pass | all finalist teams are in the surviving bracket | 0 |
| no_placeholder_teams_in_outputs | pass | no TBD/placeholder team appears in forecast outputs | 0 |
| probabilities_numerically_valid | pass | champion probabilities within [0, 1] | 0 |
| forecast_mode_agrees_with_gate | pass | summary=true_live_forecast gate=true_live_forecast | 0 |
| provider_freshness_disclosed | pass | data_source_mode=fresh_api, cache_used=False, snapshot_used=False | 0 |