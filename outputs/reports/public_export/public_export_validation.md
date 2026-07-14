# Public Export Validation

- Generated: 2026-07-14T22:22:08+00:00

| Check | Status | Message |
|---|---|---|
| latest_overview.json:required_keys | pass | all required keys present |
| knockout_bracket.json:required_keys | pass | all required keys present |
| champion_forecast.json:required_keys | pass | all required keys present |
| finalist_forecast.json:required_keys | pass | all required keys present |
| finalist_pairs.json:required_keys | pass | all required keys present |
| matchup_predictions.json:required_keys | pass | all required keys present |
| teams.json:required_keys | pass | all required keys present |
| team_stats.json:required_keys | pass | all required keys present |
| system_health.json:required_keys | pass | all required keys present |
| latest_run_manifest.json:required_keys | pass | all required keys present |
| champion:probabilities_in_range | pass | all champion probabilities in [0,1] |
| champion:sums_to_one | pass | sum=1.0000 |
| finalist_pairs:sums_to_one | pass | sum=1.0000 |
| teams:status_vocabulary | pass | all statuses valid |
| teams:unique_slugs | pass | 48 unique team slugs |
| teams:no_placeholder_teams | pass | no TBD placeholder appears as a team |
| teams:eliminated_have_zero_probability | pass | no eliminated team carries championship probability |
| teams:eliminated_have_no_next_matchup | pass | no eliminated team has an active next matchup |
| champion:no_eliminated_candidates | pass | champion candidates are all non-eliminated |
| bracket:valid_states | pass | 31 matches with valid states |
| bracket:completed_have_scores | pass | all completed matches carry score and winner |
| bracket:source_vocabulary | pass | all bracket sources use the declared vocabulary |
| bracket:tbd_not_named | pass | TBD matches carry no team names |
| matchups:xgboost_backed | pass | all predicted matchups carry model name and live_model source |
| matchups:advance_sums_to_one | pass | max deviation 0.00000 |
| overview:phase_matches_manifest | pass | overview=semifinal manifest=semifinal |
| overview:provider_matches_manifest | pass | overview=football_data_org manifest=football_data_org |
| overview:forecast_mode_matches_manifest | pass | overview=true_live_forecast manifest=true_live_forecast |
| exports:timestamps_parseable | pass | all _meta.generated_at timestamps parse |
| exports:no_secret_values | pass | 5 secret values checked, 0 hits |
| exports:no_private_local_paths | pass | no private local paths in exports |