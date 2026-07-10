# Data Validation Failure Audit — Phase 5G Workstream A

- Audit date: 2026-07-09
- Baseline: `python main.py validate` reported **3 failing checks**, which propagated to `Existing data refresh validation status: failed` in every matchday update since Phase 2.

## Summary Table

| Check | Status (before) | Observed | Expected | Root cause | Severity | Impact on live forecast | Recommended fix | Fix implemented | Post-fix status |
|---|---|---|---|---|---|---|---|---|---|
| `matches_master / duplicate_same_date_same_teams` | fail | 868 duplicate same-date team-pair rows | 0 | Outdated validation assumption: the two Kaggle feeds (`kaggle_international_results`, `kaggle_world_cup_historical`) intentionally both contribute rows, so the same real match appears twice in the **raw** master (853 cross-feed groups + 15 same-day feed quirks; 110 groups with conflicting scores). Phase 3 architecture deliberately keeps the raw master untouched and deduplicates into `matches_master_feature_clean.csv`, which is the file feature engineering actually consumes (verified: 0 duplicates there). The check enforced a zero-duplicate rule at the wrong layer. | Low (handled downstream by design) | Indirect: the Phase 5F live feature history was reading the **raw** master, so live form/Elo replay double-counted ~850 historical matches. Fixed (see below). | Demote raw-master duplicates to `warn` with an explanatory message; add a **fail-level** check `feature_clean_no_duplicates` on the deduplicated file that features actually consume. | Yes — `src/validation/validate_data.py` | `warn` (raw, expected) + new `pass` (feature-clean, fail-capable) |
| `fixtures_2026 / non_null_team_a` | fail | 32 missing names | 0 | Expected placeholder condition incorrectly treated as failure: the 32 rows are exactly the knockout-slot fixtures (16 R32 + 8 R16 + 4 QF + 2 SF + 1 third-place + 1 final) in the pre-tournament template, all `status=scheduled`. Phase 3 explicitly preserves TBD fixtures; live bracket data resolves them. | Low | None — the live pipeline reads provider fixtures, not the template. | Split the check: missing names on group-stage or completed fixtures remain **fail**; scheduled knockout placeholders become a separate `warn` check with count. | Yes — `_check_fixture_team_names` in `src/validation/validate_data.py` | `pass` (0 hard-missing) + `warn` (32 placeholders, expected) |
| `fixtures_2026 / non_null_team_b` | fail | 32 missing names | 0 | Same as above. | Low | None | Same as above. | Yes | `pass` + `warn` (32 placeholders) |

## Verification Detail

**Duplicates (868):** sampled duplicate groups confirm the pattern — e.g. the same 1916 Argentina–Uruguay matches present once per feed with different tournament labels, and every FIFA World Cup match present in both the international-results feed and the world-cup-historical feed. `data/features/intermediate/matches_master_feature_clean.csv` (49,596 rows) has **0** same-date-team duplicates, confirming the Phase 3 dedup works. Duplicate details were already documented in `outputs/reports/features/duplicate_match_report.md` at feature-build time.

**Missing fixture names (32+32):** all 32 rows are `Round of 32` → `Final` template slots with `status=scheduled` and no completed result. No group-stage or completed fixture is missing a team name.

## Was validation weakened?

No. The failure conditions were **relocated, not removed**:

- A duplicate row in `matches_master_feature_clean.csv` (the file that actually feeds features/models) now **fails** — this check did not exist before.
- A missing team name on any group-stage or completed fixture still **fails**.
- Both expected conditions remain visible as `warn` rows with counts and explanations, so they are never silently ignored.

## Related defect fixed (live feature lineage)

The investigation exposed that `src/live_state/live_matchup_features.py::_build_combined_history` read the **raw** `matches_master.csv` (with the 868 duplicates) while training features were built from the deduplicated feature-clean file. The live history now prefers `matches_master_feature_clean.csv` (falling back to the raw master only if the clean file is missing), keeping live knockout features on the same data lineage as the training set. The Phase 5F NaN-goal placeholder drop and the (team, date±1) live-result dedup are preserved unchanged.

Effect on current predictions: live Elo/form features no longer double-count duplicated historical matches. Quarterfinal probabilities shift slightly as a result; this is a correctness fix, not a model change (schema, model artifact, and feature definitions untouched).

## Post-fix validation state

```text
python main.py validate  ->  22 pass, 3 warn, 0 fail
```

- `matches_master / duplicate_same_date_same_teams`: warn (868, expected, explained)
- `matches_master_feature_clean / feature_clean_no_duplicates`: pass (0) — new fail-capable gate
- `fixtures_2026 / non_null_team_a,b`: pass (0 hard-missing)
- `fixtures_2026 / knockout_placeholder_team_a,b`: warn (32, expected, explained)

Live forecast validation, feature validation, leakage checks, simulation validation, and bracket validation all still pass (verified in the Phase 5G baseline run before any changes, and re-verified after).
