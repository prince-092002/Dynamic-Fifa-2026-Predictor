# Phase 5H-A — Zafronix World Cup, Squad & Historical Intelligence Enrichment

**Status:** Complete. **Promotion decision: REJECT — production XGBoost retained, byte-identical.**
**Not pushed / not deployed — local restore-point commit only, pending review.**

---

## 1. Objective

Add the **Zafronix World Cup API** as a *secondary* historical/squad enrichment provider (never a live-truth source), engineer carefully leakage-safe World Cup history and squad features, and promote a new production model **only if it honestly beats the frozen baseline**. football-data.org remains the sole authoritative live-tournament-state provider; nothing here overwrites live truth.

## 2. Existing production baseline (reproduced exactly)

The Phase 5G frozen baseline was reproduced byte-for-byte before any enrichment:

| Metric | Frozen 5G baseline | Reproduced here |
|---|---|---|
| Accuracy | 0.6075 | **0.6075** |
| Macro F1 | 0.4511 | **0.4511** |
| Log loss | 0.8607 | **0.8607** |
| Brier | 0.5056 | **0.5056** |
| ECE | ~0.0053 | **0.0053** |

Baseline reproducibility is a hard precondition for a fair comparison; it passed.

## 3. Why new information was needed

Phase 5G established that further tuning of the *existing* 25 features cannot beat the baseline (draw is a minority class; class-weighting trades away calibration). Phase 5H-A therefore tests **new information** — World Cup pedigree and squad experience — rather than re-optimizing existing signal.

## 4. Provider design

`src/live_state/providers/zafronix_provider.py` — `ZafronixProvider` (role: `historical_and_squad_enrichment`):
- Auth via `X-API-Key` (key from `ZAFRONIX_API_KEY`, **never logged, snapshotted, or reported**; `_sanitize` strips `x-api-key`, `token`, `keyprefix`, etc.).
- Bounded retries, `Retry-After` support, conditional requests via **ETag** cache (`304 → no quota cost`), sanitized snapshots, **last-known-good** fallback that never passes stale data as fresh.
- **Fetch → validate → snapshot → normalize → features → model.** No API calls inside model/simulation/render loops.

## 5. API endpoints used

`GET /health`, `GET /me/usage`, `GET /tournaments`, `GET /tournaments/{year}`. A single `GET /tournaments/{year}` returns tournament metadata + every team (finalPosition, groupStage, knockoutPath) **and the embedded 26-player squad**, so the entire 23-tournament corpus was fetched in ~25 requests (free tier, 250/day). No per-match or per-player fan-out. Schema recorded in `zafronix_schema_inventory.json`.

## 6. Authentication & secret safety

Key in `.env` only; placeholder added to `.env.example`; `data/raw/zafronix/` gitignored. Secret scan of all tracked artifacts is clean (no `zwc_*` key material; the partial `keyPrefix` echoed by `/me/usage` is stripped by `_sanitize`).

## 7. Data coverage (`zafronix_coverage_report.json`)

- 23 tournaments (1930–2026), 537 team-appearances, **12,220 player rows**.
- **World Cup *finals* matches in the training corpus: 1,054 (2.1%)** — Zafronix does not cover the ~8,771 WC *qualifiers* that dominate the `is_world_cup_match` flag.
- Matches where **both** teams are WC nations (pedigree-relevant): **20,681 (41.7%)**.
- Frozen-test enrichment: 154 WC-finals matches; 2,311 both-WC-nation matches (of 7,439).
- **Squad-field coverage:** `position` ~100% and `ageAtTournament` ~95–100% in every era; **`caps`, `nationalGoals`, `heightCm`, `weightKg` are populated for < 0.5% of players in every era** (schema-ready but unpopulated).

## 8. Entity resolution (`zafronix_entity_resolution_report.csv`)

