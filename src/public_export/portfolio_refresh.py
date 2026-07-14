"""Unified matchday portfolio refresh: forecast -> validate -> publish -> manifest.

Orchestrates the existing verified components (nothing is reimplemented):
the matchday update pipeline already refreshes the provider, locks completed
results, predicts newly resolved matchups with XGBoost, runs Monte Carlo,
validates, appends history, and fail-closed-publishes public exports. This
module adds the surrounding publication gates and a machine-readable manifest.
"""

from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path

from src.config import PROJECT_ROOT
from src.utils.dates import now_utc_iso

PORTFOLIO_REPORT_DIR = PROJECT_ROOT / "outputs" / "reports" / "portfolio"
MANIFEST_PATH = PORTFOLIO_REPORT_DIR / "latest_portfolio_refresh_manifest.json"


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


def _git_commit() -> str | None:
    try:
        result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=PROJECT_ROOT, capture_output=True, text=True)
        return result.stdout.strip() or None
    except Exception:
        return None


def _snapshot_state() -> dict:
    gate = _read_json(PROJECT_ROOT / "outputs" / "live_state" / "live_forecast_quality_gate.json")
    overview = _read_json(PROJECT_ROOT / "public_data" / "latest_overview.json")
    return {
        "phase": gate.get("current_phase"),
        "completed_matches": gate.get("completed_result_count"),
        "teams_alive": overview.get("teams_alive"),
        "teams_eliminated": overview.get("teams_eliminated"),
    }


def run_portfolio_refresh(n_simulations: int = 10000, no_retrain: bool = True, allow_fallback_forecast: bool = False, dry_run: bool = False) -> dict:
    """One-command matchday refresh with fail-closed publication gating."""
    from src.prediction_history.snapshot import archive_current_forecast
    from src.public_export.deployment_readiness import validate_deployment_readiness
    from src.public_export.export_validation import validate_dashboard, validate_public_exports
    from src.update.update_runner import run_update

    PORTFOLIO_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    refresh_id = f"refresh-{now_utc_iso().replace(':', '').replace('+0000', 'Z')}-{uuid.uuid4().hex[:6]}"
    started_at = now_utc_iso()
    commit_before = _git_commit()
    state_before = _snapshot_state()
    warnings: list[str] = []

    # Preserve the currently-published forecast as a history snapshot BEFORE the update can
    # overwrite it (idempotent: a no-op if that state is already archived). Archival never
    # blocks the refresh.
    pre_archive = {"archived": False, "reason": "not_run"}
    try:
        pre_archive = archive_current_forecast(
            provenance={"refresh_id": refresh_id, "git_commit": commit_before, "stage": "pre_refresh"},
            dry_run=dry_run)
    except Exception as exc:  # pragma: no cover - defensive
        warnings.append(f"pre-refresh snapshot archival failed: {str(exc)[:120]}")

    update_result = run_update(mode="matchday", force=False, run_live_forecast=True, n_simulations=n_simulations, no_retrain=no_retrain, allow_fallback_forecast=allow_fallback_forecast)
    live = update_result.get("live_forecast") or {}
    publication = live.get("public_export_publication") or {}
    if update_result.get("validation_status") != "passed":
        warnings.append(f"broader refresh validation: {update_result.get('validation_status')}")
    for warning in update_result.get("warnings", []) or []:
        warnings.append(str(warning)[:180])

    export_validation = validate_public_exports()
    dashboard_validation = validate_dashboard()
    readiness = validate_deployment_readiness()
    state_after = _snapshot_state()
    transition = _read_json(PROJECT_ROOT / "outputs" / "live_state" / "tournament_phase_transition.json")
    freshness = _read_json(PROJECT_ROOT / "outputs" / "live_state" / "live_provider_freshness.json")

    live_ok = live.get("status") == "success" and live.get("forecast_ran") is True
    publication_ok = publication.get("published") is True
    eligible = bool(live_ok and publication_ok and export_validation["status"] == "pass" and dashboard_validation["status"] == "pass")

    # Archive the newly-published forecast so the latest production forecast is captured in
    # the audit trail (idempotent; only when the refresh actually published a valid forecast).
    post_archive = {"archived": False, "reason": "not_eligible"}
    if eligible:
        try:
            post_archive = archive_current_forecast(
                provenance={"refresh_id": refresh_id, "git_commit": _git_commit(), "stage": "post_refresh"},
                dry_run=dry_run)
        except Exception as exc:  # pragma: no cover - defensive
            warnings.append(f"post-refresh snapshot archival failed: {str(exc)[:120]}")

    manifest = {
        "refresh_id": refresh_id,
        "started_at": started_at,
        "completed_at": now_utc_iso(),
        "git_commit_before_refresh": commit_before,
        "phase_before": state_before.get("phase"),
        "phase_after": state_after.get("phase"),
        "provider": freshness.get("provider"),
        "provider_mode": freshness.get("data_source_mode"),
        "completed_matches_before": state_before.get("completed_matches"),
        "completed_matches_after": state_after.get("completed_matches"),
        "teams_alive": state_after.get("teams_alive"),
        "teams_eliminated": state_after.get("teams_eliminated"),
        "newly_completed_matches": transition.get("newly_completed_matches"),
        "newly_predicted_matchups": live.get("live_matchups_predicted"),
        "simulation_count": n_simulations,
        "live_forecast_status": live.get("status", "not_run"),
        "live_forecast_validation": "pass" if live_ok else str(live.get("status", "not_run")),
        "public_export_publication": publication.get("status", "not_run"),
        "public_export_validation": export_validation["status"],
        "dashboard_validation": dashboard_validation["status"],
        "deployment_readiness": readiness["status"],
        "changed_public_files": publication.get("changed_files", []),
        "warnings": warnings,
        "eligible_for_publication": eligible,
        "prediction_history": {"pre_refresh": pre_archive, "post_refresh": post_archive, "dry_run": dry_run},
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
