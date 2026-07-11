"""Data-coverage audit: how much of the training corpus Zafronix can enrich."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from src.enrichment.zafronix_config import REPORT_DIR, ensure_dirs
from src.enrichment.zafronix_entities import resolve_team
from src.enrichment.zafronix_normalize import load_normalized


def _split_masks(df: pd.DataFrame):
    from src.modeling.splits import chronological_train_val_test_split

    train, val, test = chronological_train_val_test_split(df)
    return set(train["match_id"]), set(val["match_id"]), set(test["match_id"])


def build_coverage_report() -> dict:
    ensure_dirs()
    from src.modeling.data_loader import load_training_dataset

    tournaments, appearances, players = load_normalized()
    df = load_training_dataset()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    wc_nations = set(appearances["team_raw"].map(resolve_team).dropna()) if not appearances.empty else set()
    is_finals = df.get("tournament", pd.Series(index=df.index, dtype=str)).astype(str).str.casefold().eq("fifa world cup")
    both_wc = df["team_a"].isin(wc_nations) & df["team_b"].isin(wc_nations)

    tr, va, te = _split_masks(df)

    def split_stats(mask_name, mask):
        sub = df[mask]
        return {
            "split": mask_name,
            "matches": int(len(sub)),
            "wc_finals_matches": int(is_finals[mask].sum()),
            "both_teams_wc_nations": int(both_wc[mask].sum()),
            "both_teams_wc_nations_pct": round(100 * both_wc[mask].mean(), 2) if len(sub) else 0.0,
        }

    per_split = [
        split_stats("all", pd.Series(True, index=df.index)),
        split_stats("train", df["match_id"].isin(tr)),
        split_stats("validation", df["match_id"].isin(va)),
        split_stats("test", df["match_id"].isin(te)),
    ]

    # coverage by year (squad field completeness)
    by_year_rows = []
    if not players.empty:
        p = players.copy()
        for f in ["position_group", "age_at_tournament", "caps_at_start", "national_goals_at_start"]:
            p[f + "_ok"] = p[f].notna() & (p[f].astype(str).str.strip() != "")
        for year, g in p.groupby("year"):
            by_year_rows.append({
                "year": int(year), "players": int(len(g)),
                "position_pct": round(100 * g["position_group_ok"].mean(), 1),
                "age_pct": round(100 * g["age_at_tournament_ok"].mean(), 1),
                "caps_pct": round(100 * g["caps_at_start_ok"].mean(), 1),
                "national_goals_pct": round(100 * g["national_goals_at_start_ok"].mean(), 1),
            })
    by_year = pd.DataFrame(by_year_rows)
    by_year.to_csv(REPORT_DIR / "zafronix_coverage_by_year.csv", index=False)

    # coverage by feature field (overall)
    feat_rows = []
    if not players.empty:
        total = len(players)
        for f in ["position_group", "age_at_tournament", "caps_at_start", "national_goals_at_start"]:
            ok = int((players[f].notna() & (players[f].astype(str).str.strip() != "")).sum())
            feat_rows.append({"field": f, "populated": ok, "total": total,
                              "populated_pct": round(100 * ok / max(total, 1), 2)})
    pd.DataFrame(feat_rows).to_csv(REPORT_DIR / "zafronix_coverage_by_feature.csv", index=False)

    # coverage by tournament
    tour_rows = []
    if not appearances.empty:
        for year, g in appearances.groupby("year"):
            tour_rows.append({"year": int(year), "teams": int(len(g)),
                              "with_final_position": int(g["final_position"].notna().sum()),
                              "with_knockout_path": int((g["ko_matches"].fillna(0) > 0).sum())})
    pd.DataFrame(tour_rows).to_csv(REPORT_DIR / "zafronix_coverage_by_tournament.csv", index=False)

    report = {
        "training_matches": int(len(df)),
        "wc_finals_matches_total": int(is_finals.sum()),
        "wc_finals_pct_of_training": round(100 * is_finals.mean(), 3),
        "both_teams_wc_nations_total": int(both_wc.sum()),
        "both_teams_wc_nations_pct": round(100 * both_wc.mean(), 2),
        "distinct_wc_nations": len(wc_nations),
        "per_split": per_split,
        "tournaments_covered": int(len(tournaments)),
        "years": tournaments["year"].tolist() if not tournaments.empty else [],
        "squad_field_coverage_note": (
            "position ~100% and age ~95-100% in every era; caps/nationalGoals/height/weight <0.5% "
            "in every era -> only position and age are usable; caps-based experience features are rejected."
        ),
    }
    (REPORT_DIR / "zafronix_coverage_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
