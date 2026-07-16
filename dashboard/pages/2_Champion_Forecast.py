"""Champion and finalist forecasts from the latest Monte Carlo run."""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.loaders import load_json, missing  # noqa: E402
from theme import header, apply_plotly, flag_html  # noqa: E402

overview = load_json("latest_overview.json")
is_final = overview.get("current_phase") == "final"
header(
    "The Road to the Title",
    "Final prediction" if is_final else "Tournament forecast",
    "Direct XGBoost probabilities of winning the confirmed final and championship." if is_final else "Championship and finalist probabilities from the latest live Monte Carlo forecast.",
    icon_name="trophy",
)

champion = load_json("champion_forecast.json")
finalist = load_json("finalist_forecast.json")
pairs = load_json("finalist_pairs.json")
if not champion.get("entries"):
    missing("Current champion forecast unavailable. Run the live forecast pipeline first.")
    st.stop()

simulations = champion.get("simulations")
generated = (champion.get("_meta") or {}).get("generated_at", "")
basis = champion.get("entries", [{}])[0].get("probability_basis")
generated_label = generated.replace("T", " ").replace("+00:00", " UTC")
caption = f"Current live forecast · generated {generated_label}"
if is_final:
    caption += f" · canonical source: {(basis or 'direct final matchup probability').replace('_', ' ')}"
elif simulations:
    caption += f" · {simulations:,} simulations"
st.caption(caption)

team_codes = {team["team"]: team.get("code") for team in load_json("teams.json").get("teams", [])}
top_entries = sorted(champion["entries"], key=lambda entry: -entry["champion_probability"])[:6]
chips = "".join(
    f'<div class="sk-team-chip">{flag_html(team_codes.get(entry["team"]), entry["team"], 30)}'
    f'<div class="meta"><div class="team">{entry["team"]}</div>'
    f'<div class="prob">{entry["champion_probability"]:.1%} champion</div></div></div>'
    for entry in top_entries
)
st.markdown(f'<div class="sk-team-strip">{chips}</div>', unsafe_allow_html=True)

left, right = st.columns(2)
with left:
    frame = pd.DataFrame(champion["entries"]).sort_values("champion_probability")
    figure = px.bar(frame, x="champion_probability", y="team", orientation="h", title="Championship probability (current live forecast)", labels={"champion_probability": "Probability", "team": ""}, text=frame["champion_probability"].map(lambda v: f"{v:.1%}"))
    figure.update_layout(xaxis_tickformat=".0%", showlegend=False, height=420)
    st.plotly_chart(apply_plotly(figure), width="stretch")
with right:
    if is_final and pairs.get("entries"):
        final = max(pairs["entries"], key=lambda entry: entry.get("probability", 0))
        st.markdown("#### Confirmed finalists")
        for team in [final["finalist_team_1"], final["finalist_team_2"]]:
            st.markdown(
                f'<div class="sk-team-chip">{flag_html(team_codes.get(team), team, 30)}'
                f'<div class="meta"><div class="team">{team}</div><div class="prob">Confirmed finalist</div></div></div>',
                unsafe_allow_html=True,
            )
    elif finalist.get("entries"):
        frame = pd.DataFrame(finalist["entries"]).sort_values("reach_final_probability")
        figure = px.bar(frame, x="reach_final_probability", y="team", orientation="h", title="Reach-the-final probability", labels={"reach_final_probability": "Probability", "team": ""}, text=frame["reach_final_probability"].map(lambda v: f"{v:.1%}"))
        figure.update_layout(xaxis_tickformat=".0%", showlegend=False, height=420)
        st.plotly_chart(apply_plotly(figure), width="stretch")
    else:
        missing("Finalist forecast unavailable.")

st.subheader("Confirmed Final" if is_final else "Projected finals")
if pairs.get("entries"):
    frame = pd.DataFrame(pairs["entries"]).nlargest(10, "probability")
    frame = frame.head(1) if is_final else frame
    pair_chips = "".join(
        f'<div class="sk-team-chip">'
        f'{flag_html(team_codes.get(entry["finalist_team_1"]), entry["finalist_team_1"], 24)}'
        f'{flag_html(team_codes.get(entry["finalist_team_2"]), entry["finalist_team_2"], 24)}'
        f'<div class="meta"><div class="team">{entry["finalist_pair_key"]}</div>'
        f'<div class="prob">{"Official matchup" if is_final else format(entry["probability"], ".1%") + " final"}</div></div></div>'
        for entry in frame.head(3).to_dict("records")
    )
    st.markdown(f'<div class="sk-team-strip">{pair_chips}</div>', unsafe_allow_html=True)
    if not is_final:
        frame["final"] = frame["finalist_pair_key"]
        figure = px.bar(frame.sort_values("probability"), x="probability", y="final", orientation="h", labels={"probability": "Probability", "final": ""}, text=frame.sort_values("probability")["probability"].map(lambda v: f"{v:.1%}"))
        figure.update_layout(xaxis_tickformat=".0%", height=380)
        st.plotly_chart(apply_plotly(figure), width="stretch")
else:
    missing("Finalist pair forecast unavailable.")
st.caption("Highest estimated probabilities from the current live forecast — probabilistic estimates, not guarantees.")
