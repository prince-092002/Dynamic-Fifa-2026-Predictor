"""Optional probability calibration reporting."""

from __future__ import annotations

from src.modeling.model_config import MODELING_REPORT_DIR, ensure_modeling_directories


def write_calibration_report(applied: bool = False, notes: str = "Calibration skipped for this first modeling pass.") -> str:
    ensure_modeling_directories()
    lines = [
        "# Calibration Report",
        "",
        f"- Calibration applied: {'yes' if applied else 'no'}",
        f"- Notes: {notes}",
        "",
        "Models are evaluated with log loss and Brier score. Calibration can be added after reviewing validation/test probability quality.",
    ]
    path = MODELING_REPORT_DIR / "calibration_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
