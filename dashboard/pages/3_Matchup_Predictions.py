"""Current XGBoost matchup predictions for known unresolved knockout matches."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.loaders import load_json, missing, pct  # noqa: E402

st.set_page_config(page_title="Matchup Predictions", page_icon="🎯", layout="wide")
st.title("🎯 Matchup Predictions")

payload = load_json("matchup_predictions.json")
matchups = payload.get("matchups", [])
if not matchups:
    missing("No known unresolved matchups to predict right now (or exports not built yet).")
    st.stop()

for match in matchups:
    with st.container(border=True):
        left, mid, right = st.columns([3, 2, 2])
        with left:
            st.markdown(f"### {match['team_a']} vs {match['team_b']}")
            st.caption(f"{match.get('stage')} · predicted {str(match.get('generated_at', ''))[:16].replace('T', ' ')} UTC")
        with mid:
            if match.get("prediction_status") == "predicted":
                st.metric(match["team_a"], pct(match.get("team_a_advance_probability")), "advance probability", delta_color="off")
                st.metric(match["team_b"], pct(match.get("team_b_advance_probability")), "advance probability", delta_color="off")
            else:
                st.warning(f"Prediction status: {match.get('prediction_status')} — the simulator uses Elo fallback for this matchup.")
        with right:
            if match.get("prediction_status") == "predicted":
                st.markdown(f"**Favorite:** {match.get('favorite')}")
                st.markdown(f"**Source:** {match.get('source_label')}")
                st.markdown(f"**Model:** {match.get('model')}")
        with st.expander("Technical detail (raw probabilities and source)"):
            st.json({key: match.get(key) for key in ["prob_team_a_win", "prob_draw", "prob_team_a_loss", "probability_source", "prediction_status", "model"]})

st.caption("Draw probability converts to advancement as: advance = win + 0.5 × draw. Raw source labels stay visible above.")
