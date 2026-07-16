"""Build, deduplicate, store and enrich prediction-history snapshots.

A snapshot is assembled purely from already-published forecast outputs (the
``public_data/*.json`` contract) — nothing here recomputes a prediction. Snapshots are
immutable once written; actual results are joined at read time (``enrich_snapshot``) so
the originally-predicted probabilities are never altered.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from src.config import PROJECT_ROOT
from src.prediction_history.config import (
    HISTORY_DIR,
    MANIFEST_PATH,
    PUBLIC_DATA_DIR,
    RECORD_GENUINE,
    SCHEMA_VERSION,
    SNAPSHOTS_DIR,
    ensure_dirs,
)
from src.utils.dates import now_utc_iso


# --------------------------------------------------------------------------- #
# low-level helpers
# --------------------------------------------------------------------------- #

def _entries(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for value in payload.values():
            if isinstance(value, list):
                return value
    return []


def _git_commit() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT_ROOT,
                             capture_output=True, text=True)
        return out.stdout.strip() or None
    except Exception:
        return None


def _method_label(matchup: dict) -> str:
    source = str(matchup.get("probability_source", "")).lower()
    if "elo" in source:
        return "Elo fallback"
    if "neutral" in source:
        return "Neutral fallback"
    if "model" in source or matchup.get("model") == "xgboost":
        return "XGBoost"
    return matchup.get("source_label") or source or "model"


def _compact_ts(iso: str) -> str:
    return (iso or "").replace(":", "").replace("+0000", "Z").replace("+00:00", "Z").replace("-", "")[:16] or "unknown"


def _display_date(iso: str) -> str:
    """Convert an archival UTC timestamp to the product's Chicago calendar date."""
    try:
        value = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(ZoneInfo("America/Chicago")).date().isoformat()
    except (TypeError, ValueError):
        return (str(iso) if iso else "")[:10]


# --------------------------------------------------------------------------- #
# snapshot construction (from a set of parsed public_data payloads)
# --------------------------------------------------------------------------- #

