"""Phase 5G tests: chronological integrity, leakage-safety, baseline reproducibility."""

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.modeling.data_loader import load_training_dataset  # noqa: E402
from src.modeling.feature_selection import get_safe_feature_columns  # noqa: E402
from src.modeling.model_config import EXCLUDE_COLUMNS, LEAKAGE_TERMS  # noqa: E402
from src.modeling.splits import chronological_train_val_test_split  # noqa: E402

PHASE5G = PROJECT_ROOT / "outputs" / "reports" / "modeling" / "phase5g"


class TestChronologicalIntegrity:
    def test_split_boundaries_are_monotonic_in_time(self):
        df = load_training_dataset()
        train, val, test = chronological_train_val_test_split(df)
        # No future leakage: every train match precedes (or ties) the validation
        # window start, which precedes the test window start.
        assert train["date"].max() <= val["date"].min()
        assert val["date"].max() <= test["date"].min()

    def test_split_is_deterministic(self):
        df = load_training_dataset()
        a = chronological_train_val_test_split(df)
        b = chronological_train_val_test_split(df)
        for x, y in zip(a, b):
            assert list(x["match_id"]) == list(y["match_id"])


class TestLeakageSafety:
    def test_no_target_or_outcome_columns_in_feature_set(self):
        df = load_training_dataset()
        feats = get_safe_feature_columns(df)
        for col in feats:
            assert col not in EXCLUDE_COLUMNS, f"excluded column leaked into features: {col}"

    def test_no_raw_goal_or_result_terms_in_features(self):
        # goal *difference/average* form features are allowed (pre-match rolling),
        # but raw post-match outcome terms must never appear as bare columns.
        df = load_training_dataset()
        feats = get_safe_feature_columns(df)
        forbidden_exact = {"team_a_goals", "team_b_goals", "winner", "team_a_win", "team_b_win", "draw", "match_result", "predicted_result"}
        assert not (set(feats) & forbidden_exact)

    def test_features_are_numeric_and_present(self):
        df = load_training_dataset()
        feats = get_safe_feature_columns(df)
        assert len(feats) >= 20
        for col in feats:
            assert pd.api.types.is_numeric_dtype(df[col]) or pd.api.types.is_bool_dtype(df[col])


@pytest.mark.skipif(not (PHASE5G / "baseline_model_metrics.json").exists(), reason="Phase 5G harness has not been run")
class TestBaselineReproducibility:
    def test_frozen_baseline_matches_published_production_numbers(self):
        baseline = json.loads((PHASE5G / "baseline_model_metrics.json").read_text(encoding="utf-8"))
        test = baseline["test"]
        # The frozen Phase 5G baseline must reproduce the published production XGBoost metrics.
        assert test["accuracy"] == pytest.approx(0.6075, abs=0.002)
        assert test["macro_f1"] == pytest.approx(0.4511, abs=0.002)
        assert test["log_loss"] == pytest.approx(0.8607, abs=0.005)

    def test_promotion_decision_is_self_consistent(self):
        decision = json.loads((PHASE5G / "promotion_decision.json").read_text(encoding="utf-8"))
        # If not promoted, production must be marked unchanged (baseline retained).
        assert decision["production_model_unchanged"] == (not decision["promote"])
        assert "rationale" in decision and decision["rationale"]

    def test_draw_class_underprediction_evidence_exists(self):
        diag = json.loads((PHASE5G / "diagnostic_metrics.json").read_text(encoding="utf-8"))
        xgb = diag["models"]["xgboost"]["test"]
        lr = diag["models"]["logistic_regression"]["test"]
        # The documented finding: XGBoost argmax-predicts far fewer draws than LR.
        assert xgb["predicted_distribution"]["draw"] < lr["predicted_distribution"]["draw"]
        assert xgb["recall"]["draw"] < 0.1  # near-zero draw recall
