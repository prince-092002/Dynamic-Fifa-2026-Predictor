"""API-Football fetcher."""

import json
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import requests

from src.cleaning.standardize_team_names import standardize_team_columns
from src.config import API_FOOTBALL_KEY, API_FOOTBALL_WORLD_CUP_LEAGUE_ID, PROCESSED_DIR, RAW_API_FOOTBALL_DIR, REPORTS_DIR
from src.logger import get_logger
from src.utils.dates import now_utc_iso
from src.utils.files import (
    FIXTURES_2026_COLUMNS,
    RESULTS_2026_COLUMNS,
    append_fetch_log,
    save_csv,
)
from src.utils.http import get_json

logger = get_logger(__name__)

BASE_URL = "https://v3.football.api-sports.io"
WORLD_CUP_LEAGUE_ID = int(API_FOOTBALL_WORLD_CUP_LEAGUE_ID or 1)
WORLD_CUP_SEASON = 2026
COMPLETED = {"FT", "AET", "PEN", "Match Finished"}
LIVE = {"1H", "2H", "HT", "ET", "P", "BT", "LIVE", "In Play"}
POSTPONED = {"PST", "Postponed", "SUSP", "INT"}
CANCELLED = {"CANC", "ABD", "AWD", "Cancelled", "Canceled", "Abandoned"}
SCHEDULED = {"NS", "TBD", "Not Started", "Time to be defined", "Scheduled"}


def _skip_missing_key(source: str) -> dict:
    message = "API_FOOTBALL_KEY is missing from .env; skipping API-Football."
    logger.warning(message)
    append_fetch_log(source=source, source_url=BASE_URL, status="skipped", notes=message)
    return {
        "source": source,
        "status": "skipped",
        "rows_fetched": 0,
        "output_file": "",
        "error_message": message,
    }


