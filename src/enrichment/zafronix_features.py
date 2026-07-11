"""Leakage-safe Zafronix enrichment features.

Three families, each with an explicit availability/leakage rule:

1. WORLD CUP PEDIGREE (family: pedigree)
   Attached to ANY international match. For a match with kickoff date D, uses only World
   Cups whose end_date is strictly before D (a team's own in-progress tournament is
   excluded). Computable for any team; teams with no prior World Cup get 0 (a true fact,
   not an imputed guess). Broad coverage.

2. SQUAD AGE & POSITIONAL DEPTH (family: squad)
   Only for World Cup FINALS matches where both teams have a squad for that tournament.
   Uses age-at-tournament-start and position, both documented as known before kickoff.
   caps / nationalGoals are NOT used: their coverage in the source is ~0% (see coverage
   report), so a caps-based "experience" feature would be fabricated, not measured.

3. PLAYER PRIOR-WORLD-CUP EXPERIENCE (family: player_experience)
   Only for World Cup FINALS matches. Counts squad members who appeared for the same
   nation in a PRIOR World Cup (year < current tournament year). Strictly prior tournaments
   only — no same-tournament or future information.

Every feature is a difference (team_a minus team_b) or a symmetric availability indicator,
matching the production model's difference-based feature convention.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.enrichment.zafronix_config import FEATURES_DIR, REPORT_DIR, ensure_dirs
from src.enrichment.zafronix_entities import resolve_team
from src.enrichment.zafronix_normalize import load_normalized

# ---- feature name groups --------------------------------------------------- #
PEDIGREE_DIFF_FEATURES = [
    "z_prior_wc_appearances_diff",
    "z_prior_wc_titles_diff",
    "z_prior_wc_finals_diff",
    "z_prior_wc_semifinals_diff",
    "z_prior_wc_knockout_win_rate_diff",
    "z_prior_wc_goal_difference_diff",
    "z_prior_wc_best_finish_diff",
    "z_years_since_last_wc_diff",
    "z_prior_wc_experience_score_diff",
]
SQUAD_DIFF_FEATURES = [
    "z_squad_avg_age_diff",
    "z_squad_age_std_diff",
    "z_squad_defender_share_diff",
    "z_squad_forward_share_diff",
]
PLAYER_EXP_DIFF_FEATURES = [
    "z_players_prior_wc_share_diff",
    "z_squad_prior_wc_appearances_total_diff",
]
AVAILABILITY_FEATURES = ["z_pedigree_available", "z_squad_features_available"]

ALL_ZAFRONIX_FEATURES = (
    PEDIGREE_DIFF_FEATURES + SQUAD_DIFF_FEATURES + PLAYER_EXP_DIFF_FEATURES + AVAILABILITY_FEATURES
)


# --------------------------------------------------------------------------- #
# Pedigree timeline (cumulative-before-date, leakage-safe)
# --------------------------------------------------------------------------- #

def _experience_score(appearances, titles, finals, semis, quarters, ko_wins) -> float:
    """Documented composite. Higher = more accomplished World Cup pedigree.

    score = 1.0*appearances + 3.0*titles + 1.5*finals + 0.75*semifinals
            + 0.25*quarterfinals + 0.5*knockout_wins
    (finals/semifinals/quarterfinals are COUNTS of reaching that stage.)
    """
    return (1.0 * appearances + 3.0 * titles + 1.5 * finals
            + 0.75 * semis + 0.25 * quarters + 0.5 * ko_wins)


def build_pedigree_timeline() -> pd.DataFrame:
    """One row per (team, tournament) with cumulative pedigree valid FROM that WC's end."""
    tournaments, appearances, _ = load_normalized()
    if appearances.empty:
        return pd.DataFrame()
    end_by_year = pd.to_datetime(tournaments.set_index("year")["end_date"], errors="coerce")
    completed = tournaments.set_index("year")["is_completed"].astype(bool)

    app = appearances.copy()
    app["canonical"] = app["team_raw"].map(resolve_team)
    app["end_date"] = app["year"].map(end_by_year)
    app["is_completed"] = app["year"].map(completed).fillna(False)
    app = app[app["is_completed"] & app["end_date"].notna()].sort_values(["canonical", "end_date"])

    rows = []
    for team, g in app.groupby("canonical", sort=False):
        c_app = c_title = c_final = c_semi = c_quarter = c_ko_m = c_ko_w = 0
        c_gf = c_ga = 0
        best_finish = np.inf
        for _, r in g.iterrows():
            c_app += 1
            c_title += int(bool(r["is_champion"]))
            c_final += int(bool(r["reached_final"]))
            c_semi += int(bool(r["reached_semi"]))
            c_quarter += int(bool(r["reached_quarter"]))
            c_ko_m += int(r["ko_matches"] or 0)
            c_ko_w += int(r["ko_wins"] or 0)
            if pd.notna(r["tourn_gf"]):
                c_gf += int(r["tourn_gf"])
            if pd.notna(r["tourn_ga"]):
                c_ga += int(r["tourn_ga"])
            if pd.notna(r["final_position"]):
                best_finish = min(best_finish, float(r["final_position"]))
            rows.append({
                "canonical": team,
                "valid_from": r["end_date"],
                "last_wc_year": int(r["year"]),
                "recent_finish": float(r["final_position"]) if pd.notna(r["final_position"]) else np.nan,
                "prior_wc_appearances": c_app,
                "prior_wc_titles": c_title,
                "prior_wc_finals": c_final,
                "prior_wc_semifinals": c_semi,
                "prior_wc_quarterfinals": c_quarter,
                "prior_wc_knockout_matches": c_ko_m,
                "prior_wc_knockout_wins": c_ko_w,
                "prior_wc_knockout_win_rate": (c_ko_w / c_ko_m) if c_ko_m else 0.0,
                "prior_wc_goals_for": c_gf,
                "prior_wc_goals_against": c_ga,
                "prior_wc_goal_difference": c_gf - c_ga,
                "prior_wc_best_finish": best_finish if np.isfinite(best_finish) else np.nan,
                "prior_wc_experience_score": _experience_score(c_app, c_title, c_final, c_semi, c_quarter, c_ko_w),
            })
    timeline = pd.DataFrame(rows).sort_values(["canonical", "valid_from"]).reset_index(drop=True)
    return timeline


