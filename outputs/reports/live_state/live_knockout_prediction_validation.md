# Live Knockout Prediction Validation

- Generated: 2026-07-20T06:05:48+00:00

| Check | Status | Message |
|---|---|---|
| matchup_file_exists | pass | C:\Users\abelp\Desktop\fifa-final-production\outputs\live_state\remaining_known_knockout_matchups.csv |
| known_unplayed_matchups_detected | warn | 0 matchups |
| feature_file_exists | pass | C:\Users\abelp\Desktop\fifa-final-production\outputs\live_state\live_knockout_match_features.csv |
| feature_columns_match_model | fail | missing: ['team_a_pre_match_elo', 'team_b_pre_match_elo', 'elo_difference', 'elo_expected_score_team_a', 'form_points_last_5_diff', 'win_rate_last_5_diff'] |
| probabilities_in_range | warn | no predicted rows |
| probabilities_sum_to_one | warn | no predicted rows |
| advancement_probabilities_sum_to_one | warn | no predicted rows |
| completed_matches_not_predicted | pass | 0 completed matches predicted |
| tbd_matches_not_predicted | pass | 0 TBD matches predicted |
| live_model_source_used_in_simulation | warn | no live predictions exist, so simulator fallback is expected |
| elo_fallback_usage_decreased | warn | fallback share 0.00% -> 0.00% |