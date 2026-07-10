"""Commit safety for automated matchday publication.

Defines exactly which generated files automation may commit, classifies every
changed file in the working tree, and refuses to proceed when anything
unexpected changed or when staged content fails secret/path scans.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
from pathlib import Path

from src.config import PROJECT_ROOT
from src.public_export.export_validation import _load_secret_values

# Files automation is allowed to commit after a verified refresh.
COMMIT_ALLOWLIST = [
    "public_data/*.json",
    "outputs/live_state/champion_probability_history.csv",
    "outputs/live_state/finalist_probability_history.csv",
    "outputs/live_state/finalist_pair_probability_history.csv",
    "outputs/live_state/probability_source_history.csv",
    "outputs/live_state/latest_live_run_manifest.json",
    "outputs/live_state/tournament_phase_transition.json",
    "outputs/live_state/live_provider_freshness.json",
    "outputs/live_state/live_forecast_summary.json",
    "outputs/live_state/live_forecast_quality_gate.json",
    "outputs/live_state/live_champion_probabilities.csv",
    "outputs/live_state/team_reach_final_probabilities.csv",
    "outputs/live_state/finalist_pair_probabilities.csv",
    "outputs/live_state/live_knockout_match_predictions.csv",
    "outputs/live_state/remaining_known_knockout_matchups.csv",
    "outputs/live_state/football_data_org_*_normalized.csv",
    "outputs/live_state/merged_bracket_state.csv",
    "outputs/reports/portfolio/latest_portfolio_refresh_manifest.json",
]

# Generated locations where changes are expected during a refresh but are
# NOT committed by automation (they regenerate deterministically or are local).
EXPECTED_VOLATILE = [
    "data/*",
    "outputs/*",
    "public_data/*",
    ".streamlit/*",
]

# Never allowed in an automated commit under any circumstances.
FORBIDDEN = [
    ".env",
    "*.env",
    "kaggle.json",
    "**/provider_snapshots/*",
    "outputs/live_state/api_football_live_*.json",
    "website/node_modules/*",
    "website/.next/*",
]

PRIVATE_PATH_PATTERN = re.compile(r"[A-Za-z]:\\\\Users|[A-Za-z]:\\Users|/Users/[a-z]|/home/[a-z]")


def _matches(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    return any(fnmatch.fnmatch(normalized, pattern) for pattern in patterns)


def is_allowlisted(path: str) -> bool:
    return _matches(path, COMMIT_ALLOWLIST) and not _matches(path, FORBIDDEN)


def classify_changed_files(changed_paths: list[str]) -> dict:
    """Split changed paths into commit / tolerate / unexpected buckets.

    FORBIDDEN files are never staged, but their routine regeneration (e.g.
    provider snapshots rewritten on every fetch) does not block automation —
    they are tolerated-and-never-committed. Only changes outside all known
    generated locations (source, config, docs, workflows) stop automation.
    """
    to_commit, tolerated, unexpected = [], [], []
    for path in changed_paths:
        normalized = path.replace("\\", "/")
        if _matches(normalized, FORBIDDEN):
            tolerated.append(normalized)
        elif is_allowlisted(normalized):
            to_commit.append(normalized)
        elif _matches(normalized, EXPECTED_VOLATILE):
            tolerated.append(normalized)
        else:
            unexpected.append(normalized)
    return {"to_commit": sorted(to_commit), "tolerated": sorted(tolerated), "unexpected": sorted(unexpected)}


def scan_files_for_secrets(paths: list[str], base_dir: Path | None = None, secrets: list[str] | None = None) -> dict:
    """Scan file contents for secret values and private local paths.

    Never returns or prints secret values — only file names that hit.
    """
    base = Path(base_dir) if base_dir else PROJECT_ROOT
    secret_values = secrets if secrets is not None else _load_secret_values()
    secret_hits, path_hits = [], []
    for name in paths:
        file_path = base / name
        if not file_path.is_file():
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if any(value in text for value in secret_values):
            secret_hits.append(name)
        if PRIVATE_PATH_PATTERN.search(text):
            path_hits.append(name)
    return {"secret_hits": secret_hits, "private_path_hits": path_hits, "clean": not secret_hits and not path_hits}


def git_changed_files(repo_dir: Path | None = None) -> list[str]:
    """Modified + untracked files from git status (porcelain)."""
    base = Path(repo_dir) if repo_dir else PROJECT_ROOT
    result = subprocess.run(["git", "status", "--porcelain"], cwd=base, capture_output=True, text=True)
    changed = []
    for line in result.stdout.splitlines():
        if len(line) > 3:
            path = line[3:].strip().strip('"')
            if line[:2].strip() == "R" and " -> " in path:
                path = path.split(" -> ", 1)[1]
            changed.append(path)
    return changed


def evaluate_commit_safety(repo_dir: Path | None = None) -> dict:
    """Full pre-commit gate for automation: classify, scan, decide."""
    base = Path(repo_dir) if repo_dir else PROJECT_ROOT
    changed = git_changed_files(base)
    classified = classify_changed_files(changed)
    scan = scan_files_for_secrets(classified["to_commit"], base_dir=base)
    safe = not classified["unexpected"] and scan["clean"] and bool(classified["to_commit"])
    reason = "ok"
    if classified["unexpected"]:
        reason = f"unexpected files changed: {classified['unexpected'][:10]}"
    elif not scan["clean"]:
        reason = f"scan failure: secrets={scan['secret_hits']}, private_paths={scan['private_path_hits']}"
    elif not classified["to_commit"]:
        reason = "no allowlisted files changed"
    return {"safe_to_commit": safe, "reason": reason, **classified, "scan": scan, "total_changed": len(changed)}