def _save_json(data: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def api_football_request(endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Call API-Football using the key from .env."""
    if not API_FOOTBALL_KEY:
        raise RuntimeError("API_FOOTBALL_KEY is missing")
    headers = {"x-apisports-key": API_FOOTBALL_KEY}
    url = f"{BASE_URL}/{endpoint.lstrip('/')}"
    return get_json(url, headers=headers, params=params, timeout=30)


def _sanitize_response(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        return {"response": data}
    sanitized = dict(data)
    sanitized.pop("parameters", None)
    return sanitized


def _api_status_message(data: dict[str, Any]) -> str:
    errors = data.get("errors")
    if isinstance(errors, dict) and errors:
        return "; ".join(f"{key}: {value}" for key, value in errors.items())
    if errors:
        return str(errors)
    return "ok"


def diagnose_api_football() -> dict:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = REPORTS_DIR / "api_football_diagnostic.json"
    md_path = REPORTS_DIR / "api_football_diagnostic.md"
    if not API_FOOTBALL_KEY:
        payload = {"key_present": False, "key_valid": False, "issue": "missing key"}
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        md_path.write_text("# API-Football Diagnostic\n\n- Key present: no\n- Likely issue: missing key\n", encoding="utf-8")
        return {"status": "missing_key", "report": str(md_path)}
    try:
        response = requests.get(f"{BASE_URL}/status", headers={"x-apisports-key": API_FOOTBALL_KEY}, timeout=30)
        try:
            data = response.json()
        except Exception:
            data = {"raw_text": response.text[:1000]}
        sanitized = _sanitize_response(data)
        json_path.write_text(json.dumps({"http_status": response.status_code, "data": sanitized}, indent=2), encoding="utf-8")
        message = _api_status_message(data)
        quota = data.get("response", {}).get("requests", {}) if isinstance(data.get("response"), dict) else {}
        key_valid = response.status_code == 200 and not data.get("errors")
        likely = "key appears valid" if key_valid else _likely_api_issue(response.status_code, message)
        lines = [
            "# API-Football Diagnostic",
            "",
            "- Key present: yes",
            f"- HTTP status code: {response.status_code}",
            f"- API response status/message: {message}",
            f"- Remaining quota if available: {quota.get('current', 'unknown')} used / {quota.get('limit_day', 'unknown')} daily limit",
            f"- Key appears valid: {'yes' if key_valid else 'no'}",
            f"- Likely issue: {likely}",
            "",
            "No API secrets are printed in this report.",
        ]
        md_path.write_text("\n".join(lines), encoding="utf-8")
        return {"status": "success" if key_valid else "failed", "report": str(md_path), "http_status": response.status_code}
    except Exception as exc:
        json_path.write_text(json.dumps({"key_present": True, "error": str(exc)}, indent=2), encoding="utf-8")
        md_path.write_text(f"# API-Football Diagnostic\n\n- Key present: yes\n- Likely issue: {exc}\n", encoding="utf-8")
        return {"status": "failed", "report": str(md_path), "error": str(exc)}


def _likely_api_issue(status_code: int, message: str) -> str:
    lowered = str(message).lower()
    if status_code in {401, 403} or "key" in lowered:
        return "invalid key, expired key, or endpoint not included in plan"
    if status_code == 429 or "rate" in lowered:
        return "rate limit reached"
    if status_code == 404:
        return "wrong endpoint"
    return "request failed, plan limitation, or no FIFA 2026 data available yet"


def discover_api_football_world_cup_2026_league() -> dict:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    RAW_API_FOOTBALL_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_API_FOOTBALL_DIR / "world_cup_2026_league_candidates.json"
    csv_path = REPORTS_DIR / "api_football_league_candidates.csv"
    md_path = REPORTS_DIR / "api_football_league_discovery.md"
    if API_FOOTBALL_WORLD_CUP_LEAGUE_ID:
        rows = [{"league_id": API_FOOTBALL_WORLD_CUP_LEAGUE_ID, "league_name": "configured in .env", "country": "", "season": WORLD_CUP_SEASON, "type": "", "confidence_score": 100, "reason_selected": "API_FOOTBALL_WORLD_CUP_LEAGUE_ID is set"}]
        pd.DataFrame(rows).to_csv(csv_path, index=False)
        raw_path.write_text(json.dumps({"configured_league_id": API_FOOTBALL_WORLD_CUP_LEAGUE_ID}, indent=2), encoding="utf-8")
        md_path.write_text("# API-Football League Discovery\n\nUsing `API_FOOTBALL_WORLD_CUP_LEAGUE_ID` from `.env`.\n", encoding="utf-8")
        return {"league_id": int(API_FOOTBALL_WORLD_CUP_LEAGUE_ID), "status": "configured", "report": str(md_path)}
    if not API_FOOTBALL_KEY:
        pd.DataFrame(columns=["league_id", "league_name", "country", "season", "type", "confidence_score", "reason_selected"]).to_csv(csv_path, index=False)
        md_path.write_text("# API-Football League Discovery\n\nAPI_FOOTBALL_KEY is missing, so discovery could not run.\n", encoding="utf-8")
        return {"league_id": WORLD_CUP_LEAGUE_ID, "status": "missing_key", "report": str(md_path)}
    candidates = []
    raw_payloads = []
    for search in ["World Cup", "FIFA World Cup", "World Championship", "World"]:
        data = api_football_request("leagues", {"search": search, "season": WORLD_CUP_SEASON})
        raw_payloads.append({"search": search, "data": _sanitize_response(data)})
        for item in data.get("response", []):
            league = item.get("league", {})
            country = item.get("country", {})
            seasons = item.get("seasons", [])
            for season in seasons or [{"year": WORLD_CUP_SEASON}]:
                if int(season.get("year") or 0) != WORLD_CUP_SEASON:
                    continue
                name = league.get("name", "")
                score = 0
                lower = name.lower()
                if "fifa world cup" in lower:
                    score += 80
                elif "world cup" in lower:
                    score += 60
                elif "world" in lower:
                    score += 25
                if country.get("name") == "World":
                    score += 15
                candidates.append(
                    {
                        "league_id": league.get("id"),
                        "league_name": name,
                        "country": country.get("name"),
                        "season": WORLD_CUP_SEASON,
                        "type": league.get("type"),
                        "confidence_score": score,
                        "reason_selected": "candidate from league search",
                    }
                )
    raw_path.write_text(json.dumps(raw_payloads, indent=2), encoding="utf-8")
    df = pd.DataFrame(candidates).drop_duplicates(subset=["league_id", "season"]) if candidates else pd.DataFrame(columns=["league_id", "league_name", "country", "season", "type", "confidence_score", "reason_selected"])
    df.to_csv(csv_path, index=False)
    high = df[df["confidence_score"] >= 75] if not df.empty else df
    selected = int(high.iloc[0]["league_id"]) if len(high) == 1 else WORLD_CUP_LEAGUE_ID
    lines = ["# API-Football League Discovery", "", "| league_id | league_name | country | season | type | confidence_score | reason_selected |", "|---:|---|---|---:|---|---:|---|"]
    for _, row in df.iterrows():
        lines.append(f"| {row['league_id']} | {row['league_name']} | {row['country']} | {row['season']} | {row['type']} | {row['confidence_score']} | {row['reason_selected']} |")
    lines.append("")
    if len(high) == 1:
        lines.append(f"Selected league ID `{selected}` automatically because exactly one high-confidence match was found.")
    elif len(high) > 1:
        lines.append("Multiple high-confidence matches were found. Copy the correct ID into `.env` as `API_FOOTBALL_WORLD_CUP_LEAGUE_ID=`.")
    else:
        lines.append("No high-confidence match was found. Review the candidates before setting `API_FOOTBALL_WORLD_CUP_LEAGUE_ID=`.")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"league_id": selected, "status": "selected" if len(high) == 1 else "needs_user_selection", "report": str(md_path)}


def _flatten_fixtures(data: Dict[str, Any], completed_only: bool = False) -> pd.DataFrame:
    rows = []
    for item in data.get("response", []):
        fixture = item.get("fixture", {})
        league = item.get("league", {})
        teams = item.get("teams", {})
        goals = item.get("goals", {})
        status = fixture.get("status", {}).get("short") or fixture.get("status", {}).get("long")
        normalized_status = normalize_api_status(status)
        if completed_only and normalized_status != "completed":
            continue
        rows.append(
            {
                "match_id": fixture.get("id"),
                "date": fixture.get("date"),
                "stage": league.get("round"),
                "group": pd.NA,
                "team_a": teams.get("home", {}).get("name"),
                "team_b": teams.get("away", {}).get("name"),
                "venue": fixture.get("venue", {}).get("name"),
                "city": fixture.get("venue", {}).get("city"),
                "country": "Canada/Mexico/United States",
                "status": normalized_status,
                "team_a_goals": goals.get("home"),
                "team_b_goals": goals.get("away"),
                "source": "api_football",
                "last_updated": now_utc_iso(),
            }
        )
    return pd.DataFrame(rows)


def normalize_api_status(status: object) -> str:
    if pd.isna(status):
        return "unknown"
    text = str(status).strip()
    if text in COMPLETED or text.lower() in {item.lower() for item in COMPLETED}:
        return "completed"
    if text in LIVE or text.lower() in {item.lower() for item in LIVE}:
        return "live"
    if text in POSTPONED or text.lower() in {item.lower() for item in POSTPONED}:
        return "postponed"
    if text in CANCELLED or text.lower() in {item.lower() for item in CANCELLED}:
        return "cancelled"
    if text in SCHEDULED or text.lower() in {item.lower() for item in SCHEDULED}:
        return "scheduled"
    return "unknown"


def _save_if_rows_or_empty(path: Path, df: pd.DataFrame, columns: list[str]) -> None:
    from src.utils.files import has_real_rows

    if not df.empty or not has_real_rows(path, columns):
        save_csv(df, path, columns)


def _save_processed_fixture_outputs(data: Dict[str, Any]) -> tuple[Path, Path, int]:
    fixtures = _flatten_fixtures(data, completed_only=False)
    fixtures = standardize_team_columns(fixtures, ["team_a", "team_b"]) if not fixtures.empty else fixtures
    fixture_output = PROCESSED_DIR / "fixtures_2026_api_football.csv"
    canonical_fixture_output = PROCESSED_DIR / "fixtures_2026.csv"
    _save_if_rows_or_empty(fixture_output, fixtures, FIXTURES_2026_COLUMNS)
    _save_if_rows_or_empty(canonical_fixture_output, fixtures, FIXTURES_2026_COLUMNS)

    results = _flatten_fixtures(data, completed_only=True)
    if not results.empty:
        results = standardize_team_columns(results, ["team_a", "team_b"])
        results["team_a_goals"] = pd.to_numeric(results["team_a_goals"], errors="coerce")
        results["team_b_goals"] = pd.to_numeric(results["team_b_goals"], errors="coerce")
        results["winner"] = results.apply(
            lambda row: row["team_a"]
            if row["team_a_goals"] > row["team_b_goals"]
            else row["team_b"]
            if row["team_b_goals"] > row["team_a_goals"]
            else "Draw",
            axis=1,
        )
        results["is_draw"] = results["winner"].eq("Draw")
    result_output = PROCESSED_DIR / "results_2026_api_football.csv"
    canonical_result_output = PROCESSED_DIR / "results_2026.csv"
    _save_if_rows_or_empty(result_output, results, RESULTS_2026_COLUMNS)
    _save_if_rows_or_empty(canonical_result_output, results, RESULTS_2026_COLUMNS)
    return fixture_output, result_output, len(fixtures)


def fetch_api_football_fixtures_2026() -> dict:
    if not API_FOOTBALL_KEY:
        return _skip_missing_key("api_football_fixtures")
    raw_output = RAW_API_FOOTBALL_DIR / "fixtures_2026.json"
    try:
        data = api_football_request("fixtures", {"league": WORLD_CUP_LEAGUE_ID, "season": WORLD_CUP_SEASON})
        _save_json(data, raw_output)
        fixture_output, result_output, rows = _save_processed_fixture_outputs(data)
        append_fetch_log(
            source="api_football_fixtures",
            source_url=f"{BASE_URL}/fixtures",
            status="success",
            rows_fetched=rows,
            raw_output_path=str(raw_output),
            processed_output_path=f"{fixture_output}; {result_output}",
        )
        return {
            "source": "api_football_fixtures",
            "status": "success",
            "rows_fetched": rows,
            "output_file": str(fixture_output),
            "error_message": "",
        }
    except Exception as exc:
        logger.exception("API-Football fixtures fetch failed")
        append_fetch_log("api_football_fixtures", f"{BASE_URL}/fixtures", "failed", notes=str(exc))
        return {"source": "api_football_fixtures", "status": "failed", "rows_fetched": 0, "output_file": str(raw_output), "error_message": str(exc)}


def fetch_api_football_results_2026() -> dict:
    if not API_FOOTBALL_KEY:
        return _skip_missing_key("api_football_results")
    raw_output = RAW_API_FOOTBALL_DIR / "results_2026.json"
    try:
        data = api_football_request("fixtures", {"league": WORLD_CUP_LEAGUE_ID, "season": WORLD_CUP_SEASON})
        _save_json(data, raw_output)
        _, result_output, rows = _save_processed_fixture_outputs(data)
        append_fetch_log(
            source="api_football_results",
            source_url=f"{BASE_URL}/fixtures",
            status="success",
            rows_fetched=rows,
            raw_output_path=str(raw_output),
            processed_output_path=str(result_output),
        )
        return {
            "source": "api_football_results",
            "status": "success",
            "rows_fetched": rows,
            "output_file": str(result_output),
            "error_message": "",
        }
    except Exception as exc:
        logger.exception("API-Football results fetch failed")
        append_fetch_log("api_football_results", f"{BASE_URL}/fixtures", "failed", notes=str(exc))
        return {"source": "api_football_results", "status": "failed", "rows_fetched": 0, "output_file": str(raw_output), "error_message": str(exc)}


def fetch_api_football_teams_2026() -> dict:
    if not API_FOOTBALL_KEY:
        return _skip_missing_key("api_football_teams")
    raw_output = RAW_API_FOOTBALL_DIR / "teams_2026.json"
    try:
        data = api_football_request("teams", {"league": WORLD_CUP_LEAGUE_ID, "season": WORLD_CUP_SEASON})
        _save_json(data, raw_output)
        rows = len(data.get("response", []))
        append_fetch_log("api_football_teams", f"{BASE_URL}/teams", "success", rows, str(raw_output))
        return {"source": "api_football_teams", "status": "success", "rows_fetched": rows, "output_file": str(raw_output), "error_message": ""}
    except Exception as exc:
        logger.exception("API-Football teams fetch failed")
        append_fetch_log("api_football_teams", f"{BASE_URL}/teams", "failed", notes=str(exc))
        return {"source": "api_football_teams", "status": "failed", "rows_fetched": 0, "output_file": str(raw_output), "error_message": str(exc)}


def fetch_api_football_standings_2026() -> dict:
    if not API_FOOTBALL_KEY:
        return _skip_missing_key("api_football_standings")
    raw_output = RAW_API_FOOTBALL_DIR / "standings_2026.json"
    try:
        data = api_football_request("standings", {"league": WORLD_CUP_LEAGUE_ID, "season": WORLD_CUP_SEASON})
        _save_json(data, raw_output)
        rows = len(data.get("response", []))
        append_fetch_log("api_football_standings", f"{BASE_URL}/standings", "success", rows, str(raw_output))
        return {"source": "api_football_standings", "status": "success", "rows_fetched": rows, "output_file": str(raw_output), "error_message": ""}
    except Exception as exc:
        logger.exception("API-Football standings fetch failed")
        append_fetch_log("api_football_standings", f"{BASE_URL}/standings", "failed", notes=str(exc))
        return {"source": "api_football_standings", "status": "failed", "rows_fetched": 0, "output_file": str(raw_output), "error_message": str(exc)}


def fetch_api_football_team_stats_2026() -> dict:
    if not API_FOOTBALL_KEY:
        return _skip_missing_key("api_football_team_stats")
    raw_output = RAW_API_FOOTBALL_DIR / "team_stats_2026.json"
    message = "API-Football team stats need a specific team id; fetch teams first, then call this per team."
    _save_json({"message": message, "response": []}, raw_output)
    append_fetch_log("api_football_team_stats", f"{BASE_URL}/teams/statistics", "skipped", raw_output_path=str(raw_output), notes=message)
    return {"source": "api_football_team_stats", "status": "skipped", "rows_fetched": 0, "output_file": str(raw_output), "error_message": message}


fetch_api_football_fixtures = fetch_api_football_fixtures_2026
fetch_api_football_results = fetch_api_football_results_2026
fetch_api_football_teams = fetch_api_football_teams_2026
fetch_api_football_standings = fetch_api_football_standings_2026
fetch_api_football_team_stats = fetch_api_football_team_stats_2026