def _pedigree_asof(matches: pd.DataFrame, timeline: pd.DataFrame, team_col: str, prefix: str) -> pd.DataFrame:
    """merge_asof each match's team to its pedigree as of the last completed WC before kickoff."""
    stat_cols = [c for c in timeline.columns if c not in ("canonical", "valid_from")]
    left = matches[["_row", "date", team_col]].copy()
    left["canonical"] = left[team_col].map(resolve_team)
    left = left.sort_values("date")
    out_parts = []
    tl = timeline.sort_values("valid_from")
    for team, g in left.groupby("canonical", sort=False):
        sub_tl = tl[tl["canonical"] == team]
        if sub_tl.empty:
            merged = g.copy()
            for c in stat_cols:
                merged[c] = np.nan
        else:
            merged = pd.merge_asof(
                g.sort_values("date"), sub_tl.sort_values("valid_from"),
                left_on="date", right_on="valid_from", direction="backward",
            )
        out_parts.append(merged)
    res = pd.concat(out_parts, ignore_index=True) if out_parts else left
    res = res.rename(columns={c: f"{prefix}_{c}" for c in stat_cols})
    keep = ["_row"] + [f"{prefix}_{c}" for c in stat_cols]
    return res[keep]


# --------------------------------------------------------------------------- #
# Squad features (WC finals matches only)
# --------------------------------------------------------------------------- #

