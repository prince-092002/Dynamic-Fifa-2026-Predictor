"""Champion and finalist forecasts from the latest Monte Carlo run."""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.loaders import load_json, missing  # noqa: E402

st.set_page_config(page_title="Champion Forecast", page_icon="👑", layout="wide")
st.title("👑 Champion & Finalist Forecast")

champion = load_json("champion_forecast.json")
finalist = load_json("finalist_forecast.json")
pairs = load_json("finalist_pairs.json")
if not champion.get("entries"):
    missing("Current champion forecast unavailable. Run the live forecast pipeline first.")
    st.stop()

simulations = champion.get("simulations")
generated = (champion.get("_meta") or {}).get("generated_at", "")
st.caption(f"Current live forecast · {simulations:,} simulations · generated {generated}" if simulations else f"generated {generated}")

left, right = st.columns(2)
with left:
    frame = pd.DataFrame(champion["entries"]).sort_values("champion_probability")
    figure = px.bar(frame, x="champion_probability", y="team", orientation="h", title="Championship probability (current live forecast)", labels={"champion_probability": "Probability", "team": ""}, text=frame["champion_probability"].map(lambda v: f"{v:.1%}"))
    figure.update_layout(xaxis_tickformat=".0%", showlegend=False, height=420)
    st.plotly_chart(figure, use_container_width=True)
with right:
    if finalist.get("entries"):
        frame = pd.DataFrame(finalist["entries"]).sort_values("reach_final_probability")
        figure = px.bar(frame, x="reach_final_probability", y="team", orientation="h", title="Reach-the-final probability", labels={"reach_final_probability": "Probability", "team": ""}, text=frame["reach_final_probability"].map(lambda v: f"{v:.1%}"))
        figure.update_layout(xaxis_tickformat=".0%", showlegend=False, height=420)
        st.plotly_chart(figure, use_container_width=True)
    else:
        missing("Finalist forecast unavailable.")

st.subheader("Most likely finals")
if pairs.get("entries"):
    frame = pd.DataFrame(pairs["entries"]).nlargest(10, "probability")
    frame["final"] = frame["finalist_pair_key"]
    figure = px.bar(frame.sort_values("probability"), x="probability", y="final", orientation="h", labels={"probability": "Probability", "final": ""}, text=frame.sort_values("probability")["probability"].map(lambda v: f"{v:.1%}"))
    figure.update_layout(xaxis_tickformat=".0%", height=380)
    st.plotly_chart(figure, use_container_width=True)
else:
    missing("Finalist pair forecast unavailable.")
st.caption("Highest estimated probabilities from the current live forecast — probabilistic estimates, not guarantees.")
