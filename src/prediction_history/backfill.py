"""Backfill prediction history from genuinely committed forecast outputs in Git.

For each commit that changed ``public_data/champion_forecast.json`` we read the exact
``public_data`` forecast that was committed at that point in time and archive it as a
snapshot tagged ``recovered_from_committed_output``. Nothing is recomputed with today's
model — these are the real forecasts as they were published, recovered verbatim from Git.
"""

from __future__ import annotations

import json
import subprocess

from src.config import PROJECT_ROOT
from src.prediction_history.config import RECORD_RECOVERED
from src.prediction_history.snapshot import build_snapshot, store_snapshot

_FILES = {
    "overview": "public_data/latest_overview.json",
    "champion": "public_data/champion_forecast.json",
    "finalist": "public_data/finalist_forecast.json",
    "finalist_pairs": "public_data/finalist_pairs.json",
    "matchups": "public_data/matchup_predictions.json",
    "bracket": "public_data/knockout_bracket.json",
    "run_manifest": "public_data/latest_run_manifest.json",
}


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True)
        return out.stdout if out.returncode == 0 else None
    except Exception:
        return None


def _show_json(commit: str, path: str):
    raw = _git("show", f"{commit}:{path}")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def _commits_touching_forecast() -> list[str]:
    out = _git("log", "--format=%H", "--", "public_data/champion_forecast.json")
    return [line.strip() for line in (out or "").splitlines() if line.strip()]


def _commit_meta(commit: str) -> dict:
    out = _git("show", "-s", "--format=%cI%n%s", commit) or ""
    lines = out.splitlines()
    return {"git_commit": commit[:9], "commit_date": lines[0] if lines else None,
            "commit_subject": lines[1] if len(lines) > 1 else None}


def backfill_from_git(commits: list[str] | None = None) -> dict:
    """Recover and archive genuine committed forecasts. Idempotent (dedup by state hash)."""
    commits = commits or _commits_touching_forecast()
    archived, skipped, empty = [], [], []
    # oldest first so the manifest builds chronologically
    for commit in reversed(commits):
        files = {key: _show_json(commit, path) for key, path in _FILES.items()}
        if not files.get("champion") or not files.get("overview"):
            empty.append(commit[:9])
            continue
        snapshot = build_snapshot(files, record_class=RECORD_RECOVERED, provenance=_commit_meta(commit))
        result = store_snapshot(snapshot, force=False)
        (archived if result.get("archived") else skipped).append(
            {"commit": commit[:9], "snapshot_id": result.get("snapshot_id"),
             "phase": snapshot.get("tournament_phase"), "completed": snapshot.get("completed_matches"),
             "reason": result.get("reason")})
    return {
        "commits_scanned": len(commits),
        "archived": len(archived),
        "skipped_duplicate": len(skipped),
        "no_forecast_in_commit": len(empty),
        "archived_detail": archived,
        "skipped_detail": skipped,
    }
