"""Build current standings from live/API standings or completed fixtures."""

from __future__ import annotations

import pandas as pd

from src.live_state.live_config import LIVE_REPORT_DIR, LIVE_STATE_DIR, ensure_live_directories, fixture_status_series
from src.live_state.live_source_config import SOURCE_VERIFICATION_REPORT_DIR, ensure_source_verification_directories


def _group_code(value) -> str:
    text = str(value or "").strip()
    normalized = text.replace("_", " ")
    return normalized.split()[-1].upper() if normalized.lower().startswith("group ") else text


def build_standings_from_completed_matches(fixtures_df: pd.DataFrame) -> pd.DataFrame:
    rows: dict[tuple[str, str], dict] = {}
    if fixtures_df is None or fixtures_df.empty:
        return pd.DataFrame()
    stage = fixtures_df["stage"] if "stage" in fixtures_df else pd.Series("", index=fixtures_df.index)
    group_matches = fixtures_df[stage.astype(str).str.lower().str.contains("group", na=False)].copy()
    completed_statuses = {"completed", "finished", "ft", "match finished", "aet", "pen"}
    completed = group_matches[fixture_status_series(group_matches).isin(completed_statuses)]
    for _, match in completed.iterrows():
        group = _group_code(match.get("group") or match.get("stage"))
        team_a = match.get("team_a")
        team_b = match.get("team_b")
        if pd.isna(team_a) or pd.isna(team_b):
            continue
        for team in [team_a, team_b]:
            rows.setdefault(
                (group, team),
                {"group": group, "team": team, "played": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0, "goal_difference": 0, "points": 0},
            )
        ga = pd.to_numeric(match.get("team_a_goals"), errors="coerce")
        gb = pd.to_numeric(match.get("team_b_goals"), errors="coerce")
        if pd.isna(ga) or pd.isna(gb):
            continue
        ga = int(ga)
        gb = int(gb)
        a = rows[(group, team_a)]
        b = rows[(group, team_b)]
        a["played"] += 1
        b["played"] += 1
        a["goals_for"] += ga
        a["goals_against"] += gb
        b["goals_for"] += gb
        b["goals_against"] += ga
        if ga > gb:
            a["wins"] += 1
            b["losses"] += 1
            a["points"] += 3
        elif gb > ga:
            b["wins"] += 1
            a["losses"] += 1
            b["points"] += 3
        else:
            a["draws"] += 1
            b["draws"] += 1
            a["points"] += 1
            b["points"] += 1
    df = pd.DataFrame(rows.values())
    if df.empty:
        return df
    df["goal_difference"] = df["goals_for"] - df["goals_against"]
    return rank_group_standings(df)


def rank_group_standings(standings_df: pd.DataFrame) -> pd.DataFrame:
    if standings_df is None or standings_df.empty:
        return pd.DataFrame()
    data = standings_df.copy()
    data["group"] = data["group"].apply(_group_code)
    for column in ["points", "goal_difference", "goals_for"]:
        data[column] = pd.to_numeric(data.get(column), errors="coerce").fillna(0)
    ranked = []
    for group, group_df in data.groupby("group", sort=True):
        ordered = group_df.sort_values(["points", "goal_difference", "goals_for", "team"], ascending=[False, False, False, True]).copy()
        ordered["rank"] = range(1, len(ordered) + 1)
        ranked.append(ordered)
    return pd.concat(ranked, ignore_index=True) if ranked else data


def rank_third_place_table(standings_df: pd.DataFrame) -> pd.DataFrame:
    ranked = rank_group_standings(standings_df)
    if ranked.empty:
        return ranked
    thirds = ranked[ranked["rank"].eq(3)].copy()
    if thirds.empty:
        return thirds
    thirds = thirds.sort_values(["points", "goal_difference", "goals_for", "team"], ascending=[False, False, False, True]).reset_index(drop=True)
    thirds["third_place_rank"] = thirds.index + 1
    thirds["qualifies_as_best_third"] = thirds["third_place_rank"] <= 8
    return thirds


def determine_qualification_status(standings_df: pd.DataFrame, current_date=None) -> pd.DataFrame:
    if standings_df is None or standings_df.empty:
        return pd.DataFrame()
    data = rank_group_standings(standings_df)
    data["qualification_status"] = "still_possible"
    data.loc[data["rank"].le(2), "qualification_status"] = "qualified_position"
    data.loc[data["rank"].gt(3), "qualification_status"] = "unknown"
    return data


def build_and_save_standings(live_fixtures_df: pd.DataFrame, live_standings_df: pd.DataFrame | None = None) -> dict:
    ensure_live_directories()
    ensure_source_verification_directories()
    if live_standings_df is not None and not live_standings_df.empty:
        standings = live_standings_df.rename(columns={"rank": "rank"}).copy()
        provider = standings.get("provider", pd.Series("", index=standings.index)).astype(str).str.lower()
        source = "football_data_org_standings" if provider.eq("football_data_org").any() else "api_football_standings"
        if "source" not in standings:
            standings["source"] = source
    else:
        standings = build_standings_from_completed_matches(live_fixtures_df)
        source = "computed_from_completed_matches"
        if not standings.empty:
            standings["source"] = source
    standings = determine_qualification_status(standings)
    third = rank_third_place_table(standings)
    standings_path = LIVE_STATE_DIR / "current_group_standings.csv"
    third_path = LIVE_STATE_DIR / "current_third_place_table.csv"
    standings.to_csv(standings_path, index=False)
    third.to_csv(third_path, index=False)
    report = LIVE_REPORT_DIR / "standings_status_report.md"
    report.write_text(
        "\n".join(
            [
                "# Standings Status Report",
                "",
                f"- Source: {source}",
                f"- Group standing rows: {len(standings)}",
                f"- Third-place rows: {len(third)}",
                "- Qualification status is conservative during group play; teams may remain `still_possible` when math is not fully resolved.",
            ]
        ),
        encoding="utf-8",
    )
    verification_report = SOURCE_VERIFICATION_REPORT_DIR / "live_standings_report.md"
    completed_group = 0
    if live_fixtures_df is not None and not live_fixtures_df.empty:
        status = fixture_status_series(live_fixtures_df)
        stage = live_fixtures_df.get("stage", pd.Series(dtype=str)).astype(str).str.lower()
        completed_group = int((status.isin(["completed", "finished", "ft", "match finished", "aet", "pen"]) & stage.str.contains("group", na=False)).sum())
    lines = [
        "# Live Standings Report",
        "",
        f"- Source used: {source if not standings.empty else 'unavailable'}",
        f"- Standings rows: {len(standings)}",
        f"- Groups found: {standings['group'].nunique() if not standings.empty and 'group' in standings else 0}",
        f"- Teams found: {standings['team'].nunique() if not standings.empty and 'team' in standings else 0}",
        f"- Completed group matches used: {completed_group}",
        f"- Qualification status is known or approximate: {'yes' if not standings.empty else 'no'}",
    ]
    if standings.empty:
        lines.append("- Reason: API standings returned no rows and there are no completed group matches to compute standings from.")
    verification_report.write_text("\n".join(lines), encoding="utf-8")
    return {"standings": standings, "third_place": third, "report": str(report), "source": source}
