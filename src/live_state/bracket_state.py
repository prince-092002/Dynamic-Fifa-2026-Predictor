"""Current knockout bracket state and live/fallback source reporting."""

from __future__ import annotations

import pandas as pd

from src.live_state.live_config import LIVE_REPORT_DIR, LIVE_STATE_DIR, coerce_bool_series, ensure_live_directories, normalize_stage_name
from src.live_state.live_source_config import SOURCE_VERIFICATION_REPORT_DIR, ensure_source_verification_directories
from src.simulation.bracket_mapping import create_default_bracket_files, load_bracket_slots
from src.simulation.tournament_structure import is_tbd_team


KNOCKOUT_STAGES = {"Round of 32", "Round of 16", "Quarterfinal", "Semifinal", "Final"}
PREVIOUS_STAGE = {
    "Round of 16": "Round of 32",
    "Quarterfinal": "Round of 16",
    "Semifinal": "Quarterfinal",
    "Final": "Semifinal",
}


def build_current_knockout_bracket(live_fixtures_df: pd.DataFrame) -> pd.DataFrame:
    output = build_live_bracket_from_fixtures(live_fixtures_df)
    output.to_csv(LIVE_STATE_DIR / "current_knockout_bracket.csv", index=False)
    return output


def build_live_bracket_from_fixtures(live_fixtures_df: pd.DataFrame) -> pd.DataFrame:
    ensure_live_directories()
    ensure_source_verification_directories()
    if live_fixtures_df is None or live_fixtures_df.empty:
        bracket = pd.DataFrame()
    else:
        data = live_fixtures_df.copy()
        stage = data["stage"] if "stage" in data else pd.Series("", index=data.index)
        data["stage"] = stage.apply(normalize_stage_name)
        bracket = data[data["stage"].isin(KNOCKOUT_STAGES)].copy()
        bracket = _fill_missing_teams_from_completed_previous_rounds(bracket)
    rows = []
    for _, row in bracket.iterrows():
        source = str(row.get("source", "")).lower()
        if source == "api_football":
            bracket_source = "live_api"
        elif source == "official_fifa":
            bracket_source = "official_fifa"
        elif source == "football_data_org":
            bracket_source = "football_data_org_live"
        else:
            bracket_source = "fallback_template"
        rows.append(
            {
                "match_id": row.get("match_id"),
                "fixture_id": row.get("fixture_id", row.get("match_id")),
                "stage": row.get("stage"),
                "round": row.get("round", row.get("stage")),
                "team_a": row.get("team_a"),
                "team_b": row.get("team_b"),
                "team_a_goals": row.get("team_a_goals"),
                "team_b_goals": row.get("team_b_goals"),
                "winner": row.get("winner", ""),
                "status": row.get("status"),
                "is_completed": _bool_value(row.get("is_completed", False)),
                "is_live": _bool_value(row.get("is_live", False)),
                "is_scheduled": _bool_value(row.get("is_scheduled", False)),
                "is_tbd": is_tbd_team(row.get("team_a")) or is_tbd_team(row.get("team_b")),
                "bracket_source": bracket_source,
                "last_updated": row.get("last_updated"),
            }
        )
    output = pd.DataFrame(rows)
    output.to_csv(LIVE_STATE_DIR / "live_knockout_bracket_from_api.csv", index=False)
    _write_live_bracket_status_report(output)
    return output


def _fill_missing_teams_from_completed_previous_rounds(bracket: pd.DataFrame) -> pd.DataFrame:
    if bracket.empty:
        return bracket
    data = bracket.copy()
    for stage, previous_stage in PREVIOUS_STAGE.items():
        stage_mask = data["stage"].eq(stage)
        if not stage_mask.any():
            continue
        previous = data[data["stage"].eq(previous_stage)].copy()
        if previous.empty or "winner" not in previous:
            continue
        winners = [team for team in previous["winner"].dropna().astype(str).tolist() if not is_tbd_team(team)]
        known = set()
        for column in ["team_a", "team_b"]:
            known.update(team for team in data.loc[stage_mask, column].dropna().astype(str).tolist() if not is_tbd_team(team))
        remaining = [team for team in winners if team not in known]
        if not remaining:
            continue
        for idx in data[stage_mask].index:
            for column in ["team_a", "team_b"]:
                if not remaining:
                    break
                if is_tbd_team(data.at[idx, column]):
                    data.at[idx, column] = remaining.pop(0)
    return data


def lock_completed_knockout_results(bracket_df: pd.DataFrame) -> pd.DataFrame:
    data = bracket_df.copy()
    if data.empty:
        return data
    data["locked_result"] = coerce_bool_series(data.get("is_completed", pd.Series(False, index=data.index)))
    return data


def identify_remaining_knockout_matches(bracket_df: pd.DataFrame) -> pd.DataFrame:
    if bracket_df is None or bracket_df.empty:
        return pd.DataFrame()
    completed = coerce_bool_series(bracket_df.get("is_completed", pd.Series(False, index=bracket_df.index)))
    return bracket_df[~completed].copy()


