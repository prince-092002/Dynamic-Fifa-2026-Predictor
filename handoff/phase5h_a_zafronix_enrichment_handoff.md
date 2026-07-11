# Phase 5H-A — Zafronix Enrichment Handoff

**Saved:** 2026-07-11 · **Decision: REJECT challenger — production XGBoost unchanged (byte-identical).**
**NOT pushed / NOT deployed — local restore-point commit only, pending independent review.**

## A. Phase
Zafronix World Cup, Squad & Historical Intelligence Enrichment (secondary enrichment provider; football-data.org remains primary live truth).

## B. Executive summary
Added the real **Zafronix World Cup API** as an enrichment-only provider, fetched all 23 tournaments (metadata + squads) in ~25 sanitized requests, resolved 91/91 team names to canonical training names, and engineered **17 leakage-safe** World Cup pedigree / squad-age / player-experience difference features. Ran the frozen-baseline reproduction (exact) and experiments E0–E9. **No challenger beat the baseline** on the frozen global test (accuracy +0.0000, bootstrap 95% CI [−0.0013, +0.0013], log loss/Brier marginally worse). Production model retained, byte-identical. Full test suite (35) and all production validations pass. Enrichment pipeline retained for descriptive/analytical use.

## C. Files created
- `src/live_state/providers/zafronix_provider.py` — secure provider client.
- `src/enrichment/` — `__init__`, `zafronix_config`, `zafronix_fetch`, `zafronix_normalize`, `zafronix_entities`, `zafronix_coverage`, `zafronix_features`, `zafronix_challenger`.
- `tests/test_zafronix_enrichment.py` — 11 tests.
- `PHASE_5H_A_REPORT.md`, this handoff.
- Data: `data/processed/zafronix/{tournaments,team_appearances,squad_players}.csv`, `data/features/zafronix/zafronix_feature_coverage.csv`.
- Artifacts: `outputs/reports/enrichment/zafronix/*` (diagnostic, schema inventory, coverage×4, aliases, entity resolution, unresolved, feature registry, feature coverage, experiment results, chronological CV, challenger comparison, WC-subset metrics, promotion decision, feature importance, audit manifest, production integrity, France-vs-Spain audit).

## D. Files modified
- `src/config.py` (+`ZAFRONIX_API_KEY`, `ZAFRONIX_BASE_URL`), `.env.example` (placeholder), `.gitignore` (raw snapshots + joblib + bulky feature-values ignored), `main.py` (7 CLI commands).
- **No** analytics/model/simulation/live-pipeline/website/dashboard code changed.

## E. API endpoints used
`GET /health`, `/me/usage`, `/tournaments`, `/tournaments/{year}`. Base `https://api.zafronix.com/fifa/worldcup/v1`.

## F. Authentication
`X-API-Key` header; key from `ZAFRONIX_API_KEY` (free-tier read key). Never logged/snapshotted/reported; `_sanitize` strips key fields incl. partial `keyPrefix`. Secret scan of tracked artifacts: clean.

## G. Data fetched
23 tournaments (1930–2026), 537 team-appearances, 12,220 player rows, in ~25 requests (ETag-cached; 244 quota remaining).

## H. Coverage
WC-finals matches = 1,054 (2.1% of 49,589); both-teams-WC-nations = 20,681 (41.7%). Squad: position ~100%, age ~95–100%; caps/nationalGoals/physicals < 0.5% (every era).

## I. Entity mapping
91/91 resolved (90 exact + 1 alias `East Germany→German DR`); 0 unresolved; historically distinct teams kept separate (no silent merges).

## J. Leakage safeguards
Pedigree = prior completed WCs only (in-progress tournament excluded); squad = tournament-start age/position; player-exp = prior tournaments only. Excluded: in-tournament goals/cards, current finalPosition, observed weather. Tested by `test_pedigree_excludes_current_and_future_tournaments`.

## K. Features created (17)
Pedigree diffs (9), squad age/positional diffs (4), player prior-WC diffs (2), availability indicators (2). Registry: `zafronix_feature_registry.json`.

## L. Features rejected
Squad caps/national-goals experience (coverage < 0.5%), physical attributes (< 0.5%), weather (retrospective). Documented in registry.

## M. Experimental configs
E0 baseline; E1 pedigree; E2 squad; E3 player-exp; E4 availability; E5 pedigree+avail; E6 squad+player; E7 all; E8 WC-finals-specific model; E9 routed hybrid. Selected by validation log loss: **E3**.

## N–P. Metrics
**Baseline test:** acc 0.6075 / macro-F1 0.4511 / log loss 0.8607 / Brier 0.5056 / ECE 0.0053.
**Challenger (E3) test:** acc 0.6075 / macro-F1 0.4511 / log loss 0.8610 / Brier 0.5058 / ECE 0.0053.
**WC-finals subset (154):** base acc 0.5974 → chal 0.5909 (worse). E8 WC-only model improves vs a WC-only baseline (0.519→0.558) but is far below production on those matches.

## Q. Significance
Paired bootstrap 95% CI on Δaccuracy = [−0.0013, +0.0013] → not significant.

## R. Promotion decision
**REJECT.** Gates failed: meaningful+significant accuracy gain (Δ=0.0000, CI spans 0); probability quality preserved (log loss/Brier slightly worse). No forced promotion.

## S. If promoted
N/A.

## T. Because rejected
Production XGBoost is **unchanged and byte-identical** (`production_model_integrity.json`, git clean). Reason: WC-finals are 2.1% of data and pedigree overlaps Elo — the model uses the features (`z_pedigree_available` #8/42 by gain) but they add no new held-out signal. This is an expected, acceptable outcome.

## U. Test results
`pytest tests -q` → **35 passed** (24 prior + 11 new). New tests cover secret sanitization, no-key-on-disk, entity/historical resolution, prior-WC-only leakage, WC-finals-only squad gating, determinism, numeric/no-NaN, production separation.

## V. Audit results
validate-public-exports pass (31), validate-dashboard pass (10), validate-live-forecast pass. Live pipeline, simulator, forecasts untouched; completed matches still locked (§40: Zafronix failure cannot break live — provider fails to last-known-good).

## W. Known limitations
Squad features WC-finals-only; caps-based features impossible; successor states not merged; knockout goals parsed from result strings (shootouts excluded from tallies); 2026 squads preliminary and excluded from pedigree.

## X. Recommended next phase
Surface Zafronix pedigree/squad-depth as **descriptive** team intelligence on team pages (honest, leakage-safe, adds narrative) without claiming it powers predictions. Optionally revisit if a future data source provides populated caps/appearances at scale.

## Reproduce
```
python main.py diagnose-zafronix
python main.py fetch-zafronix        # ~25 requests, ETag-cached
python main.py normalize-zafronix
python main.py zafronix-entities
python main.py zafronix-coverage
python main.py build-zafronix-features
python main.py run-zafronix-challenger   # ~230s
```

## Status
**Nothing pushed. Nothing deployed. Portfolio Refresh not triggered.** One local restore-point commit on `main`, awaiting review.
