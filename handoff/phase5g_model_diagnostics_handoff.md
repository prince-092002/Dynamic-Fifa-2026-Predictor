# Phase 5G — Leakage-Safe Model Diagnostics, Feature Optimization & Challenger Evaluation Handoff

Saved: 2026-07-11  
Scope: diagnose the production match-outcome model, explain the low XGBoost macro-F1, run controlled leakage-safe feature/hyperparameter experiments, and promote a challenger only if it genuinely beats the baseline. No live-pipeline, simulator, provider, dashboard-architecture, or deployment changes beyond an additive diagnostics panel. **(Note: distinct from the earlier `phase5g_live_reliability_and_validation_handoff.md`, which used the same "5G" label for a different reliability workstream.)**

## Outcome in one line

The production **XGBoost remains the model** — no challenger legitimately beat it (best tuned challenger: test accuracy 0.6069 vs 0.6075, 95% bootstrap CI on the difference [−0.0023, +0.0012] includes zero). The low macro-F1 was fully explained (draw-class argmax artifact of a well-calibrated model) and is not a defect. All artifacts, a comprehensive report, and transparency panels on both methodology pages were produced. Production model artifacts were **not modified**.

## What was implemented

- `src/modeling/phase5g_diagnostics.py` — self-contained research harness (no new deps; XGBoost + sklearn + custom bounded search). Reproduces the production chronological 70/15/15 split and runs: full diagnostics (confusion, per-class P/R/F1/support, class distributions, confidence bands, balanced accuracy, ECE) for Logistic Regression and XGBoost; segmented performance; feature-family ablation; expanding-window chronological CV; controlled experiments (multi-window form, recency weighting, class weighting/draw investigation); a 30-config randomized hyperparameter search; a single frozen-test challenger evaluation with paired bootstrap CI; and an explicit promotion decision. Writes all artifacts under `outputs/reports/modeling/phase5g/`; any challenger model would go under `outputs/models/phase5g/` (kept separate from production).
- `tests/test_phase5g_diagnostics.py` — 8 tests: chronological split monotonicity + determinism, leakage-safety (no target/outcome columns in the feature set), baseline reproducibility (frozen metrics match the published 0.6075/0.4511/0.8607), promotion-decision self-consistency, and draw-underprediction evidence.
- Additive transparency: extended `src/public_export/build_public_exports.py::_build_model_insights` with a `diagnostics` block (production XGBoost per-class metrics, actual/predicted distribution, ECE, draw explanation) sourced from `diagnostic_metrics.json`; surfaced it on the website `/methodology` page (`website/app/methodology/page.tsx` + `lib/types.ts`) and the Streamlit `Model & Methodology` page. `public_data/model_insights.json` regenerated.

## Baseline (frozen, immutable reference)

| Model | Test acc | Test macro-F1 | Test log loss | Test Brier | Test ECE |
|---|---:|---:|---:|---:|---:|
| Logistic Regression (`class_weight="balanced"`) | 0.5752 | 0.5273 | 0.8872 | 0.5241 | 0.0463 |
| **XGBoost (production)** | **0.6075** | **0.4511** | **0.8607** | **0.5056** | **0.0053** |

The harness reproduced these exactly, validating faithful reproduction. `baseline_model_metrics.json`.

## Why XGBoost macro-F1 was low (calculated)

Draws are the minority class (22.7% train; 1,703/7,439 test). XGBoost (unweighted, optimizing log loss) **argmax-predicts "draw" only 46 times** (recall 0.012, F1 0.024) because a draw is rarely the single most likely 3-way outcome — so the unweighted macro-F1 collapses to 0.451. Logistic Regression's `class_weight="balanced"` forces ~1,658 draw predictions (recall 0.287, F1 0.290 → macro-F1 0.527) but pays with worse accuracy, log loss, Brier, and 9× worse calibration (ECE 0.046 vs 0.0053). Because the model feeds a **probability-sampling Monte Carlo simulator**, calibrated draw *probabilities* (not hard draw predictions) are what matter — so XGBoost's selection by log loss is correct and the low macro-F1 is a metric artifact, not a defect.

## Experiments run (validation set; test untouched) — including failures

| Experiment | Result | Verdict |
|---|---|---|
| Multi-window form (last_3/last_10 + draw_rate diffs) | val log loss 0.897 ≈ baseline | no value — last_5 already captures signal |
| Recency weighting (half-life 8/4/2y) | ↑macro-F1 & draw recall, but ↑log loss, ↓/≈ accuracy | reject — no era decay exists (2010s≈2020s) |
| Class weighting — inverse-freq | macro-F1 0.43→0.51, draw recall 0.01→0.39, **accuracy −0.047, log loss +0.037** | reject — destroys calibration |
| Class weighting — draw ×1.8 | similar tradeoff | reject |
| Hyperparameter search (30 configs) | best val log loss 0.89785 ≈ baseline 0.89782 | baseline already near-optimal |
| Feature-family ablation | full 25-feature set best on val acc & log loss; Elo alone already 0.576 | keep all features |

**Chronological CV (4 expanding folds):** baseline mean acc 0.5843 (std 0.0037, stable); tuned 0.5838 — no improvement.

## Challenger on frozen test + promotion decision

Best tuned XGBoost on the single frozen test evaluation: accuracy 0.6069 (−0.0005), macro-F1 0.4510, log loss 0.8613 (slightly worse). Paired bootstrap 95% CI on the accuracy difference: **[−0.0023, +0.0012]** — includes zero. Promotion gates: meaningful+significant accuracy gain → **fail**; probability quality preserved → pass; CV stable → pass. **Decision: REJECT — production XGBoost retained** (`promotion_decision.json`). No downstream regeneration performed (model unchanged → live predictions, Monte Carlo outputs, champion/finalist probabilities, and completed-match locking all untouched).

## Verification

```text
python -m pytest tests -q                 -> 24 passed (16 Phase 6B + 8 Phase 5G)
python -m compileall src main.py scripts dashboard -> pass
Production model + registry (outputs/models/) -> UNCHANGED (git-verified)
validate-public-exports / validate-dashboard / validate-live-forecast -> pass / pass / pass
website npm run build                     -> 55 static pages (incl. new diagnostics section)
No new dependencies added.
```

## Artifacts

`outputs/reports/modeling/phase5g/`: PHASE_5G_REPORT.md, baseline_model_metrics.json, diagnostic_metrics.json, classification_reports.json, confusion_matrices.json, segmented_performance.csv, feature_ablation_results.csv, feature_experiment_results.csv, hyperparameter_search_results.csv, chronological_cv_results.csv, challenger_model_comparison.csv, promotion_decision.json, experiment_registry.json, phase_5g_audit_manifest.json.

## Known limitations & recommended next step

- Draw predictability is **data-limited** (draws cluster in close, low-Elo-gap matches that are inherently near-random: abs Elo diff <50 → 44.7% accuracy / 28% draw rate; 300+ → 87% / 10%). No leakage-safe feature moved draw probability quality.
- **Not implemented (require raw-history feature-pipeline extension):** Elo-momentum (Elo slope over last N) and opponent-strength-adjusted form. These are the most promising untried directions and the natural first step of future modeling work.
- LightGBM/CatBoost/Optuna intentionally not added (deployment simplicity); a custom bounded search was used.
- **Recommended next phase: Phase 5H — Player, Squad & Tactical Intelligence** (as planned). Do not pursue class-weighting to raise macro-F1 — this phase proved it degrades simulator-relevant probability quality.
