"""Forecast evolution: probabilities over recorded runs and source progression."""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.loaders import load_json, missing  # noqa: E402
from theme import header, apply_plotly, flag_html  # noqa: E402
header("Forecast Evolution", "How the odds moved", "Championship and finalist probabilities across recorded forecast runs, and the probability-source mix.", icon_name="chart")

history = load_json("forecast_history.json")
champion_history = pd.DataFrame(history.get("champion", []))
if champion_history.empty or champion_history["run_id"].nunique() < 2:
    missing("Forecast history will appear after additional recorded forecast runs.")
else:
    top_teams = champion_history.groupby("team")["champion_probability"].max().nlargest(8).index
    team_codes = {team["team"]: team.get("code") for team in load_json("teams.json").get("teams", [])}
    chips = "".join(
        f'<div class="sk-team-chip">{flag_html(team_codes.get(team), team, 26)}'
        f'<div class="meta"><div class="team">{team}</div></div></div>'
        for team in top_teams
    )
    st.markdown(f'<div class="sk-team-strip">{chips}</div>', unsafe_allow_html=True)
    frame = champion_history[champion_history["team"].isin(top_teams)]
    figure = px.line(frame, x="timestamp", y="champion_probability", color="team", markers=True, title="Champion probability over recorded forecast runs")
    figure.update_layout(yaxis_tickformat=".0%", height=420)
    st.plotly_chart(apply_plotly(figure), width="stretch")
    finalist_history = pd.DataFrame(history.get("finalist", []))
    if not finalist_history.empty and finalist_history["run_id"].nunique() >= 2:
        frame = finalist_history[finalist_history["team"].isin(top_teams)]
        figure = px.line(frame, x="timestamp", y="reach_final_probability", color="team", markers=True, title="Reach-final probability over recorded runs")
        figure.update_layout(yaxis_tickformat=".0%", height=380)
        st.plotly_chart(apply_plotly(figure), width="stretch")

st.divider()
st.subheader("Probability-source progression")
source_history = load_json("probability_source_history.json")
runs = pd.DataFrame(source_history.get("runs", []))
if runs.empty:
    missing("Probability-source history unavailable.")
else:
    source_columns = [c for c in ["completed_result", "live_model_exact", "live_model_reversed", "model_exact", "model_reversed", "elo_fallback", "neutral_fallback"] if c in runs.columns]
    label_map = {"completed_result": "Completed results", "live_model_exact": "Live XGBoost", "live_model_reversed": "Live XGBoost (reversed)", "model_exact": "Pre-tournament model", "model_reversed": "Pre-tournament model (reversed)", "elo_fallback": "Elo fallback", "neutral_fallback": "Neutral fallback"}
    melted = runs.melt(id_vars=["timestamp"], value_vars=source_columns, var_name="source", value_name="decisions")
    melted["source"] = melted["source"].map(label_map)
    figure = px.area(melted, x="timestamp", y="decisions", color="source", title="Simulation decisions by probability source (per recorded run)", groupnorm="fraction")
    figure.update_layout(yaxis_tickformat=".0%", height=420)
    st.plotly_chart(apply_plotly(figure), width="stretch")
    st.info("Probability-source usage measures which probability engine supplied simulation decisions. It is not an accuracy metric.")
    st.dataframe(runs[["timestamp", "tournament_phase", "simulation_count", "known_remaining_matchups", "model_driven_pct", "fallback_pct"]], width="stretch", hide_index=True)

st.divider()
st.subheader("Tournament phase transitions")
transition = load_json("latest_run_manifest.json").get("phase_transition") or {}
if transition:
    st.markdown(f"- Previous phase: **{transition.get('previous_phase') or 'first recorded run'}**")
    st.markdown(f"- Current phase: **{transition.get('current_phase')}**")
    st.markdown(f"- Phase changed this run: **{transition.get('phase_changed')}**")
    st.markdown(f"- Newly completed matches since last run: **{transition.get('newly_completed_matches')}**")
    st.markdown(f"- Newly resolved matchups: **{transition.get('newly_resolved_matchups')}**")
else:
    missing("Phase transition data unavailable.")