def build_snapshot(files: dict[str, Any], record_class: str = RECORD_GENUINE,
                   provenance: dict | None = None) -> dict:
    """Assemble a snapshot dict from parsed public_data payloads.

    ``files`` keys: overview, champion, finalist, finalist_pairs, matchups, bracket,
    run_manifest — each the parsed JSON (or {} / [] if unavailable).
    """
    overview = files.get("overview") or {}
    champion = files.get("champion") or {}
    finalist = files.get("finalist") or {}
    pairs = files.get("finalist_pairs") or {}
    matchups = _entries(files.get("matchups"))
    bracket = files.get("bracket") or {}
    run_manifest = files.get("run_manifest") or {}

    champ_meta = champion.get("_meta") if isinstance(champion, dict) else {}
    generated_at = (
        (champ_meta or {}).get("generated_at")
        or (overview.get("_meta") or {}).get("generated_at")
        or run_manifest.get("generated_at")
        or run_manifest.get("timestamp")
        or now_utc_iso()
    )
    phase = overview.get("current_phase") or (champ_meta or {}).get("current_phase") or "unknown"
    completed = overview.get("completed_matches")

    # ---- main tournament forecast ----
    champ_rows = sorted(
        [
            {
                "team": e.get("team"),
                "probability": e.get("champion_probability"),
                **({"probability_basis": e.get("probability_basis")} if e.get("probability_basis") else {}),
                **({"monte_carlo_probability": e.get("monte_carlo_champion_probability")} if e.get("monte_carlo_champion_probability") is not None else {}),
            }
            for e in _entries(champion)
            if e.get("team")
        ],
        key=lambda r: (r["probability"] is None, -(r["probability"] or 0)),
    )
    finalist_rows = sorted(
        [{"team": e.get("team"), "probability": e.get("reach_final_probability")} for e in _entries(finalist) if e.get("team")],
        key=lambda r: (r["probability"] is None, -(r["probability"] or 0)),
    )
    pair_rows = sorted(
        [{"team_1": e.get("finalist_team_1"), "team_2": e.get("finalist_team_2"),
          "pair_key": e.get("finalist_pair_key"), "probability": e.get("probability")} for e in _entries(pairs)],
        key=lambda r: (r["probability"] is None, -(r["probability"] or 0)),
    )
    main_forecast = {
        "most_likely_champion": champ_rows[0] if champ_rows else None,
        "second_most_likely_champion": champ_rows[1] if len(champ_rows) > 1 else None,
        "champion_probabilities": champ_rows,
        "champion_probability_basis": overview.get("champion_probability_basis") or (champ_rows[0].get("probability_basis") if champ_rows else None),
        "most_likely_final": pair_rows[0] if pair_rows else None,
        "finalist_probabilities": finalist_rows,
        # The pipeline forecasts champion odds, not a discrete final-winner call; kept null
        # for honesty. The UI derives a "projected final favourite" from champion odds.
        "predicted_final_winner": None,
    }

    # ---- matchday predictions (the then-upcoming matches) ----
    date_by_pair, id_by_pair = {}, {}
    for rnd in bracket.get("rounds", []) if isinstance(bracket, dict) else []:
        for m in rnd.get("matches", []) or []:
            key = frozenset([m.get("team_a"), m.get("team_b")])
            date_by_pair[key] = m.get("date")
            id_by_pair[key] = m.get("fixture_id")

    matchday = []
    for m in matchups:
        if str(m.get("prediction_status")) not in ("predicted", "", "None") and m.get("favorite") is None:
            continue
        key = frozenset([m.get("team_a"), m.get("team_b")])
        stage = m.get("stage") or ""
        is_knockout = "group" not in str(stage).lower()
        matchday.append({
            "match_id": id_by_pair.get(key) or f"{m.get('team_a')}_vs_{m.get('team_b')}_{stage}".replace(" ", "_"),
            "stage": stage,
            "scheduled_at": date_by_pair.get(key),
            "team_a": m.get("team_a"),
            "team_b": m.get("team_b"),
            "team_a_win_probability": m.get("team_a_advance_probability"),
            "team_b_win_probability": m.get("team_b_advance_probability"),
            "draw_probability": None if is_knockout else m.get("prob_draw"),
            "regulation": {"team_a_win": m.get("prob_team_a_win"), "draw": m.get("prob_draw"),
                           "team_a_loss": m.get("prob_team_a_loss")},
            "predicted_winner": m.get("favorite"),
            "prediction_method": _method_label(m),
            "status_at_snapshot": "scheduled",
            "confidence": None,
            "actual_winner": None,
            "actual_score": None,
            "prediction_outcome": "pending",
        })

    snapshot = {
        "schema_version": SCHEMA_VERSION,
        "snapshot_id": f"{_compact_ts(generated_at)}__{phase}__{completed if completed is not None else 'na'}_completed",
        "generated_at": generated_at,
        "display_date": _display_date(generated_at),
        "timezone": "America/Chicago",
        "tournament_phase": phase,
        "completed_matches": completed,
        "remaining_matches": overview.get("known_unresolved_matchups"),
        "teams_alive": overview.get("teams_alive"),
        "teams_eliminated": overview.get("teams_eliminated"),
        "provider": overview.get("provider"),
        "forecast_mode": overview.get("forecast_mode"),
        "source_quality_score": overview.get("source_quality_score"),
        "simulation_count": overview.get("simulations") or champion.get("simulations"),
        "seed": overview.get("seed"),
        "selected_model": overview.get("selected_model"),
        "run_id": overview.get("run_id") or run_manifest.get("run_id"),
        "record_class": record_class,
        "provenance": provenance or {"git_commit": _git_commit()},
        "main_forecast": main_forecast,
        "matchday_predictions": matchday,
    }
    snapshot["state_hash"] = state_hash(snapshot)
    return snapshot


def state_hash(snapshot: dict) -> str:
    """Deterministic hash of the *meaningful* forecast state, for dedup.

    Keyed on phase + completed count + the matchday prediction set (teams, advance
    probability, method) + the champion probability table. Trivial reruns over an
    unchanged tournament state hash identically; a new completed match / phase change /
    materially different probabilities produce a new hash.
    """
    key = {
        "phase": snapshot.get("tournament_phase"),
        "completed": snapshot.get("completed_matches"),
        "matchday": sorted(
            f"{m.get('team_a')}|{m.get('team_b')}|{round(m.get('team_a_win_probability') or 0, 4)}|{m.get('prediction_method')}"
            for m in snapshot.get("matchday_predictions", [])
        ),
        "champion": sorted(
            f"{c.get('team')}|{round(c.get('probability') or 0, 4)}"
            for c in (snapshot.get("main_forecast", {}).get("champion_probabilities") or [])
        ),
    }
    return hashlib.sha256(json.dumps(key, sort_keys=True).encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------- #
# storage (append-only manifest + one JSON per snapshot)
# --------------------------------------------------------------------------- #

def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"schema_version": SCHEMA_VERSION, "snapshots": []}
    return {"schema_version": SCHEMA_VERSION, "snapshots": []}


