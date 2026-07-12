"""Regression: football-data.org completion recovery for malformed status strings.

The provider once returned a finished knockout match (Mexico 2-3 England, R16) with a
timestamp in the `status` field instead of "FINISHED". Because completion keyed off
status == "FINISHED", a decided match was treated as an unplayed, predictable matchup.
These tests lock in the recovery: a decisive full-time result is treated as FINISHED,
while genuinely scheduled matches stay open.
"""

from __future__ import annotations

from src.live_state.providers.football_data_org_provider import FootballDataOrgProvider


def _match(status, home_g, away_g, winner=None, mid=1):
    return {
        "id": mid,
        "utcDate": "2026-07-06T01:00:00Z",
        "stage": "LAST_16",
        "homeTeam": {"name": "Mexico", "id": 10},
        "awayTeam": {"name": "England", "id": 20},
        "status": status,
        "score": {"winner": winner, "fullTime": {"home": home_g, "away": away_g}, "penalties": {"home": None, "away": None}},
    }


def _normalize(match):
    df = FootballDataOrgProvider().normalize_fixtures({"matches": [match]})
    return df.iloc[0]


def test_malformed_status_with_decisive_score_is_completed():
    row = _normalize(_match("2026-07-06 01:00:00Z", 2, 3, winner="AWAY_TEAM"))
    assert row["is_completed"] is True or row["is_completed"] == True  # noqa: E712
    assert row["is_scheduled"] == False  # noqa: E712
    assert row["winner"] == "England"
    assert row["status_short"] == "FINISHED"


def test_scheduled_match_without_score_stays_open():
    row = _normalize(_match("TIMED", None, None))
    assert row["is_completed"] == False  # noqa: E712
    assert row["is_scheduled"] == True  # noqa: E712
    assert row["winner"] is None


def test_finished_status_still_completed():
    row = _normalize(_match("FINISHED", 1, 0, winner="HOME_TEAM"))
    assert row["is_completed"] == True  # noqa: E712
    assert row["winner"] == "Mexico"


def test_live_match_not_marked_completed():
    # An in-play match has no full-time score; must not be recovered to FINISHED.
    m = _match("IN_PLAY", None, None)
    m["score"]["fullTime"] = {"home": None, "away": None}
    row = _normalize(m)
    assert row["is_completed"] == False  # noqa: E712
    assert row["is_live"] == True  # noqa: E712
