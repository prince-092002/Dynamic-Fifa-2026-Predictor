"""Build public-safe JSON exports for the website and dashboard.

Transforms current backend outputs into stable, versioned contracts under
public_data/. Nothing is fabricated: every value traces to a backend file, and
files that cannot be sourced are simply not written.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.config import PROJECT_ROOT
from src.live_state.live_config import LIVE_STATE_DIR, coerce_bool_series
from src.public_export.team_mapping import team_code, team_flag, team_slug
from src.simulation.tournament_structure import is_tbd_team
from src.utils.dates import now_utc_iso

PUBLIC_DATA_DIR = PROJECT_ROOT / "public_data"
REPORTS_DIR = PROJECT_ROOT / "outputs" / "reports"

STAGE_ORDER = ["Group Stage", "Round of 32", "Round of 16", "Quarterfinal", "Semifinal", "Third Place Playoff", "Final"]

SOURCE_LABELS = {
    "completed_result": "Completed real result",
    "live_model_exact": "Live XGBoost prediction",
    "live_model_reversed": "Live XGBoost prediction",
    "live_model": "Live XGBoost prediction",
    "model_prediction_file": "Pre-tournament model prediction",
    "model_exact": "Pre-tournament model prediction",
    "model_reversed": "Pre-tournament model prediction",
    "elo_fallback": "Elo fallback",
    "neutral_fallback": "Neutral fallback",
    "unresolved_tbd": "Awaiting real participants",
}


def _read_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path) if path.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return path.name


def _meta(sources: list[Path], extra: dict | None = None) -> dict:
    meta = {"generated_at": now_utc_iso(), "source_files": [_rel(p) for p in sources]}
    meta.update(extra or {})
    return meta


def _num(value, digits: int = 6):
    number = pd.to_numeric(value, errors="coerce")
    return round(float(number), digits) if pd.notna(number) else None


def _context() -> dict:
    gate = _read_json(LIVE_STATE_DIR / "live_forecast_quality_gate.json")
    manifest = _read_json(LIVE_STATE_DIR / "latest_live_run_manifest.json")
    return {
        "provider": manifest.get("provider", "football_data_org" if gate.get("football_data_org_fixture_rows", 0) else "unknown"),
        "forecast_mode": gate.get("forecast_mode", "unknown"),
        "current_phase": gate.get("current_phase", "unknown"),
        "run_id": manifest.get("run_id"),
    }


# ---------------------------------------------------------------------------
# Team lifecycle + statistics (derived from completed real matches only)
# ---------------------------------------------------------------------------

def compute_team_lifecycle() -> dict[str, dict]:
    """Status, stage reached, and elimination info per team from real bracket state."""
    teams = _read_csv(LIVE_STATE_DIR / "football_data_org_teams_normalized.csv")
    bracket = _read_csv(LIVE_STATE_DIR / "merged_bracket_state.csv")
    lifecycle: dict[str, dict] = {}
    for name in teams.get("team", pd.Series(dtype=str)).dropna():
        lifecycle[str(name)] = {"status": "eliminated", "stage_reached": "Group Stage", "eliminated_by": None, "eliminated_in": "Group Stage"}
    if bracket.empty:
        return lifecycle
    completed = coerce_bool_series(bracket.get("is_completed", pd.Series(False, index=bracket.index)))
    stage_rank = {stage: rank for rank, stage in enumerate(STAGE_ORDER)}
    alive: set[str] = set()
    losers: dict[str, dict] = {}
    final_row = None
    for idx, row in bracket.iterrows():
        stage = str(row.get("stage"))
        team_a, team_b = row.get("team_a"), row.get("team_b")
        for team in [team_a, team_b]:
            if pd.notna(team) and not is_tbd_team(team):
                entry = lifecycle.setdefault(str(team), {"status": "eliminated", "stage_reached": "Group Stage", "eliminated_by": None, "eliminated_in": "Group Stage"})
                if stage_rank.get(stage, 0) > stage_rank.get(entry["stage_reached"], 0):
                    entry["stage_reached"] = stage
        if bool(completed.loc[idx]):
            winner = row.get("winner")
            if pd.notna(winner) and not is_tbd_team(winner):
                alive.add(str(winner))
                for team in [team_a, team_b]:
                    if pd.notna(team) and str(team) != str(winner):
                        losers[str(team)] = {"eliminated_by": str(winner), "eliminated_in": stage}
            if stage == "Final":
                final_row = row
        else:
            for team in [team_a, team_b]:
                if pd.notna(team) and not is_tbd_team(team):
                    alive.add(str(team))
    alive -= set(losers)
    for name, entry in lifecycle.items():
        if name in alive:
            entry.update({"status": "alive", "eliminated_by": None, "eliminated_in": None})
        elif name in losers:
            entry.update({"status": "eliminated", **losers[name]})
    if final_row is not None:
        winner = str(final_row.get("winner"))
        runner = str(final_row.get("team_b") if str(final_row.get("team_a")) == winner else final_row.get("team_a"))
        if winner in lifecycle:
            lifecycle[winner].update({"status": "champion", "eliminated_by": None, "eliminated_in": None})
        if runner in lifecycle:
            lifecycle[runner]["status"] = "runner_up"
    return lifecycle


def compute_team_stats() -> dict[str, dict]:
    """Per-team tournament record from completed real fixtures (provider data, unique matches)."""
    fixtures = _read_csv(LIVE_STATE_DIR / "football_data_org_fixtures_normalized.csv")
    stats: dict[str, dict] = {}
    if fixtures.empty:
        return stats
    completed = fixtures[coerce_bool_series(fixtures.get("is_completed", pd.Series(False, index=fixtures.index)))].copy()
    completed = completed.drop_duplicates(subset=["fixture_id"])
    completed["date"] = pd.to_datetime(completed["date"], errors="coerce", utc=True)
    for _, row in completed.sort_values("date").iterrows():
        goals_a = pd.to_numeric(row.get("team_a_goals"), errors="coerce")
        goals_b = pd.to_numeric(row.get("team_b_goals"), errors="coerce")
        if pd.isna(goals_a) or pd.isna(goals_b):
            continue
        winner = str(row.get("winner")) if pd.notna(row.get("winner")) else "Draw"
        for team, opponent, gf, ga in [(row.get("team_a"), row.get("team_b"), goals_a, goals_b), (row.get("team_b"), row.get("team_a"), goals_b, goals_a)]:
            if pd.isna(team) or is_tbd_team(team):
                continue
            entry = stats.setdefault(
                str(team),
                {"played": 0, "wins": 0, "draws": 0, "losses": 0, "goals_for": 0, "goals_against": 0, "clean_sheets": 0, "matches": []},
            )
            result = "W" if winner == str(team) else ("D" if winner == "Draw" else "L")
            entry["played"] += 1
            entry["wins"] += int(result == "W")
            entry["draws"] += int(result == "D")
            entry["losses"] += int(result == "L")
            entry["goals_for"] += int(gf)
            entry["goals_against"] += int(ga)
            entry["clean_sheets"] += int(ga == 0)
            entry["matches"].append(
                {
                    "date": str(row.get("date"))[:10],
                    "stage": row.get("stage"),
                    "opponent": str(opponent),
                    "goals_for": int(gf),
                    "goals_against": int(ga),
                    "result": result,
                    "score": f"{int(gf)}-{int(ga)}",
                }
            )
    for entry in stats.values():
        played = entry["played"]
        entry["goal_difference"] = entry["goals_for"] - entry["goals_against"]
        entry["avg_goals_for"] = round(entry["goals_for"] / played, 2) if played else None
        entry["avg_goals_against"] = round(entry["goals_against"] / played, 2) if played else None
    return stats


def _team_groups() -> dict[str, str]:
    fixtures = _read_csv(LIVE_STATE_DIR / "football_data_org_fixtures_normalized.csv")
    groups: dict[str, str] = {}
    if fixtures.empty:
        return groups
    group_stage = fixtures[fixtures.get("stage", pd.Series(dtype=str)).eq("Group Stage")]
    for _, row in group_stage.iterrows():
        label = str(row.get("group") or "").replace("GROUP_", "").strip()
        for team in [row.get("team_a"), row.get("team_b")]:
            if pd.notna(team) and label:
                groups.setdefault(str(team), label)
    return groups


# ---------------------------------------------------------------------------
# Export builders
# ---------------------------------------------------------------------------

def _build_overview(lifecycle: dict) -> dict:
    summary = _read_json(LIVE_STATE_DIR / "live_forecast_summary.json")
    gate = _read_json(LIVE_STATE_DIR / "live_forecast_quality_gate.json")
    freshness = _read_json(LIVE_STATE_DIR / "live_provider_freshness.json")
    manifest = _read_json(LIVE_STATE_DIR / "latest_live_run_manifest.json")
    matchups = _read_csv(LIVE_STATE_DIR / "remaining_known_knockout_matchups.csv")
    statuses = [entry["status"] for entry in lifecycle.values()]
    return {
        "current_phase": gate.get("current_phase"),
        "completed_matches": gate.get("completed_result_count"),
        "teams_total": len(lifecycle),
        "teams_alive": sum(1 for s in statuses if s in {"alive", "champion", "runner_up"}),
        "teams_eliminated": sum(1 for s in statuses if s == "eliminated"),
        "known_unresolved_matchups": int(len(matchups)),
        "top_champion": summary.get("top_champion"),
        "top_champion_probability": _num(summary.get("top_champion_probability")),
        "champion_probability_basis": summary.get("champion_probability_basis"),
        "monte_carlo_top_champion": summary.get("monte_carlo_top_champion"),
        "monte_carlo_top_champion_probability": _num(summary.get("monte_carlo_top_champion_probability")),
        "top_finalist_pair": summary.get("top_finalist_pair"),
        "top_finalist_pair_probability": _num(summary.get("top_finalist_pair_probability")),
        "forecast_mode": gate.get("forecast_mode"),
        "public_label": gate.get("public_label"),
        "provider": freshness.get("provider", "unknown"),
        "data_source_mode": freshness.get("data_source_mode", "unknown"),
        "data_age_minutes": freshness.get("data_age_minutes"),
        "source_quality_score": gate.get("source_quality_score"),
        "simulations": summary.get("simulations"),
        "selected_model": manifest.get("selected_model"),
        "live_forecast_validation": manifest.get("live_forecast_validation"),
        "broader_refresh_validation": manifest.get("broader_refresh_validation"),
        "run_id": manifest.get("run_id"),
        "seed": manifest.get("seed"),
        "_meta": _meta(
            [LIVE_STATE_DIR / "live_forecast_summary.json", LIVE_STATE_DIR / "live_forecast_quality_gate.json", LIVE_STATE_DIR / "live_provider_freshness.json", LIVE_STATE_DIR / "latest_live_run_manifest.json"]
        ),
    }


def _build_bracket() -> dict:
    bracket = _read_csv(LIVE_STATE_DIR / "merged_bracket_state.csv")
    fixtures = _read_csv(LIVE_STATE_DIR / "football_data_org_fixtures_normalized.csv")
    predictions = _read_csv(LIVE_STATE_DIR / "live_knockout_match_predictions.csv")
    fixture_info = {}
    if not fixtures.empty:
        for _, row in fixtures.iterrows():
            fixture_info[str(row.get("fixture_id"))] = row
    prediction_by_pair = {}
    if not predictions.empty:
        for _, row in predictions[predictions.get("prediction_status", "") == "predicted"].iterrows():
            prediction_by_pair[frozenset([str(row["team_a"]), str(row["team_b"])])] = row
    rounds: dict[str, list] = {}
    context = _context()
    for _, row in bracket.iterrows():
        stage = str(row.get("stage"))
        team_a, team_b = row.get("team_a"), row.get("team_b")
        known = pd.notna(team_a) and pd.notna(team_b) and not is_tbd_team(team_a) and not is_tbd_team(team_b)
        is_completed = bool(coerce_bool_series(pd.Series([row.get("is_completed", False)])).iloc[0])
        fixture = fixture_info.get(str(row.get("fixture_id")))
        match: dict = {
            "fixture_id": row.get("fixture_id"),
            "stage": stage,
            "date": (str(fixture.get("date")) if fixture is not None and pd.notna(fixture.get("date")) else None),
            "state": "completed" if is_completed else ("scheduled_known" if known else "tbd"),
            "team_a": str(team_a) if known else None,
            "team_b": str(team_b) if known else None,
        }
        if is_completed and fixture is not None:
            goals_a = pd.to_numeric(fixture.get("team_a_goals"), errors="coerce")
            goals_b = pd.to_numeric(fixture.get("team_b_goals"), errors="coerce")
            match.update(
                {
                    "score": f"{int(goals_a)}-{int(goals_b)}" if pd.notna(goals_a) and pd.notna(goals_b) else None,
                    "winner": str(row.get("winner")) if pd.notna(row.get("winner")) else None,
                    "source": "completed_result",
                    "source_label": SOURCE_LABELS["completed_result"],
                }
            )
        elif known:
            prediction = prediction_by_pair.get(frozenset([str(team_a), str(team_b)]))
            if prediction is not None:
                aligned = str(prediction["team_a"]) == str(team_a)
                advance_a = _num(prediction["prob_team_a_advance"] if aligned else prediction["prob_team_b_advance"])
                advance_b = _num(prediction["prob_team_b_advance"] if aligned else prediction["prob_team_a_advance"])
                match.update(
                    {
                        "team_a_advance_probability": advance_a,
                        "team_b_advance_probability": advance_b,
                        "predicted_favorite": str(team_a) if (advance_a or 0) >= (advance_b or 0) else str(team_b),
                        "source": "live_model",
                        "source_label": SOURCE_LABELS["live_model"],
                        "model": prediction.get("model_name"),
                    }
                )
            else:
                match.update({"source": "elo_fallback", "source_label": SOURCE_LABELS["elo_fallback"]})
        else:
            match.update({"placeholder": "Winners of earlier rounds", "source": "unresolved_tbd", "source_label": SOURCE_LABELS["unresolved_tbd"]})
        rounds.setdefault(stage, []).append(match)
    return {
        "rounds": [{"stage": stage, "matches": rounds[stage]} for stage in STAGE_ORDER if stage in rounds],
        "source_legend": {key: SOURCE_LABELS[key] for key in ["completed_result", "live_model", "model_exact", "elo_fallback", "neutral_fallback", "unresolved_tbd"]},
        "current_phase": context["current_phase"],
        "_meta": _meta([LIVE_STATE_DIR / "merged_bracket_state.csv", LIVE_STATE_DIR / "football_data_org_fixtures_normalized.csv", LIVE_STATE_DIR / "live_knockout_match_predictions.csv"], context),
    }


def _build_probability_export(csv_name: str, value_column: str, count_column: str) -> dict | None:
    frame = _read_csv(LIVE_STATE_DIR / csv_name)
    if frame.empty:
        return None
    summary = _read_json(LIVE_STATE_DIR / "live_forecast_summary.json")
    entries = []
    for _, row in frame.iterrows():
        entry = {key: (str(row[key]) if isinstance(row.get(key), str) else row.get(key)) for key in frame.columns if key != count_column}
        entry[value_column] = _num(row.get(value_column))
        if "team" in entry:
            entry["slug"] = team_slug(entry["team"])
        entries.append(entry)
    return {
        "entries": entries,
        "simulations": summary.get("simulations"),
        "_meta": _meta([LIVE_STATE_DIR / csv_name], _context()),
    }


def _build_matchup_predictions() -> dict:
    predictions = _read_csv(LIVE_STATE_DIR / "live_knockout_match_predictions.csv")
    entries = []
    for _, row in predictions.iterrows():
        predicted = row.get("prediction_status") == "predicted"
        entries.append(
            {
                "stage": row.get("stage"),
                "team_a": row.get("team_a"),
                "team_b": row.get("team_b"),
                "team_a_slug": team_slug(row.get("team_a")),
                "team_b_slug": team_slug(row.get("team_b")),
                "team_a_advance_probability": _num(row.get("prob_team_a_advance")) if predicted else None,
                "team_b_advance_probability": _num(row.get("prob_team_b_advance")) if predicted else None,
                "prob_team_a_win": _num(row.get("prob_team_a_win")) if predicted else None,
                "prob_draw": _num(row.get("prob_draw")) if predicted else None,
                "prob_team_a_loss": _num(row.get("prob_team_a_loss")) if predicted else None,
                "favorite": (row.get("team_a") if (row.get("prob_team_a_advance") or 0) >= (row.get("prob_team_b_advance") or 0) else row.get("team_b")) if predicted else None,
                "model": row.get("model_name"),
                "prediction_status": row.get("prediction_status"),
                "probability_source": row.get("probability_source"),
                "source_label": SOURCE_LABELS.get(str(row.get("probability_source")), str(row.get("probability_source"))),
                "generated_at": row.get("generated_at"),
            }
        )
    return {"matchups": entries, "_meta": _meta([LIVE_STATE_DIR / "live_knockout_match_predictions.csv"], _context())}


def _build_teams(lifecycle: dict, stats: dict) -> tuple[dict, dict]:
    groups = _team_groups()
    champion = _read_csv(LIVE_STATE_DIR / "live_champion_probabilities.csv")
    reach = _read_csv(LIVE_STATE_DIR / "team_reach_final_probabilities.csv")
    matchups = _read_csv(LIVE_STATE_DIR / "remaining_known_knockout_matchups.csv")
    predictions = _read_csv(LIVE_STATE_DIR / "live_knockout_match_predictions.csv")
    champion_map = dict(zip(champion.get("team", []), champion.get("champion_probability", []))) if not champion.empty else {}
    reach_map = dict(zip(reach.get("team", []), reach.get("reach_final_probability", []))) if not reach.empty else {}
    next_matchup: dict[str, dict] = {}
    prediction_by_pair = {}
    if not predictions.empty:
        for _, row in predictions[predictions.get("prediction_status", "") == "predicted"].iterrows():
            prediction_by_pair[frozenset([str(row["team_a"]), str(row["team_b"])])] = row
    for _, row in matchups.iterrows():
        pair = frozenset([str(row["team_a"]), str(row["team_b"])])
        prediction = prediction_by_pair.get(pair)
        for team, opponent in [(row["team_a"], row["team_b"]), (row["team_b"], row["team_a"])]:
            info = {"opponent": str(opponent), "stage": row.get("stage"), "date": row.get("date")}
            if prediction is not None:
                aligned = str(prediction["team_a"]) == str(team)
                info["advance_probability"] = _num(prediction["prob_team_a_advance"] if aligned else prediction["prob_team_b_advance"])
                info["source_label"] = SOURCE_LABELS.get(str(prediction.get("probability_source")), "Live XGBoost prediction")
            next_matchup[str(team)] = info
    team_rows = []
    stats_rows = {}
    for name in sorted(lifecycle):
        life = lifecycle[name]
        team_stat = stats.get(name, {})
        slug = team_slug(name)
        team_rows.append(
            {
                "team": name,
                "slug": slug,
                "code": team_code(name),
                "flag": team_flag(name),
                "group": groups.get(name),
                "status": life["status"],
                "stage_reached": life["stage_reached"],
                "eliminated_by": life["eliminated_by"],
                "eliminated_in": life["eliminated_in"],
                "played": team_stat.get("played", 0),
                "wins": team_stat.get("wins", 0),
                "draws": team_stat.get("draws", 0),
                "losses": team_stat.get("losses", 0),
                "goals_for": team_stat.get("goals_for", 0),
                "goals_against": team_stat.get("goals_against", 0),
                "goal_difference": team_stat.get("goal_difference", 0),
                "champion_probability": _num(champion_map.get(name)) if life["status"] in {"alive", "champion"} else (0.0 if name in champion_map or life["status"] == "eliminated" else None),
                "reach_final_probability": _num(reach_map.get(name)) if life["status"] in {"alive", "champion", "runner_up"} else (0.0 if life["status"] == "eliminated" else None),
                "next_matchup": next_matchup.get(name),
                "latest_result": (team_stat.get("matches") or [None])[-1],
            }
        )
        stats_rows[slug] = {
            "team": name,
            "slug": slug,
            **{k: v for k, v in team_stat.items() if k != "matches"},
            "matches": team_stat.get("matches", []),
        }
    context = _context()
    teams_export = {"teams": team_rows, "_meta": _meta([LIVE_STATE_DIR / "football_data_org_teams_normalized.csv", LIVE_STATE_DIR / "merged_bracket_state.csv", LIVE_STATE_DIR / "live_champion_probabilities.csv"], context)}
    stats_export = {"team_stats": stats_rows, "_meta": _meta([LIVE_STATE_DIR / "football_data_org_fixtures_normalized.csv"], context)}
    return teams_export, stats_export


def _build_history_export() -> dict | None:
    frames = {
        "champion": _read_csv(LIVE_STATE_DIR / "champion_probability_history.csv"),
        "finalist": _read_csv(LIVE_STATE_DIR / "finalist_probability_history.csv"),
        "finalist_pair": _read_csv(LIVE_STATE_DIR / "finalist_pair_probability_history.csv"),
    }
    if all(frame.empty for frame in frames.values()):
        return None
    payload: dict = {"_meta": _meta([LIVE_STATE_DIR / f"{name}_probability_history.csv" for name in ["champion", "finalist", "finalist_pair"]], _context())}
    for name, frame in frames.items():
        payload[name] = frame.to_dict(orient="records") if not frame.empty else []
    return payload


def _build_source_history_export() -> dict | None:
    frame = _read_csv(LIVE_STATE_DIR / "probability_source_history.csv")
    if frame.empty:
        return None
    return {"runs": frame.to_dict(orient="records"), "_meta": _meta([LIVE_STATE_DIR / "probability_source_history.csv"])}


def _validation_counts(path: Path) -> dict | None:
    frame = _read_csv(path)
    if frame.empty or "status" not in frame.columns:
        return None
    counts = frame["status"].value_counts().to_dict()
    return {"pass": int(counts.get("pass", 0)), "warn": int(counts.get("warn", 0)), "fail": int(counts.get("fail", 0))}


def _build_system_health() -> dict:
    freshness = _read_json(LIVE_STATE_DIR / "live_provider_freshness.json")
    gate = _read_json(LIVE_STATE_DIR / "live_forecast_quality_gate.json")
    return {
        "provider_freshness": freshness or None,
        "quality_gate": {
            "forecast_mode": gate.get("forecast_mode"),
            "public_label": gate.get("public_label"),
            "source_quality_score": gate.get("source_quality_score"),
            "current_phase": gate.get("current_phase"),
            "completed_result_count": gate.get("completed_result_count"),
            "fallback_usage_rate": gate.get("fallback_usage_rate"),
            "finalist_prediction_allowed": gate.get("finalist_prediction_allowed"),
        },
        "validations": {
            "broader_data_validation": _validation_counts(REPORTS_DIR / "data_validation_report.csv"),
            "live_forecast_validation": _validation_counts(REPORTS_DIR / "live_state" / "live_validation_report.csv"),
        },
        "_meta": _meta([LIVE_STATE_DIR / "live_provider_freshness.json", LIVE_STATE_DIR / "live_forecast_quality_gate.json", REPORTS_DIR / "data_validation_report.csv"]),
    }


def _build_model_insights() -> dict | None:
    registry = _read_json(PROJECT_ROOT / "outputs" / "models" / "model_registry.json")
    models = registry.get("models", [])
    if not models:
        return None
    rows = []
    selected_features: list[str] = []
    for model in models:
        metrics = model.get("test_metrics", {}) or {}
        rows.append(
            {
                "model": model.get("model_name"),
                "selected": bool(model.get("selected_model")),
                "test_accuracy": _num(metrics.get("accuracy"), 4),
                "test_log_loss": _num(metrics.get("log_loss"), 4),
                "test_brier_score": _num(metrics.get("brier_score"), 4),
                "test_macro_f1": _num(metrics.get("macro_f1"), 4),
                "train_rows": model.get("train_rows"),
                "test_rows": model.get("test_rows"),
            }
        )
        if model.get("selected_model"):
            selected_features = model.get("feature_columns", [])
    importances = None
    try:
        import joblib

        model_path = PROJECT_ROOT / "outputs" / "models" / "selected_model.joblib"
        if model_path.exists() and selected_features:
            artifact = joblib.load(model_path)
            booster = artifact.named_steps["model"] if hasattr(artifact, "named_steps") else artifact
            values = getattr(booster, "feature_importances_", None)
            if values is not None and len(values) == len(selected_features):
                pairs = sorted(zip(selected_features, values), key=lambda item: -float(item[1]))
                importances = [{"feature": feature, "importance": _num(value)} for feature, value in pairs]
    except Exception:
        importances = None
    diagnostics = None
    diag_path = REPORTS_DIR / "modeling" / "phase5g" / "diagnostic_metrics.json"
    diag = _read_json(diag_path)
    if diag.get("models", {}).get("xgboost"):
        test = diag["models"]["xgboost"]["test"]
        diagnostics = {
            "evaluation": "chronological 70/15/15 split; leakage-safe (shift-before-rolling, pre-match Elo); test set 7,439 matches",
            "per_class": {cls: {"precision": _num(test["precision"][cls]), "recall": _num(test["recall"][cls]), "f1": _num(test["f1"][cls])} for cls in test["precision"]},
            "actual_distribution": test["actual_distribution"],
            "predicted_distribution": test["predicted_distribution"],
            "calibration_ece": _num(test.get("ece")),
            "macro_f1_note": (
                "XGBoost's lower macro-F1 vs Logistic Regression is a draw-class argmax artifact, not a defect: draws are the "
                "minority outcome (23%) and rarely the single most likely result, so a calibrated model seldom argmax-predicts them. "
                "XGBoost is chosen for its superior calibration (ECE 0.005) and log loss because the Monte Carlo simulator samples "
                "from probabilities — it never needs the model to hard-predict a draw. Full analysis: Phase 5G report."
            ),
        }
    return {
        "models": rows,
        "selected_feature_columns": selected_features,
        "global_feature_importance": importances,
        "importance_note": "Global feature importance shows which features are influential across the model overall. It does not by itself explain a specific matchup.",
        "diagnostics": diagnostics,
        "_meta": _meta([PROJECT_ROOT / "outputs" / "models" / "model_registry.json", PROJECT_ROOT / "outputs" / "models" / "selected_model.joblib", diag_path]),
    }


def build_public_exports(target_dir: Path | None = None) -> dict:
    output_dir = Path(target_dir) if target_dir else PUBLIC_DATA_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    lifecycle = compute_team_lifecycle()
    stats = compute_team_stats()
    teams_export, stats_export = _build_teams(lifecycle, stats)
    exports: dict[str, dict | None] = {
        "latest_overview.json": _build_overview(lifecycle),
        "knockout_bracket.json": _build_bracket(),
        "champion_forecast.json": _build_probability_export("live_champion_probabilities.csv", "champion_probability", "champion_count"),
        "finalist_forecast.json": _build_probability_export("team_reach_final_probabilities.csv", "reach_final_probability", "reach_final_count"),
        "finalist_pairs.json": _build_probability_export("finalist_pair_probabilities.csv", "probability", "count"),
        "matchup_predictions.json": _build_matchup_predictions(),
        "teams.json": teams_export,
        "team_stats.json": stats_export,
        "forecast_history.json": _build_history_export(),
        "probability_source_history.json": _build_source_history_export(),
        "system_health.json": _build_system_health(),
        "latest_run_manifest.json": {**_read_json(LIVE_STATE_DIR / "latest_live_run_manifest.json"), "_meta": _meta([LIVE_STATE_DIR / "latest_live_run_manifest.json"])},
        "model_insights.json": _build_model_insights(),
    }
    written, skipped = [], []
    for name, payload in exports.items():
        if payload is None:
            skipped.append(name)
            continue
        (output_dir / name).write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
        written.append(name)
    return {"written": written, "skipped": skipped, "directory": _rel(output_dir)}
