# API-Football Live Diagnostic

- API key found: yes
- League ID used: 1
- Season used: 2026
- Fixtures endpoint status: failed
- Fixtures row count: 0
- Completed matches: 0
- Live matches: 0
- Scheduled matches: 0
- Rounds endpoint status: failed
- Available rounds: none
- Standings endpoint status: failed
- Standings row count: 0
- Teams endpoint status: failed
- Teams row count: 0
- Detected current phase: pre_group_stage

## Problems Found

- Fixtures endpoint failed: {'plan': 'Free plans do not have access to this season, try from 2022 to 2024.'}
- Fixtures endpoint returned 0 normalized rows.
- Standings endpoint returned 0 normalized rows.
- No completed FIFA 2026 matches detected from API-Football.

## Exact Next Action

Run the quality gate. If mode is fallback_pre_tournament_forecast, only run forecast with --allow-fallback-forecast for testing.

No API secrets are printed or saved.