"""The completed-tournament snapshot is dated by publication, not by rerun wall-clock time.

A rerun that happens just after midnight UTC would otherwise date the final archive to the
following calendar day in America/Chicago, misrepresenting when the final state was
published. These tests pin that behaviour and confirm pre-final snapshots are unaffected.
"""

from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.prediction_history.config import MANIFEST_PATH, SNAPSHOTS_DIR
from src.prediction_history.snapshot import _display_date, _to_utc_iso, build_snapshot

CHICAGO = ZoneInfo("America/Chicago")


def _rendered_chicago(iso: str) -> str:
    value = datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone(CHICAGO)
    return value.strftime("%b %d, %Y, %I:%M %p %Z").replace(" 0", " ", 1)


# --- timestamp normalisation ---------------------------------------------- #

def test_local_offset_timestamp_normalises_to_utc_z():
    assert _to_utc_iso("2026-07-19T19:00:00-05:00") == "2026-07-20T00:00:00Z"


def test_utc_timestamp_passes_through_unchanged():
    assert _to_utc_iso("2026-07-20T00:00:00Z") == "2026-07-20T00:00:00Z"


def test_invalid_or_missing_timestamp_is_ignored():
    assert _to_utc_iso(None) is None
    assert _to_utc_iso("") is None
    assert _to_utc_iso("not-a-timestamp") is None


def test_publication_instant_displays_as_july_19_in_chicago():
    """2026-07-20T00:00:00Z is 7:00 PM CDT on July 19 — the user-facing date is the 19th."""
    assert _display_date("2026-07-20T00:00:00Z") == "2026-07-19"
    assert _rendered_chicago("2026-07-20T00:00:00Z") == "Jul 19, 2026, 7:00 PM CDT"


# --- snapshot construction ------------------------------------------------ #

def _files(*, complete: bool, export_generated_at: str = "2026-07-20T05:53:01+00:00") -> dict:
    overview = {
        "current_phase": "complete" if complete else "final",
        "completed_matches": 104 if complete else 103,
        "_meta": {"generated_at": export_generated_at},
    }
    if complete:
        overview["tournament_complete"] = True
        overview["final_result"] = {
            "champion": "Spain",
            "runner_up": "Argentina",
            "published_at": "2026-07-19T19:00:00-05:00",
        }
    return {
        "overview": overview,
        "champion": {"entries": [], "_meta": {"generated_at": export_generated_at}},
        "finalist": {},
        "finalist_pairs": {},
        "matchups": [],
        "bracket": {},
        "run_manifest": {},
    }


def test_completed_snapshot_uses_the_publication_timestamp():
    snapshot = build_snapshot(_files(complete=True))
    assert snapshot["generated_at"] == "2026-07-20T00:00:00Z"
    assert snapshot["display_date"] == "2026-07-19"
    assert _rendered_chicago(snapshot["generated_at"]) == "Jul 19, 2026, 7:00 PM CDT"


def test_pre_final_snapshot_still_uses_the_export_timestamp():
    """Backward compatibility: nothing changes before the tournament completes."""
    snapshot = build_snapshot(_files(complete=False, export_generated_at="2026-07-19T18:07:41+00:00"))
    assert snapshot["generated_at"] == "2026-07-19T18:07:41+00:00"
    assert snapshot["display_date"] == "2026-07-19"


def test_completed_snapshot_without_publication_timestamp_falls_back():
    files = _files(complete=True)
    files["overview"]["final_result"].pop("published_at")
    snapshot = build_snapshot(files)
    assert snapshot["generated_at"] == "2026-07-20T05:53:01+00:00"


# --- archived state ------------------------------------------------------- #

@pytest.mark.skipif(not MANIFEST_PATH.exists(), reason="prediction history manifest not present")
def test_archived_final_snapshot_is_dated_july_19():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    complete = [s for s in manifest["snapshots"] if s.get("tournament_phase") == "complete"]
    assert len(complete) == 1, "exactly one completed-tournament snapshot should be archived"
    entry = complete[0]
    assert entry["display_date"] == "2026-07-19"
    assert _rendered_chicago(entry["generated_at"]) == "Jul 19, 2026, 7:00 PM CDT"
    assert (SNAPSHOTS_DIR / f"{entry['snapshot_id']}.json").exists()


@pytest.mark.skipif(not MANIFEST_PATH.exists(), reason="prediction history manifest not present")
def test_pre_final_snapshot_probabilities_were_not_rewritten():
    """The pre-final forecast must survive the result unchanged (no 100% back-fill)."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    pre_final = [s for s in manifest["snapshots"]
                 if s.get("tournament_phase") == "final" and s.get("completed_matches") == 103]
    assert pre_final, "the pre-final snapshot should still be archived"
    payload = json.loads((SNAPSHOTS_DIR / f"{pre_final[-1]['snapshot_id']}.json").read_text(encoding="utf-8"))
    probabilities = {c["team"]: c["probability"] for c in payload["main_forecast"]["champion_probabilities"]}
    assert round(probabilities["Spain"], 4) == 0.5195
    assert round(probabilities["Argentina"], 4) == 0.4805
    assert payload["main_forecast"]["predicted_final_winner"] is None