def _squad_year_stats() -> pd.DataFrame:
    """Per (canonical team, WC year) squad aggregates from age & position (leakage-safe)."""
    tournaments, _, players = load_normalized()
    if players.empty:
        return pd.DataFrame()
    p = players.copy()
    p["canonical"] = p["team_raw"].map(resolve_team)
    p["age"] = pd.to_numeric(p["age_at_tournament"], errors="coerce")
    grp = p.groupby(["year", "canonical"])
    stats = grp.agg(
        squad_size=("name", "count"),
        squad_avg_age=("age", "mean"),
        squad_age_std=("age", "std"),
    ).reset_index()
    # positional shares
    for pos in ["GK", "DF", "MF", "FW"]:
        share = grp.apply(lambda d, pos=pos: float((d["position_group"] == pos).mean()), include_groups=False)
        stats = stats.merge(share.rename(f"squad_{pos.lower()}_share").reset_index(), on=["year", "canonical"], how="left")
    return stats


def _player_prior_wc_experience() -> pd.DataFrame:
    """Per (canonical team, WC year): squad members who played a PRIOR WC for that nation."""
    _, _, players = load_normalized()
    if players.empty:
        return pd.DataFrame()
    p = players.copy()
    p["canonical"] = p["team_raw"].map(resolve_team)
    p["name_key"] = p["name"].astype(str).str.strip().str.casefold()
    # prior appearances per (team, player): list of years
    appearance_years: dict[tuple, list[int]] = {}
    for _, r in p.iterrows():
        appearance_years.setdefault((r["canonical"], r["name_key"]), []).append(int(r["year"]))

    rows = []
    for (year, team), g in p.groupby(["year", "canonical"]):
        n = len(g)
        with_prior = 0
        prior_total = 0
        for _, r in g.iterrows():
            years = appearance_years.get((team, r["name_key"]), [])
            prior = [y for y in years if y < year]
            if prior:
                with_prior += 1
                prior_total += len(prior)
        rows.append({
            "year": year, "canonical": team,
            "players_with_prior_wc": with_prior,
            "players_prior_wc_share": (with_prior / n) if n else 0.0,
            "squad_prior_wc_appearances_total": prior_total,
        })
    return pd.DataFrame(rows)


def _map_match_to_wc_year(matches: pd.DataFrame, tournaments: pd.DataFrame) -> pd.Series:
    """For WC-finals matches, map kickoff date -> tournament year via [start,end] window."""
    windows = []
    for _, t in tournaments.iterrows():
        start = pd.to_datetime(t["start_date"], errors="coerce")
        end = pd.to_datetime(t["end_date"], errors="coerce")
        if pd.notna(start) and pd.notna(end):
            windows.append((start, end, int(t["year"])))
    year = pd.Series(np.nan, index=matches.index)
    d = pd.to_datetime(matches["date"], errors="coerce")
    for start, end, yr in windows:
        year = year.mask((d >= start) & (d <= end), yr)
    return year


