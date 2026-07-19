# Live Knockout Prediction Validation

- Generated: 2026-07-19T18:07:41+00:00

| Check | Status | Message |
|---|---|---|
| matchup_file_exists | pass | C:\Users\abelp\Desktop\Dynamic-Fifa-2026-Predictor-PreFinal\outputs\live_state\remaining_known_knockout_matchups.csv |
| known_unplayed_matchups_detected | pass | 1 matchups |
| feature_file_exists | pass | C:\Users\abelp\Desktop\Dynamic-Fifa-2026-Predictor-PreFinal\outputs\live_state\live_knockout_match_features.csv |
| feature_columns_match_model | pass | all model feature columns present |
| probabilities_in_range | pass | all probabilities within [0, 1] |
| probabilities_sum_to_one | pass | max deviation 0.00000 |
| advancement_probabilities_sum_to_one | pass | max deviation 0.00000 |
| completed_matches_not_predicted | pass | 0 completed matches predicted |
| tbd_matches_not_predicted | pass | 0 TBD matches predicted |
| live_model_source_used_in_simulation | pass | live_model_exact + live_model_reversed = 10000 |
| elo_fallback_usage_decreased | warn | fallback share 0.00% -> 0.00% |