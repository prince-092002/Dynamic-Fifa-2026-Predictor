"""Live knockout bracket with honest probability-source labels."""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.loaders import load_json, missing, pct  # noqa: E402

st.set_page_config(page_title="Live Bracket", page_icon="🏆", layout="wide")
st.title("🏆 Live Knockout Bracket")

bracket = load_json("knockout_bracket.json")
if not bracket.get("rounds"):
    missing("Bracket export unavailable. Run the live forecast pipeline first.")
    st.stop()

stages = [round_["stage"] for round_ in bracket["rounds"]]
selected = st.multiselect("Rounds", stages, default=stages[-4:] if len(stages) > 4 else stages)

legend = bracket.get("source_legend", {})
with st.expander("Probability source legend"):
    for key, label in legend.items():
        st.markdown(f"- `{key}` → **{label}**")

for round_ in bracket["rounds"]:
    if round_["stage"] not in selected:
        continue
    st.subheader(round_["stage"])
    columns = st.columns(min(4, max(1, len(round_["matches"]))))
    for index, match in enumerate(round_["matches"]):
        with columns[index % len(columns)]:
            with st.container(border=True):
                state = match.get("state")
                if state == "completed":
                    st.markdown(f"**{match['team_a']} {match.get('score', '')} {match['team_b']}**")
                    st.markdown(f"✅ Winner: **{match.get('winner')}**")
                    st.caption(f"{match.get('source_label')} · {str(match.get('date', ''))[:10]}")
                elif state == "scheduled_known":
                    st.markdown(f"**{match['team_a']}** vs **{match['team_b']}**")
                    advance_a = match.get("team_a_advance_probability")
                    if advance_a is not None:
                        st.markdown(f"{match['team_a']}: **{pct(advance_a)}** · {match['team_b']}: **{pct(match.get('team_b_advance_probability'))}**")
                        st.caption(f"Favorite: {match.get('predicted_favorite')} · {match.get('source_label')} ({match.get('model', '')})")
                    else:
                        st.caption(f"Source: {match.get('source_label')}")
                    st.caption(f"Scheduled: {str(match.get('date', ''))[:16].replace('T', ' ')} UTC")
                else:
                    st.markdown("*Winners of earlier rounds*")
                    st.caption(f"{match.get('source_label')} · {str(match.get('date', ''))[:10]}")
st.caption("Sources are labeled explicitly; Elo fallback is never presented as an XGBoost prediction.")
