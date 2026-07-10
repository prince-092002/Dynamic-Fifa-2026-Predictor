# Elo Loading Status

- Status: kaggle_fifa_ranking_fallback
- Message: Web parse failed; loaded 211 FIFA ranking rows from Kaggle fallback. Error: No tables found
- Raw/manual input: data/raw/kaggle/world_cup_historical/fifa_ranking_*.csv
- Processed output: C:\Users\abelp\Desktop\Fifa Project\data\processed\team_ratings.csv

If web parsing still fails, add rows to `data/raw/manual/manual_team_ratings.csv` and rerun `python main.py load-real-data`.