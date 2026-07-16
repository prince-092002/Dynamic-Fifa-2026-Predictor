"""Technical audit: latest run manifest and public artifact downloads."""

import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.loaders import PUBLIC_DATA, load_json, missing, source_label  # noqa: E402
from theme import header, flag_html  # noqa: E402
header("Technical Audit", "Run manifest · reproducibility", "The complete audit manifest of the latest forecast run, with public-artifact downloads.", icon_name="lock")

manifest = load_json("latest_run_manifest.json")
if not manifest:
    missing("Run manifest unavailable. Run the live forecast pipeline first.")
    st.stop()

left, mid, right = st.columns(3)
left.metric("Run ID", str(manifest.get("run_id", "—"))[:28])
mid.metric("Run started", str(manifest.get("run_started_at", "—"))[:19].replace("T", " "))
right.metric("Run completed", str(manifest.get("run_completed_at", "—"))[:19].replace("T", " "))
left, mid, right, far = st.columns(4)
left.metric("Simulations", f"{manifest.get('simulation_count', 0):,}")
mid.metric("Seed", manifest.get("seed", "—"))
right.metric("Model", manifest.get("selected_model", "—"))
far.metric("Provider", manifest.get("provider", "—"))
left, mid, right, far = st.columns(4)
left.metric("Live validation", manifest.get("live_forecast_validation", "—"))
mid.metric("Broader validation", manifest.get("broader_refresh_validation", "—"))
right.metric("Data source mode", manifest.get("data_source_mode", "—"))
far.metric("Provider data age", f"{manifest.get('provider_data_age_minutes', '—')} min")

st.subheader("Probability-source counts (latest run)")
sources = manifest.get("probability_sources") or {}
if sources:
    frame = pd.DataFrame([{"Source": key, "Label": source_label(key), "Decisions": value} for key, value in sources.items()]).sort_values("Decisions", ascending=False)
    st.dataframe(frame, width="stretch", hide_index=True)
else:
    missing("No probability-source counts in the manifest.")

st.subheader("Top results (latest run)")
team_codes = {team["team"]: team.get("code") for team in load_json("teams.json").get("teams", [])}
top_champion = manifest.get("top_champion", "—")
st.markdown(
    f'<div class="sk-team-row">{flag_html(team_codes.get(top_champion), top_champion, 28)}'
    f'<span class="name">Top champion: <b>{top_champion}</b></span></div>',
    unsafe_allow_html=True,
)
pair = str(manifest.get("top_finalist_pair", "—"))
pair_teams = pair.split(" vs ") if " vs " in pair else []
pair_flags = "".join(flag_html(team_codes.get(team), team, 24) for team in pair_teams)
st.markdown(
    f'<div class="sk-team-row">{pair_flags}<span class="name">Top finalist pair: <b>{pair}</b></span></div>',
    unsafe_allow_html=True,
)
transition = manifest.get("phase_transition") or {}
st.markdown(f"- Phase: **{transition.get('previous_phase') or '—'} → {transition.get('current_phase') or '—'}** (changed: {transition.get('phase_changed', '—')})")

st.subheader("Download public artifacts")
downloadables = [
    "champion_forecast.json",
    "finalist_forecast.json",
    "finalist_pairs.json",
    "matchup_predictions.json",
    "latest_run_manifest.json",
    "probability_source_history.json",
    "system_health.json",
]
columns = st.columns(3)
for index, name in enumerate(downloadables):
    path = PUBLIC_DATA / name
    if path.exists():
        columns[index % 3].download_button(f"⬇ {name}", data=path.read_text(encoding="utf-8"), file_name=name, mime="application/json")
st.caption("All downloads are public-safe exports. Raw provider payloads, credentials, and local paths are never exposed.")

with st.expander("Full run manifest (JSON)"):
    st.json(manifest)