def _is_wc_finals(matches: pd.DataFrame) -> pd.Series:
    tour = matches.get("tournament")
    if tour is None:
        return pd.Series(False, index=matches.index)
    return tour.astype(str).str.strip().str.casefold().eq("fifa world cup")


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def build_zafronix_features(matches: pd.DataFrame) -> pd.DataFrame:
    """Return a frame aligned to `matches.index` with all Zafronix difference features."""
    ensure_dirs()
    tournaments, _, _ = load_normalized()
    work = matches.copy()
    work["date"] = pd.to_datetime(work["date"], errors="coerce")
    work["_row"] = np.arange(len(work))

    # --- pedigree (any match) ---
    timeline = build_pedigree_timeline()
    ped_a = _pedigree_asof(work, timeline, "team_a", "a")
    ped_b = _pedigree_asof(work, timeline, "team_b", "b")
    ped = work[["_row"]].merge(ped_a, on="_row", how="left").merge(ped_b, on="_row", how="left")

    def diff(col):
        return ped[f"a_{col}"] - ped[f"b_{col}"]

    feat = pd.DataFrame(index=work.index)
    feat["z_prior_wc_appearances_diff"] = diff("prior_wc_appearances").to_numpy()
    feat["z_prior_wc_titles_diff"] = diff("prior_wc_titles").to_numpy()
    feat["z_prior_wc_finals_diff"] = diff("prior_wc_finals").to_numpy()
    feat["z_prior_wc_semifinals_diff"] = diff("prior_wc_semifinals").to_numpy()
    feat["z_prior_wc_knockout_win_rate_diff"] = diff("prior_wc_knockout_win_rate").to_numpy()
    feat["z_prior_wc_goal_difference_diff"] = diff("prior_wc_goal_difference").to_numpy()
    # best_finish: lower is better -> a team with a better (smaller) best finish gets a positive edge
    feat["z_prior_wc_best_finish_diff"] = (ped["b_prior_wc_best_finish"] - ped["a_prior_wc_best_finish"]).to_numpy()
    # years since last WC: fewer years (more recent) is an edge -> b_minus_a
    ya = work["date"].dt.year.to_numpy() - ped["a_last_wc_year"].to_numpy()
    yb = work["date"].dt.year.to_numpy() - ped["b_last_wc_year"].to_numpy()
    feat["z_years_since_last_wc_diff"] = yb - ya
    feat["z_prior_wc_experience_score_diff"] = diff("prior_wc_experience_score").to_numpy()

    both_have_history = ped["a_prior_wc_appearances"].notna() & ped["b_prior_wc_appearances"].notna()
    feat["z_pedigree_available"] = both_have_history.astype(int).to_numpy()
    # pedigree diffs are 0 (neutral) when a team has no prior history; availability flag disambiguates
    for c in PEDIGREE_DIFF_FEATURES:
        feat[c] = pd.to_numeric(feat[c], errors="coerce").fillna(0.0)

    # --- squad + player-experience (WC finals matches only) ---
    wc_year = _map_match_to_wc_year(work, tournaments)
    is_finals = _is_wc_finals(work) & wc_year.notna()
    squad = _squad_year_stats()
    pexp = _player_prior_wc_experience()

    def _attach(prefix_team_col: str, year_series: pd.Series):
        key = pd.DataFrame({"year": year_series.to_numpy(),
                            "canonical": work[prefix_team_col].map(resolve_team).to_numpy()},
                           index=work.index)
        s = key.merge(squad, on=["year", "canonical"], how="left") if not squad.empty else key.assign()
        pe = key.merge(pexp, on=["year", "canonical"], how="left") if not pexp.empty else key.assign()
        return s, pe

    sa, pea = _attach("team_a", wc_year)
    sb, peb = _attach("team_b", wc_year)

    def _sq(df, col):
        return pd.to_numeric(df.get(col, pd.Series(np.nan, index=work.index)), errors="coerce").to_numpy()

    feat["z_squad_avg_age_diff"] = _sq(sa, "squad_avg_age") - _sq(sb, "squad_avg_age")
    feat["z_squad_age_std_diff"] = _sq(sa, "squad_age_std") - _sq(sb, "squad_age_std")
    feat["z_squad_defender_share_diff"] = _sq(sa, "squad_df_share") - _sq(sb, "squad_df_share")
    feat["z_squad_forward_share_diff"] = _sq(sa, "squad_fw_share") - _sq(sb, "squad_fw_share")
    feat["z_players_prior_wc_share_diff"] = _sq(pea, "players_prior_wc_share") - _sq(peb, "players_prior_wc_share")
    feat["z_squad_prior_wc_appearances_total_diff"] = (
        _sq(pea, "squad_prior_wc_appearances_total") - _sq(peb, "squad_prior_wc_appearances_total")
    )

    squad_avail = is_finals.to_numpy() & ~np.isnan(feat["z_squad_avg_age_diff"].to_numpy())
    feat["z_squad_features_available"] = squad_avail.astype(int)
    # Outside WC finals (or missing squad), squad diffs are undefined -> neutral 0 + availability flag.
    for c in SQUAD_DIFF_FEATURES + PLAYER_EXP_DIFF_FEATURES:
        feat[c] = pd.to_numeric(feat[c], errors="coerce").fillna(0.0)

    return feat[ALL_ZAFRONIX_FEATURES]


