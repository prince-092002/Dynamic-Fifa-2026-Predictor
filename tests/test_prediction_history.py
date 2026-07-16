"""Tests for the Prediction History snapshot audit trail."""

from __future__ import annotations

import pytest

from src.prediction_history import snapshot as sn


def make_files(completed=98, champ=None, matchups=None, gen="2026-07-11T00:02:43+00:00"):
    champ = champ or [("Spain", 0.40), ("Argentina", 0.35), ("France", 0.25)]
    matchups = matchups if matchups is not None else [{
        "stage": "Semifinal", "team_a": "France", "team_b": "Spain",
        "team_a_advance_probability": 0.446, "team_b_advance_probability": 0.554,
        "prob_team_a_win": 0.40, "prob_draw": 0.20, "prob_team_a_loss": 0.40,
        "favorite": "Spain", "model": "xgboost", "prediction_status": "predicted",
        "probability_source": "live_model",
    }]
    bracket_matches = [{"team_a": m["team_a"], "team_b": m["team_b"], "fixture_id": 5000 + i,
                        "date": "2026-07-14T19:00:00Z", "state": "scheduled"}
                       for i, m in enumerate(matchups)]
    return {
        "overview": {"current_phase": "semifinal", "completed_matches": completed, "provider": "football_data_org",
                     "forecast_mode": "true_live_forecast", "source_quality_score": 100, "simulations": 10000,
                     "seed": 42, "selected_model": "xgboost", "run_id": "test", "known_unresolved_matchups": len(matchups)},
        "champion": {"entries": [{"team": t, "champion_probability": p} for t, p in champ], "simulations": 10000,
                     "_meta": {"generated_at": gen}},
        "finalist": {"entries": [{"team": t, "reach_final_probability": min(1.0, p * 1.5)} for t, p in champ]},
        "finalist_pairs": {"entries": [{"finalist_team_1": "Argentina", "finalist_team_2": "Spain",
                                        "finalist_pair_key": "Argentina vs Spain", "probability": 0.6}]},
        "matchups": {"matchups": matchups},
        "bracket": {"rounds": [{"matches": bracket_matches}]},
        "run_manifest": {},
    }


@pytest.fixture
def store(tmp_path, monkeypatch):
    snaps = tmp_path / "snapshots"
    snaps.mkdir()
    monkeypatch.setattr(sn, "SNAPSHOTS_DIR", snaps)
    monkeypatch.setattr(sn, "MANIFEST_PATH", tmp_path / "manifest.json")
    monkeypatch.setattr(sn, "HISTORY_DIR", tmp_path)
    monkeypatch.setattr(sn, "ensure_dirs", lambda: snaps.mkdir(exist_ok=True))
    return sn


def test_build_preserves_probabilities_exactly():
    snap = sn.build_snapshot(make_files())
    champ = snap["main_forecast"]["champion_probabilities"]
    assert champ[0] == {"team": "Spain", "probability": 0.40}
    m = snap["matchday_predictions"][0]
    assert m["team_a"] == "France" and m["team_b"] == "Spain"
    assert m["team_b_win_probability"] == 0.554
    assert m["predicted_winner"] == "Spain"
    assert m["prediction_method"] == "XGBoost"
    assert m["prediction_outcome"] == "pending" and m["actual_winner"] is None


def test_display_date_uses_chicago_calendar_date():
    snap = sn.build_snapshot(make_files(gen="2026-07-16T00:15:25+00:00"))
    assert snap["display_date"] == "2026-07-15"
    assert snap["timezone"] == "America/Chicago"


def test_champion_probabilities_sum_close_to_one():
    snap = sn.build_snapshot(make_files(champ=[("Spain", 0.5), ("Argentina", 0.3), ("England", 0.2)]))
    total = sum(c["probability"] for c in snap["main_forecast"]["champion_probabilities"])
    assert abs(total - 1.0) < 1e-6


