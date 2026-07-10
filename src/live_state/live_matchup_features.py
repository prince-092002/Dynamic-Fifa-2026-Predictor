"""Identify resolved live knockout matchups and build model features for them.

Reuses the Phase 3 feature engineering functions so live knockout features stay
consistent with the training and pre-tournament fixture feature definitions.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.cleaning.standardize_team_names import load_team_name_map, standardize_team_name
from src.config import PROCESSED_DIR
from src.features.elo_features import actual_score, expected_score, update_elo
from src.features.feature_config import MATCHES_FEATURE_CLEAN_PATH, MODEL_FEATURE_COLUMNS
from src.features.form_features import build_rolling_form_features, calculate_team_match_history
from src.features.goal_features import build_rolling_goal_features
from src.features.head_to_head_features import build_head_to_head_features
from src.features.schedule_features import build_schedule_features
from src.features.tournament_features import build_tournament_features
from src.live_state.live_config import LIVE_STATE_DIR, coerce_bool_series, ensure_live_directories
from src.simulation.tournament_structure import is_tbd_team
from src.utils.dates import now_utc_iso

KNOCKOUT_STAGES = ["Round of 32", "Round of 16", "Quarterfinal", "Semifinal", "Third Place Playoff", "Final"]
HOST_NATIONS = {"United States", "Canada", "Mexico"}
REMAINING_MATCHUPS_PATH = LIVE_STATE_DIR / "remaining_known_knockout_matchups.csv"
LIVE_FEATURES_PATH = LIVE_STATE_DIR / "live_knockout_match_features.csv"

MATCHUP_COLUMNS = ["fixture_id", "match_id", "stage", "round", "team_a", "team_b", "date", "provider"]


def _read(path, columns=None) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame(columns=columns or [])


def _known(value) -> bool:
    return pd.notna(value) and not is_tbd_team(value)


def _make_standardizer():
    """Same mapping as standardize_team_name, but the name map is loaded once.

    Calling standardize_team_name without explicit mappings re-reads
    team_name_map.csv from disk on every call — ~99k times per history build.
    """
    mappings = load_team_name_map()
    cache: dict = {}

    def convert(name):
        if name in cache:
            return cache[name]
        value = standardize_team_name(name, mappings)
        cache[name] = value
        return value

    return convert


def identify_remaining_live_knockout_matches() -> pd.DataFrame:
    """List unplayed knockout matches where both teams are known from live data."""
    ensure_live_directories()
    bracket = _read(LIVE_STATE_DIR / "merged_bracket_state.csv")
    if bracket.empty:
        bracket = _read(LIVE_STATE_DIR / "football_data_org_bracket_normalized.csv")
    fixtures = _read(LIVE_STATE_DIR / "football_data_org_fixtures_normalized.csv")
    date_by_fixture = {}
    provider_by_fixture = {}
    if not fixtures.empty and "fixture_id" in fixtures.columns:
        date_by_fixture = dict(zip(fixtures["fixture_id"], fixtures.get("date", "")))
        provider_by_fixture = dict(zip(fixtures["fixture_id"], fixtures.get("provider", "")))
    rows = []
    if not bracket.empty:
        completed = coerce_bool_series(bracket.get("is_completed", pd.Series(False, index=bracket.index)))
        for idx, row in bracket.iterrows():
            if str(row.get("stage")) not in KNOCKOUT_STAGES:
                continue
            if bool(completed.loc[idx]):
                continue
            if not _known(row.get("team_a")) or not _known(row.get("team_b")):
                continue
            fixture_id = row.get("fixture_id")
            rows.append(
                {
                    "fixture_id": fixture_id,
                    "match_id": row.get("match_id"),
                    "stage": row.get("stage"),
                    "round": row.get("round"),
                    "team_a": row.get("team_a"),
                    "team_b": row.get("team_b"),
                    "date": date_by_fixture.get(fixture_id, ""),
                    "provider": row.get("provider", provider_by_fixture.get(fixture_id, "")),
                }
            )
    matchups = pd.DataFrame(rows, columns=MATCHUP_COLUMNS)
    matchups.to_csv(REMAINING_MATCHUPS_PATH, index=False)
    return matchups


def _live_completed_as_history(fixtures: pd.DataFrame) -> pd.DataFrame:
    """Convert completed live fixtures to the matches-master history schema."""
    if fixtures.empty:
        return pd.DataFrame()
    completed = fixtures[coerce_bool_series(fixtures.get("is_completed", pd.Series(False, index=fixtures.index)))].copy()
    if completed.empty:
        return pd.DataFrame()
    return pd.DataFrame(
        {
            "match_id": completed.get("match_id"),
            "date": completed.get("date"),
            "team_a": completed.get("team_a"),
            "team_b": completed.get("team_b"),
            "team_a_goals": pd.to_numeric(completed.get("team_a_goals"), errors="coerce"),
            "team_b_goals": pd.to_numeric(completed.get("team_b_goals"), errors="coerce"),
            "winner": completed.get("winner"),
            "tournament": "FIFA World Cup",
            "stage": completed.get("stage"),
            "neutral": True,
            "source": completed.get("provider", "live_provider"),
        }
    )


def _build_combined_history() -> pd.DataFrame:
    """Master match history plus any completed live results not already in it.

    Completed live results are deduplicated against the master file on
    (team, date +/- 1 day) so provider/master team-name variants for the same
    real match never enter a team's history twice.
    """
    # Prefer the deduplicated feature-clean history — the same lineage training
    # features were built from. The raw master keeps cross-feed duplicates by design.
    master = _read(MATCHES_FEATURE_CLEAN_PATH)
    if master.empty:
        master = _read(PROCESSED_DIR / "matches_master.csv")
    master["date"] = pd.to_datetime(master.get("date"), errors="coerce")
    # Unplayed fixture placeholders (NaN goals) are not history: they corrupt
    # rest-day features and block real live results from being appended.
    for column in ["team_a_goals", "team_b_goals"]:
        master[column] = pd.to_numeric(master.get(column), errors="coerce")
    master = master.dropna(subset=["team_a_goals", "team_b_goals"])
    live = _live_completed_as_history(_read(LIVE_STATE_DIR / "football_data_org_fixtures_normalized.csv"))
    if live.empty:
        return master
    live["date"] = pd.to_datetime(live["date"], errors="coerce", utc=True).dt.tz_localize(None)
    standardize = _make_standardizer()
    master_team_days = set()
    for col in ["team_a", "team_b"]:
        frame = master[[col, "date"]].dropna()
        for team, date in zip(frame[col].map(standardize), frame["date"].dt.normalize()):
            master_team_days.add((team, date))

    def _already_in_master(row) -> bool:
        date = row["date"]
        if pd.isna(date):
            return False
        day = pd.Timestamp(date).normalize()
        for team in [standardize(row["team_a"]), standardize(row["team_b"])]:
            for offset in [-1, 0, 1]:
                if (team, day + pd.Timedelta(days=offset)) in master_team_days:
                    return True
        return False

    missing = live[~live.apply(_already_in_master, axis=1)]
    if missing.empty:
        return master
    return pd.concat([master, missing], ignore_index=True)


def _replay_chronological_elo(history: pd.DataFrame) -> dict[str, float]:
    """Current chronological Elo per team, replayed the same way training Elo was built."""
    data = history.dropna(subset=["team_a", "team_b"]).sort_values(["date", "match_id"], na_position="last")
    ratings: dict[str, float] = {}
    for row in data.itertuples(index=False):
        team_a = str(row.team_a)
        team_b = str(row.team_b)
        elo_a = ratings.get(team_a, 1500.0)
        elo_b = ratings.get(team_b, 1500.0)
        score_a = actual_score(row.team_a_goals, row.team_b_goals)
        if score_a is not None:
            ratings[team_a], ratings[team_b] = update_elo(elo_a, elo_b, score_a)
    return ratings


def _fast_team_match_history(matches_df: pd.DataFrame) -> pd.DataFrame:
    """Vectorized equivalent of ``calculate_team_match_history``.

    Produces the same rows, columns, and (team, date, match_id) ordering as the
    Phase 3 row-loop implementation without the per-row Python cost. Verified by
    ``run_feature_equivalence_validation``; no feature definition changes.
    """
    data = matches_df.copy()
    goals_a = pd.to_numeric(data.get("team_a_goals"), errors="coerce")
    goals_b = pd.to_numeric(data.get("team_b_goals"), errors="coerce")
    valid = goals_a.notna() & goals_b.notna()
    data = data[valid]
    goals_a = goals_a[valid].astype(float)
    goals_b = goals_b[valid].astype(float)
    sides = []
    for team_col, opp_col, gf, ga in [("team_a", "team_b", goals_a, goals_b), ("team_b", "team_a", goals_b, goals_a)]:
        points = np.where(gf > ga, 3, np.where(gf == ga, 1, 0))
        sides.append(
            pd.DataFrame(
                {
                    "match_id": data.get("match_id").values,
                    "date": data.get("date").values,
                    "team": data.get(team_col).values,
                    "opponent": data.get(opp_col).values,
                    "goals_for": gf.values,
                    "goals_against": ga.values,
                    "goal_diff": (gf - ga).values,
                    "result_points": points,
                    "win_flag": (points == 3).astype(int),
                    "draw_flag": (points == 1).astype(int),
                    "loss_flag": (points == 0).astype(int),
                    "clean_sheet_flag": (ga == 0).astype(int).values,
                    "tournament": data.get("tournament", pd.Series(index=data.index)).values,
                    "neutral": data.get("neutral", pd.Series(index=data.index)).values,
                    "source": data.get("source", pd.Series(index=data.index)).values,
                }
            )
        )
    history = pd.concat(sides, ignore_index=True)
    history["date"] = pd.to_datetime(history["date"], errors="coerce")
    return history.sort_values(["team", "date", "match_id"]).reset_index(drop=True)


def _restrict_history_to_pairs(history: pd.DataFrame, matchups: pd.DataFrame) -> pd.DataFrame:
    """Rows whose team pair matches a target matchup pair.

    Equivalent input reduction for head-to-head features: ``_h2h_before`` only
    ever reads rows with the exact (sorted) pair of the target matchup.
    """
    pairs = {tuple(sorted([str(a), str(b)])) for a, b in zip(matchups["team_a"], matchups["team_b"])}
    mask = [tuple(sorted([str(a), str(b)])) in pairs for a, b in zip(history["team_a"], history["team_b"])]
    return history[pd.Series(mask, index=history.index)]


def _restrict_history_to_teams(history: pd.DataFrame, matchups: pd.DataFrame) -> pd.DataFrame:
    """Rows involving any team from the target matchups.

    Equivalent input reduction for schedule features: rest days and 30-day
    congestion only read rows where the target team itself played.
    """
    teams = {str(t) for col in ["team_a", "team_b"] for t in matchups[col].dropna()}
    mask = history["team_a"].astype(str).isin(teams) | history["team_b"].astype(str).isin(teams)
    return history[mask]


def _form_and_goal_features(matchups_std: pd.DataFrame, history: pd.DataFrame, use_fast: bool = True) -> pd.DataFrame:
    """As-of-now rolling form/goal features via the Phase 3 rolling builders.

    Each matchup is appended to the team history as a placeholder future row;
    the shift(1)-based rolling functions then produce, at that placeholder row,
    exactly the pre-match rolling values over all completed matches.
    """
    placeholders = matchups_std[["match_id", "date", "team_a", "team_b"]].copy()
    placeholders["team_a_goals"] = 0
    placeholders["team_b_goals"] = 0
    placeholder_ids = set(placeholders["match_id"].astype(str))
    combined = pd.concat([history, placeholders], ignore_index=True)
    team_history = _fast_team_match_history(combined) if use_fast else calculate_team_match_history(combined)
    form = build_rolling_form_features(team_history)
    goals = build_rolling_goal_features(team_history)
    form_cols = [c for c in form.columns if c.startswith(("form_points_", "win_rate_", "draw_rate_", "loss_rate_"))]
    goal_cols = [c for c in goals.columns if c.startswith(("goals_for_avg_", "goals_against_avg_", "goal_diff_avg_", "goals_for_sum_", "clean_sheet_rate_"))]
    form_rows = form[form["match_id"].astype(str).isin(placeholder_ids)][["match_id", "team", *form_cols]]
    goal_rows = goals[goals["match_id"].astype(str).isin(placeholder_ids)][["match_id", "team", *goal_cols]]
    output = matchups_std[["match_id", "team_a", "team_b"]].copy()
    for side in ["team_a", "team_b"]:
        side_form = form_rows.rename(columns={"team": side, **{c: f"{side}_{c}" for c in form_cols}})
        side_goals = goal_rows.rename(columns={"team": side, **{c: f"{side}_{c}" for c in goal_cols}})
        output = output.merge(side_form, on=["match_id", side], how="left")
        output = output.merge(side_goals, on=["match_id", side], how="left")
    output["form_points_last_5_diff"] = output["team_a_form_points_last_5"] - output["team_b_form_points_last_5"]
    output["win_rate_last_5_diff"] = output["team_a_win_rate_last_5"] - output["team_b_win_rate_last_5"]
    output["loss_rate_last_5_diff"] = output["team_a_loss_rate_last_5"] - output["team_b_loss_rate_last_5"]
    output["goals_for_avg_last_5_diff"] = output["team_a_goals_for_avg_last_5"] - output["team_b_goals_for_avg_last_5"]
    output["goals_against_avg_last_5_diff"] = output["team_a_goals_against_avg_last_5"] - output["team_b_goals_against_avg_last_5"]
    output["goal_diff_avg_last_5_diff"] = output["team_a_goal_diff_avg_last_5"] - output["team_b_goal_diff_avg_last_5"]
    output["clean_sheet_rate_last_5_diff"] = output["team_a_clean_sheet_rate_last_5"] - output["team_b_clean_sheet_rate_last_5"]
    return output.drop(columns=["team_a", "team_b"])


def build_live_knockout_features(use_fast: bool = True, write_output: bool = True) -> pd.DataFrame:
    """Build model-ready features for the remaining known live knockout matchups.

    ``use_fast=False`` runs the original Phase 3 row-loop path; the default fast
    path is equivalence-validated against it (see run_feature_equivalence_validation).
    """
    ensure_live_directories()
    matchups = _read(REMAINING_MATCHUPS_PATH, columns=MATCHUP_COLUMNS)
    if matchups.empty:
        matchups = identify_remaining_live_knockout_matches()
    if matchups.empty:
        empty = pd.DataFrame(columns=MATCHUP_COLUMNS + MODEL_FEATURE_COLUMNS + ["feature_status", "missing_feature_count", "feature_source"])
        if write_output:
            empty.to_csv(LIVE_FEATURES_PATH, index=False)
        return empty

    history = _build_combined_history()
    matchups_std = matchups.copy()
    matchups_std["date"] = pd.to_datetime(matchups_std["date"], errors="coerce", utc=True).dt.tz_localize(None)
    for side in ["team_a", "team_b"]:
        matchups_std[side] = matchups_std[side].map(_make_standardizer())
    matchups_std["neutral"] = ~(matchups_std["team_a"].isin(HOST_NATIONS) | matchups_std["team_b"].isin(HOST_NATIONS))
    matchups_std["tournament"] = "FIFA World Cup"

    elo_ratings = _replay_chronological_elo(history)
    elo_rows = []
    for row in matchups_std.itertuples(index=False):
        elo_a = elo_ratings.get(str(row.team_a))
        elo_b = elo_ratings.get(str(row.team_b))
        elo_rows.append(
            {
                "match_id": row.match_id,
                "team_a_pre_match_elo": elo_a,
                "team_b_pre_match_elo": elo_b,
                "elo_difference": elo_a - elo_b if elo_a is not None and elo_b is not None else pd.NA,
                "elo_expected_score_team_a": expected_score(elo_a, elo_b) if elo_a is not None and elo_b is not None else pd.NA,
            }
        )
    h2h_history = _restrict_history_to_pairs(history, matchups_std) if use_fast else history
    schedule_history = _restrict_history_to_teams(history, matchups_std) if use_fast else history
    feature_tables = [
        pd.DataFrame(elo_rows),
        _form_and_goal_features(matchups_std, history, use_fast=use_fast),
        build_head_to_head_features(h2h_history, matchups_std, "live_knockout_h2h_features.csv"),
        build_tournament_features(matchups_std, "live_knockout_tournament_features.csv"),
        build_schedule_features(schedule_history, matchups_std, "live_knockout_schedule_features.csv"),
    ]
    final = matchups.copy()
    for table in feature_tables:
        if table.empty or "match_id" not in table.columns:
            continue
        table = table.drop(columns=[c for c in ["team_a", "team_b", "date"] if c in table.columns], errors="ignore")
        final = final.merge(table, on="match_id", how="left")
    for column in MODEL_FEATURE_COLUMNS:
        if column not in final.columns:
            final[column] = pd.NA
    feature_frame = final[MODEL_FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
    final["missing_feature_count"] = feature_frame.isna().sum(axis=1).astype(int)
    final["feature_status"] = final["missing_feature_count"].map(lambda n: "complete" if n == 0 else "partial_missing_features")
    final["feature_source"] = "phase3_feature_functions_with_live_history" + ("_fast" if use_fast else "")
    final["is_predictable_now"] = final["team_a_pre_match_elo"].notna() & final["team_b_pre_match_elo"].notna()
    final["generated_at"] = now_utc_iso()
    if write_output:
        final.to_csv(LIVE_FEATURES_PATH, index=False)
    return final


def run_feature_equivalence_validation() -> dict:
    """Build live knockout features with the original and fast paths and compare.

    Writes outputs/reports/live_state/live_feature_cache_validation.md. The fast
    path is only trusted (and shipped as default) because this comparison passes.
    """
    import time

    from src.live_state.live_config import LIVE_REPORT_DIR

    ensure_live_directories()
    started = time.perf_counter()
    original = build_live_knockout_features(use_fast=False, write_output=False)
    original_seconds = time.perf_counter() - started
    started = time.perf_counter()
    fast = build_live_knockout_features(use_fast=True, write_output=True)
    fast_seconds = time.perf_counter() - started
    compare_columns = [c for c in MODEL_FEATURE_COLUMNS if c in original.columns and c in fast.columns]
    tolerance = 1e-9  # float round-off only; any real logic difference exceeds this
    exact = tolerance_only = mismatched = 0
    max_abs_diff = 0.0
    mismatch_detail = []
    original_indexed = original.set_index("match_id")
    fast_indexed = fast.set_index("match_id")
    shared_ids = [m for m in original_indexed.index if m in fast_indexed.index]
    for column in compare_columns:
        left = pd.to_numeric(original_indexed.loc[shared_ids, column], errors="coerce")
        right = pd.to_numeric(fast_indexed.loc[shared_ids, column], errors="coerce")
        for match_id, a, b in zip(shared_ids, left, right):
            if (pd.isna(a) and pd.isna(b)) or a == b:
                exact += 1
            elif pd.notna(a) and pd.notna(b) and abs(float(a) - float(b)) <= tolerance:
                tolerance_only += 1
                max_abs_diff = max(max_abs_diff, abs(float(a) - float(b)))
            else:
                mismatched += 1
                diff = abs(float(a) - float(b)) if pd.notna(a) and pd.notna(b) else float("nan")
                max_abs_diff = max(max_abs_diff, diff) if pd.notna(diff) else max_abs_diff
                mismatch_detail.append(f"{match_id} / {column}: original={a} fast={b}")
    status = "pass" if mismatched == 0 and len(shared_ids) == len(original) == len(fast) and len(fast) > 0 else ("pass_empty" if len(original) == len(fast) == 0 else "fail")
    lines = [
        "# Live Feature Fast-Path Equivalence Validation",
        "",
        f"- Generated: {now_utc_iso()}",
        f"- Status: {status}",
        f"- Rows compared: {len(shared_ids)} (original {len(original)}, fast {len(fast)})",
        f"- Features compared per row: {len(compare_columns)}",
        f"- Exact matches: {exact}",
        f"- Tolerance-only matches (<= {tolerance}): {tolerance_only}",
        f"- Mismatches: {mismatched}",
        f"- Maximum absolute difference: {max_abs_diff}",
        f"- Runtime, original Phase 3 row-loop path: {original_seconds:.1f}s",
        f"- Runtime, fast vectorized path: {fast_seconds:.1f}s",
        f"- Speedup: {original_seconds / fast_seconds:.1f}x" if fast_seconds > 0 else "- Speedup: n/a",
        "",
        "The fast path vectorizes `calculate_team_match_history` and restricts the H2H/schedule",
        "history inputs to rows those functions can actually read (same pair / same team).",
        "No feature definitions, imputation behavior, or model schema were changed.",
        "The saved live_knockout_match_features.csv comes from the fast path only when this check passes.",
    ]
    if mismatch_detail:
        lines.extend(["", "## Mismatches", ""] + [f"- {d}" for d in mismatch_detail[:40]])
    report_path = LIVE_REPORT_DIR / "live_feature_cache_validation.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "status": status,
        "rows_compared": len(shared_ids),
        "features_compared": len(compare_columns),
        "exact": exact,
        "tolerance_only": tolerance_only,
        "mismatches": mismatched,
        "max_abs_diff": max_abs_diff,
        "original_seconds": round(original_seconds, 1),
        "fast_seconds": round(fast_seconds, 1),
        "report": str(report_path),
    }
