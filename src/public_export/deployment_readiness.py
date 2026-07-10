"""Local deployment-readiness checks.

Reports readiness states only; never claims an actual platform deployment
happened. Website build and Streamlit startup are verified by their own
commands and reflected here through their artifacts.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

from src.config import PROJECT_ROOT
from src.public_export.build_public_exports import PUBLIC_DATA_DIR
from src.public_export.export_validation import _load_secret_values, validate_dashboard, validate_public_exports
from src.utils.dates import now_utc_iso

REPORT_DIR = PROJECT_ROOT / "outputs" / "reports" / "public_export"


def validate_deployment_readiness() -> dict:
    checks: dict[str, str] = {}
    exports = validate_public_exports()
    checks["public_data_ready"] = "yes" if exports["status"] == "pass" else "no"
    dashboard = validate_dashboard()
    checks["dashboard_data_ready"] = "yes" if dashboard["status"] == "pass" else "no"
    python_dependencies = ["pandas", "numpy", "xgboost", "streamlit", "plotly", "joblib", "requests"]
    missing = [name for name in python_dependencies if importlib.util.find_spec(name) is None]
    checks["python_dependencies_ready"] = "yes" if not missing else f"no (missing: {missing})"
    dashboard_entry = PROJECT_ROOT / "dashboard" / "app.py"
    checks["streamlit_startup_ready"] = "yes" if dashboard_entry.exists() else "no (dashboard/app.py missing)"
    website = PROJECT_ROOT / "website"
    package_json = website / "package.json"
    if package_json.exists():
        package = json.loads(package_json.read_text(encoding="utf-8"))
        has_build = "build" in package.get("scripts", {})
        build_marker = website / ".next" / "BUILD_ID"
        checks["deployment_configuration_ready"] = "yes" if has_build else "no (no build script)"
        checks["local_build_ready"] = "yes" if build_marker.exists() else "not_verified (run npm run build in website/)"
    else:
        checks["deployment_configuration_ready"] = "no (website/package.json missing)"
        checks["local_build_ready"] = "no"
    secrets = _load_secret_values()
    hits = []
    scan_roots = ["public_data", "website/app", "website/components", "website/lib", "dashboard", "README.md", ".github"]
    for root in scan_roots:
        base = PROJECT_ROOT / root
        candidates = [base] if base.is_file() else (base.rglob("*") if base.exists() else [])
        for path in candidates:
            if path.is_file() and path.suffix.lower() in {".json", ".md", ".py", ".ts", ".tsx", ".js", ".css", ".yml", ".yaml", ".toml"}:
                text = path.read_text(encoding="utf-8", errors="ignore")
                if any(secret in text for secret in secrets):
                    hits.append(str(path.relative_to(PROJECT_ROOT)))
    checks["secret_scan_ready"] = "yes (0 hits)" if not hits else f"no ({len(hits)} files)"
    absolute_paths = []
    for path in PUBLIC_DATA_DIR.glob("*.json"):
        if re.search(r"[A-Za-z]:\\\\|[A-Za-z]:/Users", path.read_text(encoding="utf-8", errors="ignore")):
            absolute_paths.append(path.name)
    checks["relative_paths_safe"] = "yes" if not absolute_paths else f"no ({absolute_paths})"
    status = "ready" if all(value.startswith("yes") for value in checks.values()) else "not_ready"
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["# Deployment Readiness", "", f"- Generated: {now_utc_iso()}", f"- Overall: {status}", ""]
    lines += [f"- {key}: {value}" for key, value in checks.items()]
    lines += ["", "Actual Vercel/Streamlit Cloud deployment still requires connecting the GitHub repository on those platforms (documented in README.md). This report never claims a platform deployment occurred."]
    report_path = REPORT_DIR / "deployment_readiness.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return {"status": status, "checks": checks, "report": str(report_path)}
