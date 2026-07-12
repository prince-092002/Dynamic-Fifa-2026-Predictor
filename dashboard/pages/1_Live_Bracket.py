"""Live knockout bracket with honest probability-source labels."""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.loaders import load_json, missing, pct  # noqa: E402
from theme import header, flag_html  # noqa: E402
header("Live Knockout Bracket", "Knockout path", "Completed results are locked; unresolved matchups show the live XGBoost advance probability.", icon_name="route")

bracket = load_json("knockout_bracket.json")
if not bracket.get("rounds"):
    missing("Bracket export unavailable. Run the live forecast pipeline first.")
    st.stop()

team_codes = {team["team"]: team.get("code") for team in load_json("teams.json").get("teams", [])}


def team_badge(name: str | None) -> str:
    if not name:
        return '<span class="sk-team-row"><span class="name">TBD</span></span>'
    return f'<span class="sk-team-row">{flag_html(team_codes.get(name), name, 24)}<span class="name">{name}</span></span>'

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
                    st.markdown(
                        f'<div class="sk-match-title">{team_badge(match["team_a"])}'
                        f'<span style="font-family:Space Grotesk;font-weight:700;color:#29d17f">{match.get("score", "")}</span>'
                        f'{team_badge(match["team_b"])}</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(f'Winner: {team_badge(match.get("winner"))}', unsafe_allow_html=True)
                    st.caption(f"{match.get('source_label')} · {str(match.get('date', ''))[:10]}")
                elif state == "scheduled_known":
                    st.markdown(
                        f'<div class="sk-match-title">{team_badge(match["team_a"])}'
                        f'<span class="sk-match-vs">vs</span>{team_badge(match["team_b"])}</div>',
                        unsafe_allow_html=True,
                    )
                    advance_a = match.get("team_a_advance_probability")
                    if advance_a is not None:
                        st.markdown(
                            f'<div style="display:flex;justify-content:space-between;gap:.7rem;color:#9db0cc;font-size:.8rem">'
                            f'<span>{match["team_a"]} <b style="color:#eef4fd">{pct(advance_a)}</b></span>'
                            f'<span>{match["team_b"]} <b style="color:#eef4fd">{pct(match.get("team_b_advance_probability"))}</b></span></div>',
                            unsafe_allow_html=True,
                        )
                        st.caption(f"Favorite: {match.get('predicted_favorite')} · {match.get('source_label')} ({match.get('model', '')})")
                    else:
                        st.caption(f"Source: {match.get('source_label')}")
                    st.caption(f"Scheduled: {str(match.get('date', ''))[:16].replace('T', ' ')} UTC")
                else:
                    st.markdown("*Winners of earlier rounds*")
                    st.caption(f"{match.get('source_label')} · {str(match.get('date', ''))[:10]}")
st.caption("Sources are labeled explicitly; Elo fallback is never presented as an XGBoost prediction.")
