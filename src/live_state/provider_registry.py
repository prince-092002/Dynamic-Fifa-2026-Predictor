"""Live provider registry and selection."""

from __future__ import annotations

import pandas as pd

from src.config import SPORTMONKS_KEY
from src.live_state.api_football_diagnostics import run_api_football_live_diagnostics
from src.live_state.live_config import LIVE_STATE_DIR
from src.live_state.providers.football_data_org_provider import FootballDataOrgProvider

PROVIDER_REPORT_DIR = LIVE_STATE_DIR.parent / "reports" / "live_state" / "providers"


def diagnose_live_providers() -> dict:
    PROVIDER_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    details = {}
    api = run_api_football_live_diagnostics()
    api_status = "available_true_live" if api["completed_count"] > 0 and api["standings_count"] > 0 else "available_schedule_only" if api["fixtures_count"] > 0 else "no_2026_rows"
    rows.append(
        {
            "provider": "api_football",
            "provider_status": api_status,
            "credentials_available": True,
            "fixture_rows": api["fixtures_count"],
            "completed_rows": api["completed_count"],
            "live_rows": api["live_count"],
            "scheduled_rows": api["scheduled_count"],
            "teams_rows": 0,
            "standings_rows": api["standings_count"],
            "bracket_rows": 0,
            "can_support_true_live": api_status == "available_true_live",
            "can_support_partial_live": api["fixtures_count"] > 0,
            "priority": 1,
        }
    )
    details["api_football"] = api
    football_data = FootballDataOrgProvider().diagnose()
    summary = football_data["summary"]
    rows.append(
        {
            "provider": summary["provider"],
            "provider_status": summary["provider_status"],
            "credentials_available": summary["credentials_available"],
            "fixture_rows": summary["fixture_rows"],
            "completed_rows": summary["completed_rows"],
            "live_rows": summary["live_rows"],
            "scheduled_rows": summary["scheduled_rows"],
            "teams_rows": summary["teams_rows"],
            "standings_rows": summary["standings_rows"],
            "bracket_rows": summary["bracket_rows"],
            "can_support_true_live": summary["can_support_true_live"],
            "can_support_partial_live": summary["can_support_partial_live"],
            "priority": 2,
        }
    )
    details["football_data_org"] = football_data
    rows.extend(_placeholder_provider_rows())
    comparison = pd.DataFrame(rows)
    comparison["selection_score"] = comparison.apply(_selection_score, axis=1)
    comparison = comparison.sort_values(["selection_score", "priority"], ascending=[False, True])
    comparison_path = PROVIDER_REPORT_DIR / "provider_comparison.csv"
    comparison.to_csv(comparison_path, index=False)
    selected = comparison.iloc[0].to_dict() if not comparison.empty and comparison.iloc[0]["selection_score"] > 0 else {}
    report = write_provider_selection_report(comparison, selected)
    return {"comparison": comparison, "selected": selected, "details": details, "comparison_path": str(comparison_path), "report": report}


def select_live_provider() -> dict:
    result = diagnose_live_providers()
    selected = result["selected"]
    if selected and selected.get("provider") == "football_data_org":
        detail = result["details"]["football_data_org"]
        return {"provider": "football_data_org", "selection": selected, "data": detail, "report": result["report"], "comparison_path": result["comparison_path"]}
    if selected and selected.get("provider") == "api_football":
        return {"provider": "api_football", "selection": selected, "data": result["details"]["api_football"], "report": result["report"], "comparison_path": result["comparison_path"]}
    return {"provider": "none", "selection": {}, "data": {}, "report": result["report"], "comparison_path": result["comparison_path"]}


def write_provider_selection_report(comparison: pd.DataFrame, selected: dict) -> str:
    PROVIDER_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = PROVIDER_REPORT_DIR / "provider_selection_report.md"
    lines = [
        "# Live Provider Selection Report",
        "",
        f"- Selected provider: {selected.get('provider', 'none') if selected else 'none'}",
        f"- Selected provider status: {selected.get('provider_status', 'none') if selected else 'none'}",
        "",
        "| Provider | Status | Fixtures | Completed | Standings | Bracket | Score |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for _, row in comparison.iterrows():
        lines.append(
            f"| {row['provider']} | {row['provider_status']} | {row['fixture_rows']} | {row['completed_rows']} | {row['standings_rows']} | {row['bracket_rows']} | {row['selection_score']} |"
        )
    lines.extend(["", "Provider selection never treats fallback bracket mapping as official."])
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def _selection_score(row: pd.Series) -> int:
    score = 0
    if row.get("fixture_rows", 0) > 0:
        score += 30
    if row.get("completed_rows", 0) > 0 or row.get("live_rows", 0) > 0:
        score += 25
    if row.get("standings_rows", 0) > 0:
        score += 20
    if row.get("bracket_rows", 0) > 0:
        score += 10
    if row.get("can_support_true_live", False):
        score += 20
    if row.get("provider_status") in {"credentials_missing", "unauthorized", "forbidden_plan", "no_2026_rows", "endpoint_error"}:
        score -= 25
    return max(int(score), 0)


def _placeholder_provider_rows() -> list[dict]:
    return [
        {
            "provider": "sportmonks",
            "provider_status": "credentials_missing" if not SPORTMONKS_KEY else "endpoint_error",
            "credentials_available": bool(SPORTMONKS_KEY),
            "fixture_rows": 0,
            "completed_rows": 0,
            "live_rows": 0,
            "scheduled_rows": 0,
            "teams_rows": 0,
            "standings_rows": 0,
            "bracket_rows": 0,
            "can_support_true_live": False,
            "can_support_partial_live": False,
            "priority": 3,
        },
        {
            "provider": "fifa_official",
            "provider_status": "endpoint_error",
            "credentials_available": True,
            "fixture_rows": 0,
            "completed_rows": 0,
            "live_rows": 0,
            "scheduled_rows": 0,
            "teams_rows": 0,
            "standings_rows": 0,
            "bracket_rows": 0,
            "can_support_true_live": False,
            "can_support_partial_live": False,
            "priority": 4,
        },
        {
            "provider": "manual_live",
            "provider_status": "no_2026_rows",
            "credentials_available": True,
            "fixture_rows": 0,
            "completed_rows": 0,
            "live_rows": 0,
            "scheduled_rows": 0,
            "teams_rows": 0,
            "standings_rows": 0,
            "bracket_rows": 0,
            "can_support_true_live": False,
            "can_support_partial_live": False,
            "priority": 5,
        },
    ]