def _write_manifest(manifest: dict) -> None:
    manifest["snapshots"].sort(key=lambda s: (s.get("completed_matches") or -1, s.get("generated_at") or ""))
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def store_snapshot(snapshot: dict, force: bool = False) -> dict:
    """Write a snapshot if its state_hash is not already archived. Idempotent."""
    ensure_dirs()
    manifest = load_manifest()
    existing = {s.get("state_hash") for s in manifest["snapshots"]}
    if not force and snapshot["state_hash"] in existing:
        return {"archived": False, "reason": "duplicate_state", "state_hash": snapshot["state_hash"]}

    snap_id = snapshot["snapshot_id"]
    # guard against a same-id file (distinct state, same second): suffix the hash
    path = SNAPSHOTS_DIR / f"{snap_id}.json"
    if path.exists() and not force:
        snap_id = f"{snap_id}__{snapshot['state_hash']}"
        snapshot["snapshot_id"] = snap_id
        path = SNAPSHOTS_DIR / f"{snap_id}.json"
    path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    manifest["snapshots"] = [s for s in manifest["snapshots"] if s.get("snapshot_id") != snap_id]
    manifest["snapshots"].append({
        "snapshot_id": snap_id,
        "generated_at": snapshot.get("generated_at"),
        "display_date": snapshot.get("display_date"),
        "tournament_phase": snapshot.get("tournament_phase"),
        "completed_matches": snapshot.get("completed_matches"),
        "state_hash": snapshot.get("state_hash"),
        "record_class": snapshot.get("record_class"),
        "git_commit": (snapshot.get("provenance") or {}).get("git_commit"),
        "file": f"snapshots/{snap_id}.json",
    })
    _write_manifest(manifest)
    return {"archived": True, "snapshot_id": snap_id, "state_hash": snapshot["state_hash"]}


# --------------------------------------------------------------------------- #
# live archival (reads the currently-published public_data)
# --------------------------------------------------------------------------- #

def _read(name: str, base: Path = PUBLIC_DATA_DIR) -> Any:
    path = base / name
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


def _live_files(base: Path = PUBLIC_DATA_DIR) -> dict:
    return {
        "overview": _read("latest_overview.json", base),
        "champion": _read("champion_forecast.json", base),
        "finalist": _read("finalist_forecast.json", base),
        "finalist_pairs": _read("finalist_pairs.json", base),
        "matchups": _read("matchup_predictions.json", base),
        "bracket": _read("knockout_bracket.json", base),
        "run_manifest": _read("latest_run_manifest.json", base),
    }


def archive_current_forecast(record_class: str = RECORD_GENUINE, provenance: dict | None = None,
                             force: bool = False, dry_run: bool = False) -> dict:
    """Archive the currently-published public_data forecast as a snapshot (idempotent)."""
    files = _live_files()
    if not files["champion"] or not files["overview"]:
        return {"archived": False, "reason": "no_published_forecast"}
    snapshot = build_snapshot(files, record_class=record_class,
                              provenance=provenance or {"git_commit": _git_commit()})
    if dry_run:
        return {"archived": False, "reason": "dry_run", "snapshot_id": snapshot["snapshot_id"],
                "state_hash": snapshot["state_hash"]}
    return store_snapshot(snapshot, force=force)


# --------------------------------------------------------------------------- #
# read side: load snapshots + non-mutating actual-result enrichment
# --------------------------------------------------------------------------- #

def load_snapshot_file(rel_path: str) -> dict:
    path = HISTORY_DIR / rel_path
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_all_snapshots() -> list[dict]:
    manifest = load_manifest()
    snaps = []
    for entry in manifest.get("snapshots", []):
        snap = load_snapshot_file(entry.get("file", ""))
        if snap:
            snaps.append(snap)
    snaps.sort(key=lambda s: (s.get("completed_matches") or -1, s.get("generated_at") or ""))
    return snaps


def completed_results_index(bracket: dict | None = None) -> dict:
    """Map of frozenset({team_a, team_b}) -> {'winner','score'} from completed bracket matches."""
    bracket = bracket if bracket is not None else _read("knockout_bracket.json")
    index = {}
    for rnd in bracket.get("rounds", []) if isinstance(bracket, dict) else []:
        for m in rnd.get("matches", []) or []:
            if str(m.get("state")) == "completed" and m.get("winner"):
                index[frozenset([m.get("team_a"), m.get("team_b")])] = {
                    "winner": m.get("winner"), "score": m.get("score"),
                }
    return index


def enrich_snapshot(snapshot: dict, results: dict | None = None) -> dict:
    """Return a shallow copy with matchday predictions joined to actual results.

    The stored snapshot is never mutated; only the returned copy carries derived
    actual_winner / prediction_outcome fields.
    """
    results = results if results is not None else completed_results_index()
    enriched = dict(snapshot)
    out = []
    for m in snapshot.get("matchday_predictions", []):
        m = dict(m)
        actual = results.get(frozenset([m.get("team_a"), m.get("team_b")]))
        if actual:
            m["actual_winner"] = actual["winner"]
            m["actual_score"] = actual.get("score")
            pred = m.get("predicted_winner")
            m["prediction_outcome"] = "correct" if pred and pred == actual["winner"] else "incorrect"
        else:
            m["actual_winner"] = None
            m["prediction_outcome"] = "pending"
        out.append(m)
    enriched["matchday_predictions"] = out
    return enriched