def build_and_save_features(matches: pd.DataFrame) -> dict:
    """Build features, persist values + coverage + registry, return coverage summary."""
    ensure_dirs()
    feat = build_zafronix_features(matches)
    values = pd.concat([matches[["match_id", "date", "team_a", "team_b", "tournament"]].reset_index(drop=True),
                        feat.reset_index(drop=True)], axis=1)
    values.to_csv(FEATURES_DIR / "zafronix_feature_values.csv", index=False)

    n = len(feat)
    coverage_rows = []
    for c in ALL_ZAFRONIX_FEATURES:
        nonzero = int((pd.to_numeric(feat[c], errors="coerce").fillna(0) != 0).sum())
        coverage_rows.append({"feature": c, "rows": n, "nonzero_rows": nonzero,
                              "nonzero_pct": round(100 * nonzero / max(n, 1), 3)})
    cov = pd.DataFrame(coverage_rows)
    cov.to_csv(FEATURES_DIR / "zafronix_feature_coverage.csv", index=False)
    cov.to_csv(REPORT_DIR / "zafronix_feature_coverage.csv", index=False)

    _write_registry()
    return {
        "rows": n,
        "features": ALL_ZAFRONIX_FEATURES,
        "pedigree_available_rows": int(feat["z_pedigree_available"].sum()),
        "squad_available_rows": int(feat["z_squad_features_available"].sum()),
        "values_path": str(FEATURES_DIR / "zafronix_feature_values.csv"),
        "coverage_path": str(FEATURES_DIR / "zafronix_feature_coverage.csv"),
    }


def _write_registry() -> None:
    registry = {
        "phase": "5H-A", "provider": "zafronix", "generated_note":
            "All features are difference (team_a - team_b) or symmetric availability indicators.",
        "families": {
            "pedigree": {
                "features": PEDIGREE_DIFF_FEATURES,
                "source_endpoint": "GET /tournaments/{year}",
                "source_fields": ["finalPosition", "knockoutPath", "groupStage"],
                "applicable_match_types": "any international match",
                "availability_semantics": "uses only World Cups with end_date strictly before kickoff",
                "leakage_rule": "prior completed World Cups only; a team's in-progress WC is excluded",
                "missing_value_strategy": "0 (no prior WC = true zero) + z_pedigree_available indicator",
                "status": "experimental",
            },
            "squad": {
                "features": SQUAD_DIFF_FEATURES,
                "source_endpoint": "GET /tournaments/{year} (embedded squad)",
                "source_fields": ["ageAtTournament", "position"],
                "applicable_match_types": "World Cup finals matches only",
                "availability_semantics": "age & position known at tournament start",
                "leakage_rule": "tournament-start values only; no in-tournament stats",
                "missing_value_strategy": "0 + z_squad_features_available indicator",
                "status": "experimental",
            },
            "player_experience": {
                "features": PLAYER_EXP_DIFF_FEATURES,
                "source_endpoint": "GET /tournaments/{year} (embedded squads across years)",
                "source_fields": ["squad player name", "year"],
                "applicable_match_types": "World Cup finals matches only",
                "availability_semantics": "prior-tournament squad membership (year < current)",
                "leakage_rule": "strictly prior World Cups; name+nation matched, no future data",
                "missing_value_strategy": "0 + z_squad_features_available indicator",
                "status": "experimental",
            },
        },
        "rejected_families": {
            "squad_caps_and_national_goals": {
                "reason": "Source coverage ~0% (caps/nationalGoals populated for <0.4% of players in every era).",
                "decision": "excluded from modeling; would be fabricated, not measured.",
            },
            "weather": {
                "reason": "Match weather is an observed/retrospective value with no pre-kickoff forecast provenance (see report §16).",
                "decision": "descriptive only; never a model feature.",
            },
            "physical_attributes_height_weight": {
                "reason": "heightCm/weightKg coverage ~0.4%.",
                "decision": "excluded.",
            },
        },
    }
    (REPORT_DIR / "zafronix_feature_registry.json").write_text(json.dumps(registry, indent=2), encoding="utf-8")
