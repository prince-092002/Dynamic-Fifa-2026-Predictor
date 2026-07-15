# football-data.org Provider Report

- Provider: football_data_org
- Token present: yes
- Base URL: https://api.football-data.org/v4
- Competition code used: WC
- Competition ID used: 2000
- Competition metadata status: WC=200, 2000=200
- Matches endpoint HTTP status: 200
- Matches row count: 104
- resultSet count: 104
- Finished matches count: 101
- Scheduled matches count: 3
- Live/in-play matches count: 0
- Teams endpoint HTTP status: 200
- Teams row count: 48
- Standings endpoint HTTP status: 200
- Standings row count: 144
- Normalized data source: latest provider response
- Stages detected: Final, Group Stage, Quarterfinal, Round of 16, Round of 32, Semifinal, Third Place Playoff
- Groups detected: GROUP_A, GROUP_B, GROUP_C, GROUP_D, GROUP_E, GROUP_F, GROUP_G, GROUP_H, GROUP_I, GROUP_J, GROUP_K, GROUP_L
- Current phase detected: semifinal
- Can support live forecast: yes
- Provider status: available_true_live

## Limitations

- One or more optional diagnostic endpoints were rate limited after core data loaded.

## Exact Next Action

Run select-live-provider and live-quality-gate to decide whether forecasts are allowed.

No API token is printed or saved.