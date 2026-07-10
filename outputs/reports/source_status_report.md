# Source Status Report

| Source | Purpose | Credential required | Status | Rows fetched | Raw output path | Processed output path | Issue | Next action |
|---|---|---|---|---:|---|---|---|---|
| Kaggle international results | Historical international training matches | yes | loaded | 49502 | C:\Users\abelp\Desktop\Fifa Project\data\raw\kaggle\international_results\former_names.csv | C:\Users\abelp\Desktop\Fifa Project\data\processed\historical_international_matches.csv |  |  |
| Kaggle World Cup historical | Historical World Cup matches | yes | loaded | 964 | C:\Users\abelp\Desktop\Fifa Project\data\raw\kaggle\world_cup_historical\fifa_ranking_2022-10-06.csv | C:\Users\abelp\Desktop\Fifa Project\data\processed\historical_world_cup_matches.csv |  |  |
| Kaggle 2026 schedule | Unofficial 2026 fixture fallback | yes | loaded | 104 | C:\Users\abelp\Desktop\Fifa Project\data\raw\kaggle\world_cup_2026_schedule\host_cities.csv | C:\Users\abelp\Desktop\Fifa Project\data\processed\fixtures_2026.csv |  |  |
| API-Football | Live FIFA World Cup 2026 fixtures, results, teams, standings, and stats | yes | empty | 0 | data/raw/api_football/ | data/processed/fixtures_2026_api_football.csv; data/processed/results_2026_api_football.csv | API-Football team stats need a specific team id; fetch teams first, then call this per team. | Use manual/Kaggle fallback or verify API league/season availability. |
| World Football Elo Ratings | Current national team Elo ratings | no | success | 211 | data/raw/elo/world_football_elo_current.csv | data/processed/team_ratings.csv |  |  |
| FBref team stats | World Cup team stats | no | skipped | 0 |  |  | --skip-fbref was used | Use manual team stats or rerun without --skip-fbref. |
| FBref player stats | World Cup player stats | no | skipped | 0 |  |  | --skip-fbref was used | Use manual player stats or rerun without --skip-fbref. |
| Manual fixtures fallback | Manual 2026 fixtures | no | missing | 0 |  |  | no_real_manual_rows | Add real rows to data/raw/manual/manual_fixtures_2026.csv. |
| Manual results fallback | Manual 2026 results | no | missing | 0 |  |  | no_real_manual_rows | Add real rows to data/raw/manual/manual_results_2026.csv. |
| Manual team ratings fallback | Manual team ratings | no | missing | 0 |  |  | no_real_manual_rows | Add real rows to data/raw/manual/manual_team_ratings.csv. |
| Manual team stats fallback | Manual team stats | no | missing | 0 |  |  | no_real_manual_rows | Add real rows to data/raw/manual/manual_team_stats_2026.csv. |
| Manual player stats fallback | Manual player stats | no | missing | 0 |  |  | no_real_manual_rows | Add real rows to data/raw/manual/manual_player_stats_2026.csv. |
