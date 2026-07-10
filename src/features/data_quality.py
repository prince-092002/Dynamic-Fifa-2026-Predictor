"""Feature-stage data quality cleanup without modifying processed source files."""

from __future__ import annotations

import pandas as pd

from src.config import PROCESSED_DIR
from src.features.feature_config import (
    FEATURE_REPORT_DIR,
    FIXTURES_FEATURE_CLEAN_PATH,
    MATCHES_FEATURE_CLEAN_PATH,
    ensure_feature_directories,
)


def _read_csv(path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def _team_pair_key(row: pd.Series) -> str:
    teams = sorted([str(row.get("team_a", "")).strip(), str(row.get("team_b", "")).strip()])
    return "|".join(teams)


def inspect_duplicate_matches() -> dict:
    """Detect duplicate match patterns and write duplicate reports."""
    ensure_feature_directories()
    matches = _read_csv(PROCESSED_DIR / "matches_master.csv")
    rows = []
    if matches.empty:
        report = FEATURE_REPORT_DIR / "duplicate_match_report.md"
        report.write_text("# Duplicate Match Report\n\nNo matches found.\n", encoding="utf-8")
        return {"duplicate_groups": 0, "report": str(report)}

    checks = {
        "exact_duplicate_rows": matches.duplicated(keep=False),
        "same_date_team_a_team_b": matches.duplicated(["date", "team_a", "team_b"], keep=False),
        "same_date_team_b_team_a": matches.assign(pair_key=matches.apply(_team_pair_key, axis=1)).duplicated(["date", "pair_key"], keep=False),
        "same_teams_same_score_same_date": matches.assign(pair_key=matches.apply(_team_pair_key, axis=1)).duplicated(
            ["date", "pair_key", "team_a_goals", "team_b_goals"], keep=False
        ),
    }
    for duplicate_type, mask in checks.items():
        dupes = matches[mask].copy()
        if dupes.empty:
            continue
        sample = dupes.head(25)
        for _, row in sample.iterrows():
            rows.append(
                {
                    "duplicate_type": duplicate_type,
                    "match_id": row.get("match_id"),
                    "date": row.get("date"),
                    "team_a": row.get("team_a"),
                    "team_b": row.get("team_b"),
                    "team_a_goals": row.get("team_a_goals"),
                    "team_b_goals": row.get("team_b_goals"),
                    "source": row.get("source"),
                }
            )
    csv_path = FEATURE_REPORT_DIR / "duplicate_match_report.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    md_path = FEATURE_REPORT_DIR / "duplicate_match_report.md"
    lines = [
        "# Duplicate Match Report",
        "",
        f"- Rows inspected: {len(matches)}",
        f"- Duplicate sample rows written: {len(rows)}",
        f"- Duplicate groups detected: {pd.DataFrame(rows)['duplicate_type'].nunique() if rows else 0}",
        "",
        "## Recommended Action",
        "",
        "Use `matches_master_feature_clean.csv` for feature engineering. Keep `matches_master.csv` unchanged as the raw processed source.",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"duplicate_groups": len(rows), "report": str(md_path), "csv": str(csv_path)}


def _completeness_score(df: pd.DataFrame) -> pd.Series:
    preferred = ["tournament", "stage", "city", "country", "neutral", "source", "venue"]
    existing = [column for column in preferred if column in df.columns]
    return df[existing].notna().sum(axis=1) if existing else pd.Series(0, index=df.index)


def deduplicate_matches_for_features() -> dict:
    """Create a feature-safe match file, preserving source data and reporting removals."""
    ensure_feature_directories()
    matches = _read_csv(PROCESSED_DIR / "matches_master.csv")
    if matches.empty:
        matches.to_csv(MATCHES_FEATURE_CLEAN_PATH, index=False)
        return {"rows": 0, "removed": 0, "conflicts": 0, "output": str(MATCHES_FEATURE_CLEAN_PATH)}

    exact_removed = matches[matches.duplicated(keep="first")].copy()
    cleaned = matches.drop_duplicates(keep="first").copy()
    cleaned["_pair_key"] = cleaned.apply(_team_pair_key, axis=1)
    cleaned["_complete"] = _completeness_score(cleaned)
    removed_parts = [exact_removed]
    conflict_rows = []
    kept_rows = []
    group_cols = ["date", "_pair_key"]
    for _, group in cleaned.groupby(group_cols, dropna=False, sort=False):
        if len(group) == 1:
            kept_rows.append(group.iloc[0])
            continue
        score_pairs = group[["team_a_goals", "team_b_goals"]].drop_duplicates()
        if len(score_pairs) > 1:
            conflict_rows.append(group.drop(columns=["_pair_key", "_complete"], errors="ignore"))
        group_sorted = group.sort_values("_complete", ascending=False)
        kept_rows.append(group_sorted.iloc[0])
        removed_parts.append(group_sorted.iloc[1:].drop(columns=["_pair_key", "_complete"], errors="ignore"))
    feature_clean = pd.DataFrame(kept_rows).drop(columns=["_pair_key", "_complete"], errors="ignore")
    removed = pd.concat([part for part in removed_parts if not part.empty], ignore_index=True) if removed_parts else pd.DataFrame()
    conflicts = pd.concat(conflict_rows, ignore_index=True) if conflict_rows else pd.DataFrame()
    feature_clean.to_csv(MATCHES_FEATURE_CLEAN_PATH, index=False)
    removed.to_csv(FEATURE_REPORT_DIR / "removed_duplicate_matches.csv", index=False)
    conflicts.to_csv(FEATURE_REPORT_DIR / "conflicting_duplicate_matches.csv", index=False)
    return {
        "rows": len(feature_clean),
        "removed": len(removed),
        "conflicts": len(conflicts),
        "output": str(MATCHES_FEATURE_CLEAN_PATH),
    }


def handle_tbd_fixtures() -> dict:
    """Keep TBD fixtures while adding explicit placeholder and flag columns."""
    ensure_feature_directories()
    fixtures = _read_csv(PROCESSED_DIR / "fixtures_2026.csv")
    if fixtures.empty:
        fixtures.to_csv(FIXTURES_FEATURE_CLEAN_PATH, index=False)
        return {"rows": 0, "tbd_rows": 0, "output": str(FIXTURES_FEATURE_CLEAN_PATH)}
    fixtures = fixtures.copy()
    fixtures["team_a_is_tbd"] = fixtures["team_a"].isna() | fixtures["team_a"].astype(str).str.strip().eq("")
    fixtures["team_b_is_tbd"] = fixtures["team_b"].isna() | fixtures["team_b"].astype(str).str.strip().eq("")
    fixtures.loc[fixtures["team_a_is_tbd"], "team_a"] = "TBD_Team_A"
    fixtures.loc[fixtures["team_b_is_tbd"], "team_b"] = "TBD_Team_B"
    fixtures["fixture_has_tbd_team"] = fixtures["team_a_is_tbd"] | fixtures["team_b_is_tbd"]
    fixtures.to_csv(FIXTURES_FEATURE_CLEAN_PATH, index=False)
    report_df = fixtures[["match_id", "date", "stage", "group", "team_a", "team_b", "team_a_is_tbd", "team_b_is_tbd", "fixture_has_tbd_team"]].copy()
    report_df.to_csv(FEATURE_REPORT_DIR / "tbd_fixture_report.csv", index=False)
    md_path = FEATURE_REPORT_DIR / "tbd_fixture_report.md"
    lines = [
        "# TBD Fixture Report",
        "",
        f"- Fixture rows: {len(fixtures)}",
        f"- Rows with any TBD team: {int(fixtures['fixture_has_tbd_team'].sum())}",
        f"- Missing team_a replaced: {int(fixtures['team_a_is_tbd'].sum())}",
        f"- Missing team_b replaced: {int(fixtures['team_b_is_tbd'].sum())}",
        "",
        "TBD fixtures are preserved for later simulation and marked not predictable until both teams are known.",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"rows": len(fixtures), "tbd_rows": int(fixtures["fixture_has_tbd_team"].sum()), "output": str(FIXTURES_FEATURE_CLEAN_PATH)}


def run_feature_data_quality_checks() -> dict:
    """Run feature-stage duplicate and TBD cleanup."""
    ensure_feature_directories()
    duplicate_info = inspect_duplicate_matches()
    dedupe_info = deduplicate_matches_for_features()
    tbd_info = handle_tbd_fixtures()
    summary_path = FEATURE_REPORT_DIR / "feature_data_quality_summary.md"
    lines = [
        "# Feature Data Quality Summary",
        "",
        f"- Duplicate sample rows detected: {duplicate_info['duplicate_groups']}",
        f"- Feature-clean match rows: {dedupe_info['rows']}",
        f"- Duplicate rows removed for features: {dedupe_info['removed']}",
        f"- Conflicting duplicate rows reported: {dedupe_info['conflicts']}",
        f"- Feature-clean fixture rows: {tbd_info['rows']}",
        f"- Fixture rows with TBD teams: {tbd_info['tbd_rows']}",
    ]
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return {"duplicate": duplicate_info, "dedupe": dedupe_info, "tbd": tbd_info, "summary": str(summary_path)}
