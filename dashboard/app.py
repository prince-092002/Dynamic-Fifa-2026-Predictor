"""Dynamic FIFA 2026 Tournament Outcome Predictor — analytics dashboard entry page."""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from data.loaders import load_json, missing, pct  # noqa: E402

st.set_page_config(page_title="FIFA 2026 Predictor — Overview", page_icon="⚽", layout="wide")

st.title("⚽ Dynamic FIFA 2026 Tournament Outcome Predictor")
st.caption("Live machine-learning forecasts: real results + XGBoost matchup probabilities + Monte Carlo simulation. Independent analytics project — not affiliated with or endorsed by FIFA.")

overview = load_json("latest_overview.json")
if not overview:
    missing("Current overview unavailable. Run the live forecast pipeline, then `python main.py build-public-exports`.")
    st.stop()

phase = str(overview.get("current_phase", "unknown")).replace("_", " ").title()
left, mid, right, far = st.columns(4)
left.metric("Current phase", phase)
mid.metric("Completed matches", overview.get("completed_matches", "—"))
right.metric("Teams still alive", overview.get("teams_alive", "—"))
far.metric("Teams eliminated", overview.get("teams_eliminated", "—"))

left, mid, right, far = st.columns(4)
left.metric("Title favorite", overview.get("top_champion") or "—", pct(overview.get("top_champion_probability")))
mid.metric("Most likely final", overview.get("top_finalist_pair") or "—", pct(overview.get("top_finalist_pair_probability")))
right.metric("Unresolved matchups", overview.get("known_unresolved_matchups", "—"))
far.metric("Simulations (latest run)", f"{overview.get('simulations', 0):,}" if overview.get("simulations") else "—")

st.divider()
left, mid, right, far = st.columns(4)
left.metric("Forecast mode", str(overview.get("forecast_mode", "—")).replace("_", " "))
mid.metric("Provider", overview.get("provider", "—"))
age = overview.get("data_age_minutes")
right.metric("Data freshness", f"{overview.get('data_source_mode', '—')}", f"{age:.0f} min old" if age is not None else None, delta_color="off")
validation = overview.get("live_forecast_validation", "—")
far.metric("Live validation", str(validation), "✅" if validation == "pass" else None, delta_color="off")

st.divider()
st.subheader("How the system works")
st.markdown(
    """
```text
Live match results (football-data.org)
        → tournament state (completed results locked, never re-simulated)
        → leakage-safe feature generation for resolved matchups
        → XGBoost matchup probabilities
        → Monte Carlo tournament simulations
        → champion / finalist forecasts
        → validation + audit manifest
```
Use the sidebar to explore the live bracket, forecasts, matchup predictions, the team explorer,
forecast evolution, methodology, system health, and the technical audit trail.
"""
)
st.caption(f"Latest run: {overview.get('run_id', 'unknown')} · model: {overview.get('selected_model', 'unknown')} · seed: {overview.get('seed', '—')} · Predictions are probabilistic estimates, not guarantees.")
