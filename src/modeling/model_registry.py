"""Save model registry and selected model artifact."""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone

from src.modeling.model_config import MODEL_DIR, ensure_modeling_directories


def write_model_registry(entries: list[dict], selected_model_name: str) -> dict:
    ensure_modeling_directories()
    timestamp = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for entry in entries:
        entry["selected_model"] = entry.get("model_name") == selected_model_name
        entry.setdefault("training_timestamp", timestamp)
    registry = {"created_at": timestamp, "models": entries}
    path = MODEL_DIR / "model_registry.json"
    path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
    selected = next((entry for entry in entries if entry.get("model_name") == selected_model_name), None)
    selected_path = MODEL_DIR / "selected_model.joblib"
    if selected and selected.get("model_file_path"):
        shutil.copy2(selected["model_file_path"], selected_path)
    return {"registry": str(path), "selected_model": str(selected_path)}
