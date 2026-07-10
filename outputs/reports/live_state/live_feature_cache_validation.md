# Live Feature Fast-Path Equivalence Validation

- Generated: 2026-07-10T06:19:37+00:00
- Status: pass
- Rows compared: 3 (original 3, fast 3)
- Features compared per row: 28
- Exact matches: 84
- Tolerance-only matches (<= 1e-09): 0
- Mismatches: 0
- Maximum absolute difference: 0.0
- Runtime, original Phase 3 row-loop path: 5.6s
- Runtime, fast vectorized path: 1.7s
- Speedup: 3.2x

The fast path vectorizes `calculate_team_match_history` and restricts the H2H/schedule
history inputs to rows those functions can actually read (same pair / same team).
No feature definitions, imputation behavior, or model schema were changed.
The saved live_knockout_match_features.csv comes from the fast path only when this check passes.