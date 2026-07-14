"""Shared application shell and router for the FIFA 2026 dashboard."""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from theme import brand_header, inject_theme  # noqa: E402

st.set_page_config(
    page_title="FIFA 2026 Intelligence",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_theme()

PAGES = [
    st.Page("pages/0_Overview.py", title="Overview", icon=":material/home:", url_path="", default=True),
    st.Page("pages/1_Live_Bracket.py", title="Bracket", icon=":material/account_tree:", url_path="bracket"),
    st.Page("pages/2_Champion_Forecast.py", title="Forecast", icon=":material/emoji_events:", url_path="forecast"),
    st.Page("pages/3_Matchup_Predictions.py", title="Matchups", icon=":material/bolt:", url_path="matchups"),
    st.Page("pages/4_Team_Explorer.py", title="Teams", icon=":material/groups:", url_path="teams"),
    st.Page("pages/5_Forecast_Evolution.py", title="Evolution", icon=":material/monitoring:", url_path="evolution"),
    st.Page("pages/9_Prediction_History.py", title="Prediction History", icon=":material/history:", url_path="history"),
    st.Page("pages/6_Model_Methodology.py", title="Analytics Lab", icon=":material/science:", url_path="analytics"),
    st.Page("pages/7_System_Health.py", title="System Health", icon=":material/vital_signs:", url_path="health"),
    st.Page("pages/8_Technical_Audit.py", title="Audit", icon=":material/fact_check:", url_path="audit"),
]

current_page = st.navigation(PAGES, position="hidden")
brand_header()

# Keep the active pill synchronized with direct links and browser history while
# still allowing a pill click to initiate navigation on the current rerun.
route_marker = "_dashboard_route"
nav_key = "top_navigation"
if st.session_state.get(route_marker) != current_page.url_path:
    st.session_state[route_marker] = current_page.url_path
    st.session_state[nav_key] = current_page.title

selected_page = st.pills(
    "Dashboard navigation",
    [page.title for page in PAGES],
    key=nav_key,
    label_visibility="collapsed",
    width="stretch",
)
if selected_page and selected_page != current_page.title:
    destination = next(page for page in PAGES if page.title == selected_page)
    st.session_state[route_marker] = destination.url_path
    st.switch_page(destination)

st.markdown('<div class="sk-nav-rule"></div>', unsafe_allow_html=True)
current_page.run()
