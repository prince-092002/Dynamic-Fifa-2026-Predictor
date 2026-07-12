"""Current XGBoost matchup predictions for known unresolved knockout matches."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.loaders import load_json, missing, pct  # noqa: E402
from theme import header, flag_html  # noqa: E402
header("Match Predictor", "Live matchup intelligence", "Current XGBoost predictions for every known unresolved knockout matchup.", icon_name="bolt")

payload = load_json("matchup_predictions.json")
matchups = payload.get("matchups", [])
if not matchups:
    missing("No known unresolved matchups to predict right now (or exports not built yet).")
    st.stop()

team_codes = {team["team"]: team.get("code") for team in load_json("teams.json").get("teams", [])}


def team_badge(name: str | None) -> str:
    if not name:
        return '<span class="sk-team-row"><span class="name">—</span></span>'
    return f'<span class="sk-team-row">{flag_html(team_codes.get(name), name, 28)}<span class="name">{name}</span></span>'

for match in matchups:
    with st.container(border=True):
        left, mid, right = st.columns([3, 2, 2])
        with left:
            st.markdown(
                f'<div class="sk-match-title" style="justify-content:flex-start">{team_badge(match["team_a"])}'
                f'<span class="sk-match-vs">vs</span>{team_badge(match["team_b"])}</div>',
                unsafe_allow_html=True,
            )
            st.caption(f"{match.get('stage')} · predicted {str(match.get('generated_at', ''))[:16].replace('T', ' ')} UTC")
        with mid:
            if match.get("prediction_status") == "predicted":
                st.metric(match["team_a"], pct(match.get("team_a_advance_probability")), "advance probability", delta_color="off")
                st.metric(match["team_b"], pct(match.get("team_b_advance_probability")), "advance probability", delta_color="off")
            else:
                st.warning(f"Prediction status: {match.get('prediction_status')} — the simulator uses Elo fallback for this matchup.")
        with right:
            if match.get("prediction_status") == "predicted":
                favorite = match.get("favorite")
                st.markdown(f'**Favorite:** {team_badge(favorite)}', unsafe_allow_html=True)
                st.markdown(f"**Source:** {match.get('source_label')}")
                st.markdown(f"**Model:** {match.get('model')}")
        with st.expander("Technical detail (raw probabilities and source)"):
            st.json({key: match.get(key) for key in ["prob_team_a_win", "prob_draw", "prob_team_a_loss", "probability_source", "prediction_status", "model"]})

st.caption("Draw probability converts to advancement as: advance = win + 0.5 × draw. Raw source labels stay visible above.")
