"""Fail-capable validation for public exports and dashboard inputs."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from src.config import PROJECT_ROOT
from src.public_export.build_public_exports import PUBLIC_DATA_DIR, SOURCE_LABELS
from src.utils.dates import now_utc_iso

EXPORT_REPORT_DIR = PROJECT_ROOT / "outputs" / "reports" / "public_export"
DASHBOARD_REPORT_DIR = PROJECT_ROOT / "outputs" / "reports" / "dashboard"

REQUIRED_EXPORTS = {
    "latest_overview.json": ["current_phase", "completed_matches", "top_champion", "forecast_mode", "provider", "_meta"],
    "knockout_bracket.json": ["rounds", "source_legend", "_meta"],
    "champion_forecast.json": ["entries", "_meta"],
    "finalist_forecast.json": ["entries", "_meta"],
    "finalist_pairs.json": ["entries", "_meta"],
    "matchup_predictions.json": ["matchups", "_meta"],
    "teams.json": ["teams", "_meta"],
    "team_stats.json": ["team_stats", "_meta"],
    "system_health.json": ["quality_gate", "validations", "_meta"],
    "latest_run_manifest.json": ["run_id", "forecast_mode", "_meta"],
}

VALID_STATUSES = {"alive", "eliminated", "champion", "runner_up", "third_place"}
VALID_SOURCES = set(SOURCE_LABELS) | {"unresolved_tbd"}


def _load_secret_values() -> list[str]:
    values = []
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            match = re.match(r"\s*[A-Za-z_0-9]+\s*=\s*(.+)", line)
            if match and len(match.group(1).strip().strip("\"'")) >= 8:
                values.append(match.group(1).strip().strip("\"'"))
    return values


def _check(rows: list, check: str, ok: bool, message: str) -> None:
    rows.append({"check": check, "status": "pass" if ok else "fail", "message": message})


def validate_public_exports(directory: Path | None = None, write_report: bool = True) -> dict:
    data_dir = Path(directory) if directory else PUBLIC_DATA_DIR
    rows: list[dict] = []
    payloads: dict[str, dict] = {}
    for name, required_keys in REQUIRED_EXPORTS.items():
        path = data_dir / name
        if not path.exists():
            _check(rows, f"{name}:readable", False, "file missing")
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            payloads[name] = payload
            missing = [key for key in required_keys if key not in payload]
            _check(rows, f"{name}:required_keys", not missing, f"missing keys: {missing}" if missing else "all required keys present")
        except Exception as exc:
            _check(rows, f"{name}:readable", False, f"unreadable JSON: {exc}")
    champion = payloads.get("champion_forecast.json", {})
    if champion.get("entries"):
        values = [e.get("champion_probability") for e in champion["entries"]]
        in_range = all(v is not None and 0 <= v <= 1 for v in values)
        _check(rows, "champion:probabilities_in_range", in_range, "all champion probabilities in [0,1]" if in_range else "out-of-range champion probability")
        total = sum(v or 0 for v in values)
        _check(rows, "champion:sums_to_one", abs(total - 1) <= 0.01, f"sum={total:.4f}")
    pairs = payloads.get("finalist_pairs.json", {})
    if pairs.get("entries"):
        total = sum(e.get("probability") or 0 for e in pairs["entries"])
        _check(rows, "finalist_pairs:sums_to_one", abs(total - 1) <= 0.01, f"sum={total:.4f}")
    teams_payload = payloads.get("teams.json", {})
    teams = teams_payload.get("teams", [])
    if teams:
        statuses = {t.get("status") for t in teams}
        _check(rows, "teams:status_vocabulary", statuses <= VALID_STATUSES, f"invalid statuses: {sorted(statuses - VALID_STATUSES)}" if statuses - VALID_STATUSES else "all statuses valid")
        slugs = [t.get("slug") for t in teams]
        duplicate_slugs = {s for s in slugs if slugs.count(s) > 1}
        _check(rows, "teams:unique_slugs", not duplicate_slugs, f"duplicate slugs: {sorted(duplicate_slugs)}" if duplicate_slugs else f"{len(slugs)} unique team slugs")
        tbd_teams = [t["team"] for t in teams if str(t.get("team", "")).upper().startswith("TBD")]
        _check(rows, "teams:no_placeholder_teams", not tbd_teams, f"placeholder teams present: {tbd_teams}" if tbd_teams else "no TBD placeholder appears as a team")
        eliminated_with_probability = [t["team"] for t in teams if t.get("status") == "eliminated" and (t.get("champion_probability") or 0) > 0]
        _check(rows, "teams:eliminated_have_zero_probability", not eliminated_with_probability, f"eliminated teams with champion probability: {eliminated_with_probability}" if eliminated_with_probability else "no eliminated team carries championship probability")
        eliminated_with_matchup = [t["team"] for t in teams if t.get("status") == "eliminated" and t.get("next_matchup")]
        _check(rows, "teams:eliminated_have_no_next_matchup", not eliminated_with_matchup, f"eliminated teams with next matchup: {eliminated_with_matchup}" if eliminated_with_matchup else "no eliminated team has an active next matchup")
        champion_names = {e.get("team") for e in champion.get("entries", [])}
        eliminated_names = {t["team"] for t in teams if t.get("status") == "eliminated"}
        overlap = champion_names & eliminated_names
        _check(rows, "champion:no_eliminated_candidates", not overlap, f"eliminated teams in champion forecast: {sorted(overlap)}" if overlap else "champion candidates are all non-eliminated")
    bracket = payloads.get("knockout_bracket.json", {})
    if bracket.get("rounds"):
        all_matches = [m for r in bracket["rounds"] for m in r["matches"]]
        bad_states = [m for m in all_matches if m.get("state") not in {"completed", "scheduled_known", "tbd"}]
        _check(rows, "bracket:valid_states", not bad_states, f"{len(bad_states)} matches with invalid state" if bad_states else f"{len(all_matches)} matches with valid states")
        completed_missing = [m for m in all_matches if m.get("state") == "completed" and (not m.get("score") or not m.get("winner"))]
        _check(rows, "bracket:completed_have_scores", not completed_missing, f"{len(completed_missing)} completed matches missing score/winner" if completed_missing else "all completed matches carry score and winner")
        bad_sources = {m.get("source") for m in all_matches} - VALID_SOURCES
        _check(rows, "bracket:source_vocabulary", not bad_sources, f"invalid sources: {sorted(bad_sources)}" if bad_sources else "all bracket sources use the declared vocabulary")
        tbd_named = [m for m in all_matches if m.get("state") == "tbd" and (m.get("team_a") or m.get("team_b"))]
        _check(rows, "bracket:tbd_not_named", not tbd_named, f"{len(tbd_named)} TBD matches carry team names" if tbd_named else "TBD matches carry no team names")
    matchups = payloads.get("matchup_predictions.json", {}).get("matchups", [])
    predicted = [m for m in matchups if m.get("prediction_status") == "predicted"]
    if predicted:
        model_backed = all(m.get("model") and str(m.get("probability_source", "")).startswith("live_model") for m in predicted)
        _check(rows, "matchups:xgboost_backed", model_backed, "all predicted matchups carry model name and live_model source" if model_backed else "a predicted matchup lacks model backing")
        sums = [abs((m.get("team_a_advance_probability") or 0) + (m.get("team_b_advance_probability") or 0) - 1) for m in predicted]
        _check(rows, "matchups:advance_sums_to_one", max(sums) <= 0.01, f"max deviation {max(sums):.5f}")
    overview = payloads.get("latest_overview.json", {})
    manifest = payloads.get("latest_run_manifest.json", {})
    if overview and manifest:
        _check(rows, "overview:phase_matches_manifest", overview.get("current_phase") == manifest.get("current_phase"), f"overview={overview.get('current_phase')} manifest={manifest.get('current_phase')}")
        _check(rows, "overview:provider_matches_manifest", overview.get("provider") == manifest.get("provider"), f"overview={overview.get('provider')} manifest={manifest.get('provider')}")
        _check(rows, "overview:forecast_mode_matches_manifest", overview.get("forecast_mode") == manifest.get("forecast_mode"), f"overview={overview.get('forecast_mode')} manifest={manifest.get('forecast_mode')}")
    timestamp_ok = True
    for name, payload in payloads.items():
        generated_at = (payload.get("_meta") or {}).get("generated_at")
        try:
            datetime.fromisoformat(str(generated_at).replace("Z", "+00:00"))
        except Exception:
            timestamp_ok = False
            _check(rows, f"{name}:timestamp_parseable", False, f"unparseable generated_at: {generated_at}")
    if timestamp_ok:
        _check(rows, "exports:timestamps_parseable", True, "all _meta.generated_at timestamps parse")
    secrets = _load_secret_values()
    leaked = []
    private_paths = []
    for path in data_dir.glob("*.json"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(secret in text for secret in secrets):
            leaked.append(path.name)
        if re.search(r"[A-Za-z]:\\\\Users|/Users/[a-z]", text):
            private_paths.append(path.name)
    _check(rows, "exports:no_secret_values", not leaked, f"secret values found in: {leaked}" if leaked else f"{len(secrets)} secret values checked, 0 hits")
    _check(rows, "exports:no_private_local_paths", not private_paths, f"private paths found in: {private_paths}" if private_paths else "no private local paths in exports")
    if not write_report:
        failed = [row for row in rows if row["status"] == "fail"]
        return {"status": "fail" if failed else "pass", "checks": len(rows), "failed": len(failed), "report": "not_written", "rows": rows}
    return _write_report(rows, EXPORT_REPORT_DIR, "public_export_validation", "Public Export Validation")


def validate_dashboard() -> dict:
    """Dashboard-facing validation: exports plus the extra files the dashboard reads."""
    export_result = validate_public_exports()
    rows = [{"check": "public_exports_overall", "status": export_result["status"], "message": f"{export_result['report']}"}]
    live_dir = PROJECT_ROOT / "outputs" / "live_state"
    for name in ["latest_live_run_manifest.json", "live_provider_freshness.json", "probability_source_history.csv"]:
        _check(rows, f"dashboard_input:{name}", (live_dir / name).exists(), "readable" if (live_dir / name).exists() else "missing")
    stats_path = PUBLIC_DATA_DIR / "team_stats.json"
    if stats_path.exists():
        stats = json.loads(stats_path.read_text(encoding="utf-8")).get("team_stats", {})
        future_dated = 0
        now = pd.Timestamp(now_utc_iso().replace("+00:00", "")) + pd.Timedelta(hours=1)
        for entry in stats.values():
            for match in entry.get("matches", []):
                if pd.to_datetime(match.get("date"), errors="coerce") > now:
                    future_dated += 1
        _check(rows, "team_stats:only_completed_matches", future_dated == 0, f"{future_dated} future-dated rows in completed stats" if future_dated else "team stats contain only completed (non-future) matches")
        names = [entry.get("team") for entry in stats.values()]
        _check(rows, "team_stats:no_duplicate_identities", len(names) == len(set(names)), "duplicate team identities" if len(names) != len(set(names)) else f"{len(names)} unique team identities")
    for history_name, id_columns in [
        ("champion_probability_history.csv", ["run_id", "team"]),
        ("finalist_probability_history.csv", ["run_id", "team"]),
        ("finalist_pair_probability_history.csv", ["run_id", "finalist_team_1", "finalist_team_2"]),
        ("probability_source_history.csv", ["run_id"]),
    ]:
        history_path = live_dir / history_name
        if not history_path.exists():
            continue
        history = pd.read_csv(history_path)
        columns = [c for c in id_columns if c in history.columns]
        duplicates = int(history.duplicated(subset=columns).sum()) if columns else -1
        _check(rows, f"history:{history_name}:no_duplicate_run_entries", duplicates == 0, f"{duplicates} duplicate {columns} rows" if duplicates else f"{len(history)} rows, no duplicate {columns} entries")
    return _write_report(rows, DASHBOARD_REPORT_DIR, "dashboard_validation", "Dashboard Validation")


def _write_report(rows: list[dict], directory: Path, basename: str, title: str) -> dict:
    directory.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame(rows)
    frame.to_csv(directory / f"{basename}.csv", index=False)
    lines = [f"# {title}", "", f"- Generated: {now_utc_iso()}", "", "| Check | Status | Message |", "|---|---|---|"]
    for row in rows:
        lines.append(f"| {row['check']} | {row['status']} | {str(row['message']).replace('|', '/')} |")
    (directory / f"{basename}.md").write_text("\n".join(lines), encoding="utf-8")
    failed = [row for row in rows if row["status"] == "fail"]
    return {"status": "fail" if failed else "pass", "checks": len(rows), "failed": len(failed), "report": str(directory / f"{basename}.md")}
