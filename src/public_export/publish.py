"""Fail-closed publication of public exports.

Exports are built into a staging directory and validated there. Only a fully
valid staged set replaces public_data/; on any validation failure the previous
known-good public dataset is left untouched and the rejection is reported.
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path

from src.public_export.build_public_exports import PUBLIC_DATA_DIR, build_public_exports
from src.public_export.export_validation import validate_public_exports


def _hash_directory(directory: Path) -> dict[str, str]:
    hashes = {}
    if directory.exists():
        for path in sorted(directory.glob("*.json")):
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def safe_publish_public_exports() -> dict:
    """Build exports in staging, validate, and promote only when valid.

    Returns published/rejected status, the staged validation result, and the
    list of public files whose content actually changed.
    """
    before = _hash_directory(PUBLIC_DATA_DIR)
    staging = Path(tempfile.mkdtemp(prefix="public_export_stage_"))
    try:
        build_result = build_public_exports(target_dir=staging)
        validation = validate_public_exports(directory=staging, write_report=False)
        if validation["status"] != "pass":
            failed_checks = [row["check"] for row in validation.get("rows", []) if row["status"] == "fail"]
            return {
                "status": "rejected",
                "published": False,
                "validation_status": validation["status"],
                "failed_checks": failed_checks,
                "changed_files": [],
                "written": build_result["written"],
                "message": "Staged exports failed validation; previous known-good public_data was preserved.",
            }
        PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)
        for staged in sorted(staging.glob("*.json")):
            shutil.copy2(staged, PUBLIC_DATA_DIR / staged.name)
        after = _hash_directory(PUBLIC_DATA_DIR)
        changed = [name for name in after if before.get(name) != after[name]]
        final_validation = validate_public_exports()  # writes the standard report against the live directory
        return {
            "status": "published",
            "published": True,
            "validation_status": final_validation["status"],
            "failed_checks": [],
            "changed_files": changed,
            "written": build_result["written"],
            "message": f"{len(changed)} public files changed.",
        }
    finally:
        shutil.rmtree(staging, ignore_errors=True)
