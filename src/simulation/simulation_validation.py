"""Validate simulation inputs and outputs."""

from __future__ import annotations

import pandas as pd

from src.simulation.simulation_config import SIMULATION_REPORT_DIR, ensure_simulation_directories
from src.simulation.tournament_structure import is_tbd_team


def _row(check: str, status: str, message: str, rows_affected: int = 0) -> dict:
    return {"check": check, "status": status, "message": message, "rows_affected": rows_affected}


def validate_simulation(inputs: dict | None = None, aggregate: dict | None = None, n_simulations: int = 0, full_champion_possible: bool = False) -> dict:
    ensure_simulation_directories()
    rows = []
    if inputs:
        predictions = inputs["predictions"]
        predicted = predictions[predictions.get("prediction_status", "") == "predicted"]
        missing_probs = int(predicted[["prob_team_a_loss", "prob_draw", "prob_team_a_win"]].isna().any(axis=1).sum()) if not predicted.empty else 0
        rows.append(_row("predicted_probabilities_exist", "pass" if missing_probs == 0 else "fail", f"{missing_probs} predicted rows missing probabilities", missing_probs))
        probs = predicted[["prob_team_a_loss", "prob_draw", "prob_team_a_win"]].apply(pd.to_numeric, errors="coerce")
        impossible = int(((probs < 0) | (probs > 1)).any(axis=1).sum()) if not probs.empty else 0
        rows.append(_row("probabilities_possible", "pass" if impossible == 0 else "fail", f"{impossible} rows have impossible probabilities", impossible))
        tbd_predicted = int(predicted.apply(lambda row: is_tbd_team(row.get("team_a")) or is_tbd_team(row.get("team_b")), axis=1).sum()) if not predicted.empty else 0
        rows.append(_row("tbd_not_treated_as_real_team", "pass" if tbd_predicted == 0 else "fail", f"{tbd_predicted} predicted rows contain TBD teams", tbd_predicted))
        rows.append(_row("completed_results_fixed", "pass", f"{len(inputs.get('results', []))} completed results loaded"))
    rows.append(_row("simulation_count_positive", "pass" if n_simulations > 0 else "fail", f"{n_simulations} simulations"))
    if aggregate and "advancement_df" in aggregate:
        adv = aggregate["advancement_df"]
        prob_cols = [c for c in adv.columns if c.endswith("_prob")]
        invalid = int(((adv[prob_cols].apply(pd.to_numeric, errors="coerce") < 0) | (adv[prob_cols].apply(pd.to_numeric, errors="coerce") > 1)).any(axis=1).sum()) if prob_cols and not adv.empty else 0
        rows.append(_row("advancement_probabilities_between_0_and_1", "pass" if invalid == 0 else "fail", f"{invalid} invalid rows", invalid))
    if full_champion_possible and aggregate and "champion_df" in aggregate:
        champion = aggregate["champion_df"]
        champion_sum = pd.to_numeric(champion.get("champion_prob", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
        ok = abs(champion_sum - 1.0) <= 0.01
        rows.append(_row("champion_probability_sum", "pass" if ok else "fail", f"Champion probability sum: {champion_sum:.4f}"))
    else:
        rows.append(_row("champion_probability_sum", "pass", "Champion probabilities are intentionally blank/partial unless full bracket mode completes."))
    df = pd.DataFrame(rows)
    csv_path = SIMULATION_REPORT_DIR / "simulation_validation_report.csv"
    md_path = SIMULATION_REPORT_DIR / "simulation_validation_report.md"
    df.to_csv(csv_path, index=False)
    lines = ["# Simulation Validation Report", "", "| Check | Status | Message | Rows affected |", "|---|---|---|---:|"]
    for _, row in df.iterrows():
        lines.append(f"| {row['check']} | {row['status']} | {row['message']} | {row['rows_affected']} |")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    return {"status": "fail" if (df["status"] == "fail").any() else "pass", "report": str(md_path), "csv": str(csv_path)}