**91/91 (100%)** Zafronix names resolved. 90 match training names exactly; the one alias is `East Germany → German DR`. The training corpus already keeps historically distinct teams under separate names (West Germany, East Germany, Soviet Union, Yugoslavia, FR Yugoslavia, Serbia and Montenegro, Czechoslovakia, Zaire), so exact matching is historically correct — **no silent merges** (explicit alias map only, no fuzzy matching). West Germany pedigree is *not* inherited by modern Germany (documented limitation). Unresolved entities: **0**.

## 9. Leakage-safety rules

For a match with kickoff `D`:
- **Pedigree** uses only World Cups whose `end_date` is **strictly before D** — a team's in-progress tournament is excluded. (Test: an Argentina match *during* the 2022 WC sees pre-2022 pedigree only; a 2023 match sees the 2022 title.)
- **Squad age/position** use tournament-start values (documented pre-kickoff).
- **Player prior-WC experience** counts only prior tournaments (`year < current`).
- **Excluded as unsafe:** in-tournament goals/cards/assists, current-tournament `finalPosition`, and **observed weather** (no pre-kickoff forecast provenance — descriptive only, §16).

## 10–14. Feature registry & families (`zafronix_feature_registry.json`)

17 leakage-safe difference features across three **accepted** families:

- **Pedigree (9):** appearances / titles / finals / semifinals / knockout-win-rate / goal-difference / best-finish / years-since-last-WC / experience-score diffs. Experience score is a documented composite (`1·appearances + 3·titles + 1.5·finals + 0.75·semis + 0.25·quarters + 0.5·ko_wins`). Applies to any match; 25.8% have both teams with prior WC history.
- **Squad age & positional depth (4):** avg-age / age-std / defender-share / forward-share diffs. WC-finals matches only.
- **Player prior-WC experience (2):** share-with-prior-WC / total-prior-WC-appearances diffs. WC-finals only.
- Plus 2 availability indicators (`z_pedigree_available`, `z_squad_features_available`).

**Rejected families (documented, not fabricated):** squad **caps / national-goals experience** (source coverage < 0.5%), **physical attributes** (< 0.5%), **weather** (retrospective).

## 15. Missingness strategy

Pedigree diffs are true `0` when a team has no prior WC (a fact, not a guess), disambiguated by `z_pedigree_available`. Squad diffs are neutral `0` outside WC finals, disambiguated by `z_squad_features_available`. No test-set statistics used for imputation.

## 16–17. Experiments & chronological CV

E0–E9 on the preserved chronological split (train→val select, frozen test evaluated once). Validation results (`zafronix_feature_experiment_results.csv`):

| Experiment | +Zafronix feats | val acc | val log loss | val macro F1 |
|---|---|---|---|---|
| E0 baseline | 0 | 0.5824 | 0.89782 | 0.4301 |
| E1 + pedigree | 9 | 0.5843 | 0.89771 | 0.4334 |
| E2 + squad | 4 | 0.5840 | 0.89800 | 0.4299 |
| **E3 + player-exp** | 2 | 0.5831 | **0.89754** | 0.4292 |
| E4 + availability | 2 | 0.5840 | 0.89755 | 0.4314 |
| E5 + pedigree+avail | 11 | 0.5842 | 0.89783 | 0.4348 |
| E6 + squad+player | 8 | 0.5839 | 0.89802 | 0.4301 |
| E7 + all Zafronix | 17 | 0.5847 | 0.89804 | 0.4349 |

Enriched configs show only whisper-thin validation gains (≤ +0.002 acc). The challenger was selected by **validation log loss** (probability-first): **E3**.

## 18. Overall frozen-test result (`zafronix_challenger_model_comparison.csv`)

| Metric | Baseline (25f) | Challenger E3 (27f) | Δ |
|---|---|---|---|
| Accuracy | 0.6075 | 0.6075 | **+0.0000** |
| Macro F1 | 0.4511 | 0.4511 | +0.0000 |
| Log loss | 0.8607 | 0.8610 | **+0.0003 (worse)** |
| Brier | 0.5056 | 0.5058 | +0.0002 (worse) |
| ECE | 0.0053 | 0.0053 | −0.0000 |

