"""Dynamic FIFA 2026 — live analytics dashboard entry (Overview / command center)."""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.loaders import load_json, missing, pct  # noqa: E402
from theme import header, kpi_grid, bar, icon, flag_html, CYAN, PITCH, GOLD, FG2, FG3  # noqa: E402

overview = load_json("latest_overview.json")
if not overview:
    header("Live Tournament Intelligence", "Overview")
    missing("Current overview unavailable. Run the live forecast pipeline, then `python main.py build-public-exports`.")
    st.stop()

phase = str(overview.get("current_phase", "unknown")).replace("_", " ").title()
live = overview.get("forecast_mode") == "true_live_forecast"
is_final = overview.get("current_phase") == "final"
final_result = overview.get("final_result") or {}
is_complete = bool(overview.get("tournament_complete") and final_result)
if is_complete:
    phase = "Tournament complete"
    live = False
header(
    "Tournament Intelligence" if is_complete else "Live Tournament Intelligence",
    "Final state" if is_complete else "Command center",
    (f'Tournament complete — {final_result.get("champion")} are FIFA World Cup champions. '
     f'Final update: {final_result.get("published_label")}.')
    if is_complete else "Current forecast based on completed tournament results and live tournament state.",
    icon_name="pitch", live=live,
)

kpi_grid([
    {"label": "Current phase", "value": phase, "accent": "cyan", "icon": "pitch", "hint": "all matches played" if is_complete else f'{overview.get("known_unresolved_matchups","—")} {"matchup" if overview.get("known_unresolved_matchups") == 1 else "matchups"} unresolved'},
    {"label": "Matches complete", "value": overview.get("completed_matches", "—"), "accent": "pitch", "icon": "lock", "hint": "locked · never re-simulated"},
    {"label": "Teams remaining", "value": overview.get("teams_alive", "—"), "accent": "gold", "icon": "team", "hint": "tournament decided" if is_complete else f'{overview.get("teams_eliminated","—")} eliminated'},
    {"label": "Source quality", "value": f'{overview.get("source_quality_score","—")}/100', "accent": "cyan", "icon": "signal",
     "hint": f'{overview.get("data_source_mode","—")} · {overview.get("data_age_minutes",0)} min'},
    {"label": "Simulations", "value": f'{overview.get("simulations",0):,}' if overview.get("simulations") else "—", "accent": "blue", "icon": "sim", "hint": overview.get("selected_model", "")},
])

# Featured champion + top contenders
champion = load_json("champion_forecast.json")
teams = {t["team"]: t for t in load_json("teams.json").get("teams", [])}
left, right = st.columns([1, 1.15])

with left:
    if overview.get("top_champion"):
        team = teams.get(overview["top_champion"], {})
        flag = flag_html(team.get("code"), overview["top_champion"], 40)
        prob = overview.get("top_champion_probability") or 0
        st.markdown(
            f'''<div class="sk-feature">
              <div class="sk-kicker" style="color:{GOLD}">{icon("trophy", GOLD, 14)} {"World champions" if is_complete else "Most likely champion"}</div>
              <div style="display:flex;align-items:center;gap:.6rem;margin-top:.5rem">
                <span style="font-size:2.2rem">{flag}</span>
                <span style="font-family:'Space Grotesk';font-weight:700;font-size:2.3rem;color:#eef4fd">{overview["top_champion"]}</span>
              </div>
              <div style="font-family:'Space Grotesk';font-weight:700;font-size:2.6rem;color:{GOLD};margin-top:.3rem">{(str(final_result.get("champion_goals")) + "–" + str(final_result.get("runner_up_goals"))) if is_complete else pct(prob)}</div>
              <div style="color:{FG2};font-size:.85rem;margin-top:.4rem">{f'Final: {final_result.get("champion")} {final_result.get("champion_goals")}–{final_result.get("runner_up_goals")} {final_result.get("runner_up")} · {final_result.get("decided_label")}' if is_complete else ('Confirmed Final' if is_final else 'Projected final') + f': {overview.get("top_finalist_pair","—")}' + ('' if is_final else f' ({pct(overview.get("top_finalist_pair_probability"))})')}</div>
              <div style="color:{FG3};font-size:.75rem;margin-top:.35rem">{f'{final_result.get("runner_up")} finished as runner-up · tournament complete' if is_complete else ('Direct XGBoost probability of winning the final and championship' if is_final else 'Monte Carlo championship probability')}</div>
            </div>''',
            unsafe_allow_html=True,
        )

with right:
    st.markdown(f'<div class="sk-kicker" style="margin-bottom:.6rem">{icon("chart", CYAN, 14)} Top contenders</div>', unsafe_allow_html=True)
    entries = sorted(champion.get("entries", []), key=lambda e: -e["champion_probability"])[:5]
    rows = ""
    for i, e in enumerate(entries):
        team = teams.get(e["team"], {})
        flag = flag_html(team.get("code"), e["team"], 24)
        color = GOLD if i == 0 else CYAN
        rows += (f'<div style="display:flex;align-items:center;gap:.6rem;margin-bottom:.55rem">'
                 f'<span style="width:1.4rem;color:{FG3};font-family:Space Grotesk;font-weight:700">{i+1}</span>'
                 f'<span style="width:1.4rem">{flag}</span>'
                 f'<span style="width:8rem;color:#eef4fd;font-weight:600">{e["team"]}</span>'
                 f'<span style="flex:1">{bar(e["champion_probability"], color)}</span>'
                 f'<span style="width:3.4rem;text-align:right;font-family:Space Grotesk;font-weight:700;color:#eef4fd">{pct(e["champion_probability"])}</span></div>')
    st.markdown(f'<div class="sk-card">{rows}</div>', unsafe_allow_html=True)

st.markdown("")
st.markdown(f'<div class="sk-kicker">{icon("network", CYAN, 14)} How the system works</div>', unsafe_allow_html=True)
st.markdown(
    """
```text
Live match results (football-data.org)
   → tournament state (completed results locked, never re-simulated)
   → leakage-safe feature generation for resolved matchups
   → XGBoost matchup probabilities
   → Monte Carlo tournament simulations
   → champion / finalist forecasts → validation + audit manifest
```
Use the navigation above to explore the live bracket, forecasts, matchup predictions, the team explorer,
forecast evolution, the analytics lab, system health, and the technical audit trail.
"""
)
st.caption(f'Latest run: {overview.get("run_id","unknown")} · model: {overview.get("selected_model","unknown")} · seed: {overview.get("seed","—")} · Independent analytics project — not affiliated with FIFA. Probabilistic estimates, not guarantees.')