def test_state_hash_stable_and_sensitive():
    a = sn.build_snapshot(make_files())
    b = sn.build_snapshot(make_files())
    assert a["state_hash"] == b["state_hash"]  # unchanged state -> identical
    c = sn.build_snapshot(make_files(champ=[("Spain", 0.42), ("Argentina", 0.35), ("France", 0.23)]))
    assert c["state_hash"] != a["state_hash"]  # changed champion probs -> different


def test_multiple_matches_same_matchday():
    matchups = [
        {"stage": "Quarterfinal", "team_a": "Norway", "team_b": "England", "team_a_advance_probability": 0.36,
         "team_b_advance_probability": 0.64, "favorite": "England", "model": "xgboost", "probability_source": "live_model"},
        {"stage": "Quarterfinal", "team_a": "Argentina", "team_b": "Switzerland", "team_a_advance_probability": 0.77,
         "team_b_advance_probability": 0.23, "favorite": "Argentina", "model": "xgboost", "probability_source": "live_model"},
    ]
    snap = sn.build_snapshot(make_files(matchups=matchups))
    assert len(snap["matchday_predictions"]) == 2
    assert {m["predicted_winner"] for m in snap["matchday_predictions"]} == {"England", "Argentina"}


def test_enrich_correct_and_immutable():
    snap = sn.build_snapshot(make_files())
    results = {frozenset(["France", "Spain"]): {"winner": "Spain", "score": "0-2"}}
    enriched = sn.enrich_snapshot(snap, results)
    m = enriched["matchday_predictions"][0]
    assert m["prediction_outcome"] == "correct"
    assert m["actual_winner"] == "Spain" and m["actual_score"] == "0-2"
    assert m["team_b_win_probability"] == 0.554  # original probability preserved
    # immutability: the source snapshot is unchanged
    assert snap["matchday_predictions"][0]["prediction_outcome"] == "pending"
    assert snap["matchday_predictions"][0]["actual_winner"] is None


def test_enrich_incorrect():
    snap = sn.build_snapshot(make_files())
    results = {frozenset(["France", "Spain"]): {"winner": "France", "score": "1-0"}}
    m = sn.enrich_snapshot(snap, results)["matchday_predictions"][0]
    assert m["prediction_outcome"] == "incorrect"


def test_store_dedup_unchanged_rerun(store):
    snap = store.build_snapshot(make_files())
    first = store.store_snapshot(snap)
    second = store.store_snapshot(store.build_snapshot(make_files()))
    assert first["archived"] is True
    assert second["archived"] is False and second["reason"] == "duplicate_state"


def test_new_completed_match_creates_new_snapshot(store):
    store.store_snapshot(store.build_snapshot(make_files(completed=98)))
    r = store.store_snapshot(store.build_snapshot(
        make_files(completed=99, champ=[("Spain", 0.52), ("Argentina", 0.30), ("England", 0.18)],
                   gen="2026-07-12T05:08:43+00:00")))
    assert r["archived"] is True
    assert len(store.load_all_snapshots()) == 2


def test_current_and_previous_selection(store):
    store.store_snapshot(store.build_snapshot(make_files(completed=98, gen="2026-07-11T00:00:00+00:00")))
    store.store_snapshot(store.build_snapshot(make_files(completed=99, champ=[("Spain", 0.5), ("Argentina", 0.3), ("England", 0.2)], gen="2026-07-12T00:00:00+00:00")))
    store.store_snapshot(store.build_snapshot(make_files(completed=100, champ=[("Spain", 0.51), ("Argentina", 0.31), ("England", 0.18)], gen="2026-07-13T00:00:00+00:00")))
    snaps = store.load_all_snapshots()
    assert [s["completed_matches"] for s in snaps] == [98, 99, 100]  # ascending
    assert snaps[-1]["completed_matches"] == 100   # current
    assert snaps[-2]["completed_matches"] == 99     # previous meaningful


def test_missing_files_does_not_crash():
    snap = sn.build_snapshot({})
    assert snap["main_forecast"]["champion_probabilities"] == []
    assert snap["matchday_predictions"] == []
    # enrichment on an empty snapshot is safe
    assert sn.enrich_snapshot(snap, {})["matchday_predictions"] == []
