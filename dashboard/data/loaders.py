"""Cached, fault-tolerant readers for dashboard inputs.

The dashboard only reads saved outputs (public_data/ and outputs/); it never
calls external APIs and never reruns the ML pipeline.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_DATA = PROJECT_ROOT / "public_data"
LIVE_STATE = PROJECT_ROOT / "outputs" / "live_state"

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


@st.cache_data(ttl=60)
def load_json(name: str) -> dict:
    path = PUBLIC_DATA / name
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        return {}


@st.cache_data(ttl=60)
def load_live_csv(name: str) -> pd.DataFrame:
    path = LIVE_STATE / name
    try:
        return pd.read_csv(path) if path.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def pct(value, digits: int = 2) -> str:
    return f"{float(value) * 100:.{digits}f}%" if value is not None and pd.notna(value) else "—"


def missing(message: str) -> None:
    st.info(message)


def source_label(raw: str) -> str:
    return SOURCE_LABELS.get(str(raw), str(raw))
