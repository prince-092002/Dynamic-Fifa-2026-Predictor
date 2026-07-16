from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public_data"


def _json(name: str) -> dict:
    return json.loads((PUBLIC / name).read_text(encoding="utf-8"))


def _final_state():
    overview = _json("latest_overview.json")
    if overview.get("current_phase") != "final":
        pytest.skip("final-stage integration assertions only apply during the Final")
    return overview


def test_public_champion_and_final_match_probabilities_are_identical():
    _final_state()
    champion = _json("champion_forecast.json")
    matchup = _json("matchup_predictions.json")
    final = [row for row in matchup["matchups"] if str(row.get("stage", "")).lower() == "final"]
    assert len(final) == 1
    final = final[0]
    champion_map = {row["team"]: row["champion_probability"] for row in champion["entries"]}
    matchup_map = {
        final["team_a"]: final["team_a_advance_probability"],
        final["team_b"]: final["team_b_advance_probability"],
    }
    assert champion_map == matchup_map
    assert sum(champion_map.values()) == pytest.approx(1.0, abs=1e-12)
    assert sum(matchup_map.values()) == pytest.approx(1.0, abs=1e-12)
    assert {row["probability_basis"] for row in champion["entries"]} == {"direct_final_matchup_probability"}


def test_public_finalists_match_the_official_bracket_and_are_not_eliminated():
    overview = _final_state()
    bracket = _json("knockout_bracket.json")
    teams = _json("teams.json")
    final_rows = [match for round_ in bracket["rounds"] for match in round_["matches"] if str(match.get("stage", "")).lower() == "final"]
    assert len(final_rows) == 1
    final = final_rows[0]
    assert final["state"] == "scheduled_known"
    finalists = {final["team_a"], final["team_b"]}
    alive = {team["team"] for team in teams["teams"] if team["status"] != "eliminated"}
    champions = {row["team"] for row in _json("champion_forecast.json")["entries"]}
    assert finalists == alive == champions
    completed = pd.read_csv(ROOT / "outputs" / "live_state" / "football_data_org_fixtures_normalized.csv")["is_completed"]
    assert int(completed.astype(str).str.lower().isin({"true", "1"}).sum()) == overview["completed_matches"]


def test_website_dashboard_and_latest_history_use_one_timestamped_export():
    overview = _final_state()
    names = ["latest_overview.json", "champion_forecast.json", "matchup_predictions.json", "knockout_bracket.json"]
    payloads = [_json(name) for name in names]
    assert len({payload["_meta"]["generated_at"] for payload in payloads}) == 1
    run_ids = {payload.get("run_id") or payload["_meta"].get("run_id") for payload in payloads}
    assert run_ids == {overview["run_id"]}

    manifest = json.loads((ROOT / "data" / "prediction_history" / "manifest.json").read_text(encoding="utf-8"))
    latest_entry = manifest["snapshots"][-1]
    latest = json.loads((ROOT / "data" / "prediction_history" / latest_entry["file"]).read_text(encoding="utf-8"))
    public_map = {row["team"]: row["champion_probability"] for row in payloads[1]["entries"]}
    history_map = {row["team"]: row["probability"] for row in latest["main_forecast"]["champion_probabilities"]}
    assert public_map == history_map
    assert latest["run_id"] == overview["run_id"]
