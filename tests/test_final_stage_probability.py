from __future__ import annotations

import numpy as np
import pandas as pd

from src.live_state.final_stage_probability import (
    FINAL_PROBABILITY_BASIS,
    canonical_final_champion_probabilities,
)
from src.live_state.finalist_aggregation import aggregate_live_finalist_results
from src.live_state.finalist_simulator import _simulate_or_lock_knockout_match


def _prediction(team_a="Alpha", team_b="Beta", probability=0.5194714075169387):
    return pd.DataFrame(
        [
            {
                "match_id": "final-1",
                "stage": "Final",
                "team_a": team_a,
                "team_b": team_b,
                "prob_team_a_advance": probability,
                "prob_team_b_advance": 1 - probability,
                "prediction_status": "predicted",
                "model_name": "xgboost",
                "probability_source": "live_model_exact",
                "generated_at": "2026-07-15T21:57:27+00:00",
            }
        ]
    )


def _bracket(stage="Final", completed=False):
    return pd.DataFrame(
        [
            {"fixture_id": "final-1", "stage": stage, "team_a": "Alpha", "team_b": "Beta", "is_completed": completed},
            {"fixture_id": "third-1", "stage": "Third Place Playoff", "team_a": "Gamma", "team_b": "Delta", "is_completed": False},
        ]
    )


def test_known_unresolved_final_uses_direct_probability_and_ignores_third_place():
    result = canonical_final_champion_probabilities(_bracket(), _prediction("Beta", "Alpha", 0.48052859248306135))
    probabilities = dict(zip(result["team"], result["champion_probability"]))
    assert probabilities == {"Alpha": 0.5194714075169387, "Beta": 0.48052859248306135}
    assert set(result["probability_basis"]) == {FINAL_PROBABILITY_BASIS}


def test_completed_final_and_nonfinal_round_do_not_override_simulation():
    assert canonical_final_champion_probabilities(_bracket(completed=True), _prediction()).empty
    assert canonical_final_champion_probabilities(_bracket(stage="Semifinal"), _prediction()).empty


def test_final_aggregation_keeps_monte_carlo_as_diagnostic(tmp_path, monkeypatch):
    simulations = pd.DataFrame(
        {
            "finalist_1": ["Alpha"] * 10,
            "finalist_2": ["Beta"] * 10,
            "finalist_pair_key": ["Alpha vs Beta"] * 10,
            "champion": ["Alpha"] * 7 + ["Beta"] * 3,
            "fallback_mapping_used": [False] * 10,
        }
    )
    monkeypatch.setattr("src.live_state.finalist_aggregation.LIVE_STATE_DIR", tmp_path)
    result = aggregate_live_finalist_results(simulations, _bracket(), _prediction(probability=0.52))
    champion = result["champion"].set_index("team")
    assert champion.loc["Alpha", "champion_probability"] == 0.52
    assert champion.loc["Alpha", "monte_carlo_champion_probability"] == 0.7
    assert champion.loc["Alpha", "champion_count"] == 7
    assert result["summary"]["champion_probability_basis"] == FINAL_PROBABILITY_BASIS


def test_fixed_seed_sampling_converges_to_direct_final_probability():
    probability = 0.5194714075169387
    estimate_10k = float((np.random.default_rng(42).random(10_000) < probability).mean())
    repeated_10k = float((np.random.default_rng(42).random(10_000) < probability).mean())
    estimate_1m = float((np.random.default_rng(42).random(1_000_000) < probability).mean())
    assert estimate_10k == 0.5223
    assert repeated_10k == estimate_10k
    assert abs(estimate_1m - probability) < abs(estimate_10k - probability)
    assert abs(estimate_1m - probability) < 0.001


def test_completed_match_is_locked_without_random_sampling():
    class RandomMustNotRun:
        def random(self):
            raise AssertionError("completed match was re-simulated")

    result = _simulate_or_lock_knockout_match(
        {"team_a": "Alpha", "team_b": "Beta", "winner": "Beta", "is_completed": True},
        RandomMustNotRun(),
        {},
        {},
    )
    assert result == ("Beta", "Alpha", "completed_result", "completed_result")