def _fallback_rows() -> pd.DataFrame:
    create_default_bracket_files(False)
    slots = load_bracket_slots()
    rows = []
    for match_slot, slot_df in slots.groupby("match_slot", sort=False):
        rows.append(
            {
                "match_id": match_slot,
                "fixture_id": "",
                "stage": "Round of 32",
                "round": "Round of 32",
                "team_a": slot_df[slot_df["team_slot"].eq("team_a")].iloc[0].get("third_place_mapping_key") or slot_df[slot_df["team_slot"].eq("team_a")].iloc[0].get("group"),
                "team_b": slot_df[slot_df["team_slot"].eq("team_b")].iloc[0].get("third_place_mapping_key") or slot_df[slot_df["team_slot"].eq("team_b")].iloc[0].get("group"),
                "team_a_goals": pd.NA,
                "team_b_goals": pd.NA,
                "winner": "",
                "status": "scheduled",
                "is_completed": False,
                "is_live": False,
                "is_scheduled": True,
                "next_match_id": "",
                "source": "fallback_template",
                "last_updated": "",
                "bracket_source": "fallback_template",
            }
        )
    return pd.DataFrame(rows)


def merge_live_bracket_with_fallback_template(live_bracket_df: pd.DataFrame, fallback_bracket_df: pd.DataFrame | None = None) -> pd.DataFrame:
    ensure_live_directories()
    live = live_bracket_df.copy() if live_bracket_df is not None else pd.DataFrame()
    if not live.empty:
        live["contains_tbd"] = live.apply(lambda row: is_tbd_team(row.get("team_a")) or is_tbd_team(row.get("team_b")), axis=1)
        live_source = live.get("source", pd.Series("", index=live.index)).astype(str).str.lower()
        bracket_source = live.get("bracket_source", pd.Series("", index=live.index)).astype(str).str.lower()
        trustworthy = (live_source.isin(["api_football", "official_fifa", "football_data_org"]) | bracket_source.isin(["live_api", "official_fifa", "football_data_org_live"])) & ~live["contains_tbd"]
        if trustworthy.any():
            merged = live.copy()
            merged["bracket_source"] = "fallback_template"
            if "source" in merged:
                merged.loc[trustworthy, "bracket_source"] = merged.loc[trustworthy, "source"].replace({"api_football": "live_api", "official_fifa": "official_fifa", "football_data_org": "football_data_org_live"})
            else:
                merged.loc[trustworthy, "bracket_source"] = bracket_source[trustworthy].replace({"api_football": "live_api"})
        else:
            merged = fallback_bracket_df.copy() if fallback_bracket_df is not None and not fallback_bracket_df.empty else _fallback_rows()
    else:
        merged = fallback_bracket_df.copy() if fallback_bracket_df is not None and not fallback_bracket_df.empty else _fallback_rows()
    if not merged.empty:
        merged["contains_tbd"] = merged.apply(lambda row: is_tbd_team(row.get("team_a")) or is_tbd_team(row.get("team_b")), axis=1)
    merged.to_csv(LIVE_STATE_DIR / "merged_bracket_state.csv", index=False)
    source_counts = merged.get("bracket_source", pd.Series(dtype=str)).value_counts(normalize=True).to_dict() if not merged.empty else {}
    report = LIVE_REPORT_DIR / "live_bracket_source_report.md"
    lines = ["# Live Bracket Source Report", "", f"- Rows: {len(merged)}", "", "| Source | Share |", "|---|---:|"]
    for source, share in source_counts.items():
        lines.append(f"| {source} | {share:.2%} |")
    if not source_counts:
        lines.append("| unavailable | 0.00% |")
    lines.extend(["", "Fallback rows are not official FIFA bracket mapping."])
    report.write_text("\n".join(lines), encoding="utf-8")
    return merged


def _write_live_bracket_status_report(bracket: pd.DataFrame) -> str:
    path = SOURCE_VERIFICATION_REPORT_DIR / "live_bracket_status_report.md"
    if bracket.empty:
        live_api_pct = 0.0
        fallback_pct = 1.0
    else:
        sources = bracket.get("bracket_source", pd.Series(dtype=str)).astype(str)
        live_api_pct = float(sources.eq("live_api").mean())
        fallback_pct = float(sources.eq("fallback_template").mean())
    lines = [
        "# Live Bracket Status Report",
        "",
        f"- Knockout fixture rows: {len(bracket)}",
        f"- Completed knockout matches: {int(coerce_bool_series(bracket.get('is_completed', pd.Series(dtype=bool))).sum()) if not bracket.empty else 0}",
        f"- Scheduled knockout matches: {int(coerce_bool_series(bracket.get('is_scheduled', pd.Series(dtype=bool))).sum()) if not bracket.empty else 0}",
        f"- TBD knockout matches: {int(coerce_bool_series(bracket.get('is_tbd', pd.Series(dtype=bool))).sum()) if not bracket.empty else 0}",
        f"- Percentage live_api: {live_api_pct:.2%}",
        f"- Percentage fallback_template: {fallback_pct:.2%}",
        f"- Official/current bracket sufficiently known: {'yes' if live_api_pct >= 0.5 else 'no'}",
        "",
        "Fallback rows are not official FIFA bracket mapping.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)


def _bool_value(value) -> bool:
    return bool(coerce_bool_series(pd.Series([value])).iloc[0])