## 19. World Cup subset (`zafronix_world_cup_subset_metrics.csv`)

| Subset | Support | Base acc | Chal acc | Δ acc | Δ log loss |
|---|---|---|---|---|---|
| All test | 7,439 | 0.6075 | 0.6075 | 0.0000 | +0.0003 |
| WC finals | 154 | 0.5974 | 0.5909 | **−0.0065** | +0.0021 |
| Both-WC-pedigree | 2,068 | 0.5406 | 0.5392 | −0.0015 | +0.0002 |

The global-enriched challenger does not help even on WC-finals matches. **However**, a **WC-finals-only** model (E8, trained on 772 WC matches) *does* improve with Zafronix features (acc 0.519→0.558, log loss 1.031→0.961, macro F1 0.453→0.495 on 154 test matches) — but that WC-only model is still far weaker than the full production model (0.607) on the same matches, because it forgoes 35k training rows. So the features carry genuine but redundant signal. E9 (routed hybrid) ≈ baseline (0.6073).

## 20. Statistical significance

Paired bootstrap on the test accuracy difference: **95% CI = [−0.0013, +0.0013]**, includes zero → no significant difference.

## 21. Probability quality

Log loss and Brier are marginally **worse**; ECE unchanged. Since the model feeds Monte Carlo simulation, degraded probability quality alone blocks promotion.

## 22. Promotion decision (`zafronix_promotion_decision.json`)

**REJECT — production XGBoost retained unchanged.** Gates: meaningful+significant accuracy gain **fail** (0.0000, CI spans 0); probability quality preserved **fail** (log loss/Brier slightly worse); CV stable pass. Per Phase 5H-A rules, no promotion is forced. This is an **expected, acceptable** outcome: WC-finals matches are only 2.1% of training, and pedigree signal overlaps heavily with Elo (which already encodes historical strength). Feature importance confirms the model *uses* the pedigree features — `z_pedigree_available` ranks #8 of 42 by gain, above several production features — they simply add no *new* held-out signal.

## 23–24. Live-inference & Monte Carlo implications

None. No downstream regeneration (correct: nothing is regenerated for appearance when no model changes). Completed matches remain locked; the live pipeline, simulator, and forecasts are untouched. **France vs Spain audit** (`france_vs_spain_audit.json`, §49): production forecast is operative and unchanged — P(France)=0.333, P(draw)=0.226, P(Spain)=0.441 (Spain's Elo edge). For transparency, the enriched model would nudge France to 0.349 on its pedigree edge (+1 title, +19.5 experience score), but the challenger is not promoted, so this does not alter the forecast.

## 25. Production model integrity (§50)

`selected_model.joblib` and `model_registry.json` are **byte-identical** (git status clean; sha256 recorded in `production_model_integrity.json`).

## 26. Known limitations

- Squad features cover only WC-finals matches (~2% of data); caps-based experience impossible (source ~0% coverage).
- West Germany / Germany (and other successor states) kept separate — pedigree not inherited across the split.
- Knockout goals parsed from result strings (leading `X-Y`); shootouts ignored for goal tallies.
- 2026 squads are preliminary (`_squadIsPreliminary`) and excluded from historical pedigree (ongoing tournament).

## 27. Recommended next phase

Retain the Zafronix pipeline for **descriptive** team-intelligence (World Cup pedigree, squad age/positional depth on team pages) — it is honest, leakage-safe, and adds narrative value even though it does not improve the predictive model. Do **not** claim Zafronix powers production predictions.

---

### Success criteria — all met
Repository inspected · docs verified · provider added · key secure · football-data.org still primary · no live regressions · coverage + entity + unresolved reported · registry created · leakage-safe features built · unsafe fields excluded · weather not used retrospectively · baseline reproduced · experiments run · chronological validation preserved · overall + WC-subset metrics with support · probability quality evaluated · significance assessed · **explicit REJECT, no forced promotion** · production model preserved byte-identical · tests pass (35) · website/dashboard/exports/live-forecast validations pass · report + handoff written · **no GitHub push**.
