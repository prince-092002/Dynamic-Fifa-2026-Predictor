# Feature Validation Report

| Dataset | Check | Status | Message | Rows affected |
|---|---|---|---|---:|
| training | rows | pass | 49589 rows | 49589 |
| training | required_columns | pass | Missing: [] | 0 |
| training | target_leakage_columns | pass | Targets in feature list: [] | 0 |
| training | duplicate_match_id | pass | 0 duplicate match IDs | 0 |
| training | fully_null_feature_columns | pass | Fully null: [] | 0 |
| training | parseable_dates | pass | 0 invalid dates | 0 |
| training | match_result_values | pass | match_result values should be 0, 1, 2 | 0 |
| fixtures | rows | pass | 104 rows | 104 |
| fixtures | required_columns | pass | Missing: [] | 0 |
| fixtures | tbd_preserved | pass | 32 TBD fixtures preserved | 32 |
| fixtures | predictable_now | pass | 51 fixtures currently predictable | 51 |
| fixtures | feature_columns | pass | 26 configured feature columns present | 26 |