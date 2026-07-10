"""Team explorer: filter, sort, and inspect every real tournament team."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.loaders import load_json, missing, pct  # noqa: E402

st.set_page_config(page_title="Team Explorer", page_icon="🌍", layout="wide")
st.title("🌍 Team Explorer")

teams_payload = load_json("teams.json")
stats_payload = load_json("team_stats.json")
teams = teams_payload.get("teams", [])
if not teams:
    missing("Team export unavailable. Run `python main.py build-public-exports` first.")
    st.stop()

frame = pd.DataFrame(teams)
left, mid, right, far = st.columns(4)
search = left.text_input("Search team")
status_filter = mid.selectbox("Status", ["All", "Still alive", "Eliminated"])
groups = sorted(g for g in frame["group"].dropna().unique())
group_filter = right.selectbox("Group", ["All"] + groups)
sort_by = far.selectbox("Sort by", ["Championship probability", "Finalist probability", "Goals scored", "Goal difference", "Matches won", "Alphabetical"])

filtered = frame.copy()
if search:
    filtered = filtered[filtered["team"].str.contains(search, case=False, na=False)]
if status_filter == "Still alive":
    filtered = filtered[filtered["status"].isin(["alive", "champion", "runner_up"])]
elif status_filter == "Eliminated":
    filtered = filtered[filtered["status"] == "eliminated"]
if group_filter != "All":
    filtered = filtered[filtered["group"] == group_filter]
sort_map = {
    "Championship probability": ("champion_probability", False),
    "Finalist probability": ("reach_final_probability", False),
    "Goals scored": ("goals_for", False),
    "Goal difference": ("goal_difference", False),
    "Matches won": ("wins", False),
    "Alphabetical": ("team", True),
}
column, ascending = sort_map[sort_by]
filtered = filtered.sort_values(column, ascending=ascending, na_position="last")

display = filtered[["flag", "team", "group", "status", "stage_reached", "played", "wins", "draws", "losses", "goals_for", "goals_against", "goal_difference", "champion_probability", "reach_final_probability"]].copy()
display["champion_probability"] = display["champion_probability"].map(lambda v: f"{v:.2%}" if pd.notna(v) else "—")
display["reach_final_probability"] = display["reach_final_probability"].map(lambda v: f"{v:.2%}" if pd.notna(v) else "—")
display.columns = ["", "Team", "Group", "Status", "Stage reached", "P", "W", "D", "L", "GF", "GA", "GD", "Champion", "Finalist"]
st.dataframe(display, use_container_width=True, hide_index=True, height=420)

st.divider()
st.subheader("Team detail")
selected_name = st.selectbox("Choose a team", filtered["team"].tolist() if not filtered.empty else frame["team"].tolist())
team = frame[frame["team"] == selected_name].iloc[0]
stats = (stats_payload.get("team_stats") or {}).get(team["slug"], {})

left, right = st.columns([1, 2])
with left:
    st.markdown(f"## {team.get('flag') or ''} {team['team']}")
    st.markdown(f"**Group {team.get('group', '—')}** · code {team.get('code') or '—'}")
    status = team["status"]
    if status in {"alive", "champion", "runner_up"}:
        st.success(f"Status: {status.replace('_', ' ').title()} · reached {team['stage_reached']}")
    else:
        st.error(f"Eliminated in {team.get('eliminated_in') or team['stage_reached']}" + (f" by {team['eliminated_by']}" if team.get("eliminated_by") else ""))
    st.metric("Champion probability", pct(team.get("champion_probability")))
    st.metric("Reach-final probability", pct(team.get("reach_final_probability")))
    next_matchup = team.get("next_matchup")
    if isinstance(next_matchup, dict):
        st.markdown(f"**Next:** vs {next_matchup.get('opponent')} ({next_matchup.get('stage')})")
        if next_matchup.get("advance_probability") is not None:
            st.caption(f"Advance probability {pct(next_matchup['advance_probability'])} · {next_matchup.get('source_label', '')}")
with right:
    st.markdown("#### Tournament record (completed matches only)")
    record_cols = st.columns(6)
    for column_widget, (label, key) in zip(record_cols, [("Played", "played"), ("Wins", "wins"), ("Draws", "draws"), ("Losses", "losses"), ("GF", "goals_for"), ("GA", "goals_against")]):
        column_widget.metric(label, stats.get(key, team.get(key, 0)))
    extra = st.columns(3)
    extra[0].metric("Goal difference", stats.get("goal_difference", team.get("goal_difference", 0)))
    extra[1].metric("Avg scored", stats.get("avg_goals_for", "—"))
    extra[2].metric("Clean sheets", stats.get("clean_sheets", "—"))
    matches = stats.get("matches", [])
    if matches:
        st.markdown("#### Tournament journey")
        journey = pd.DataFrame(matches)[["date", "stage", "opponent", "score", "result"]]
        journey.columns = ["Date", "Stage", "Opponent", "Score", "Result"]
        st.dataframe(journey, use_container_width=True, hide_index=True)
    else:
        missing("No completed matches recorded for this team.")

history = load_json("forecast_history.json")
champion_history = pd.DataFrame(history.get("champion", []))
if not champion_history.empty and (champion_history["team"] == selected_name).sum() >= 2:
    import plotly.express as px

    team_history = champion_history[champion_history["team"] == selected_name]
    figure = px.line(team_history, x="timestamp", y="champion_probability", title=f"{selected_name} — champion probability over recorded runs", markers=True)
    figure.update_layout(yaxis_tickformat=".0%", height=320)
    st.plotly_chart(figure, use_container_width=True)
else:
    st.caption("Forecast history will appear after additional recorded forecast runs.")
st.caption("Player-level statistics are not currently part of the verified data pipeline.")
