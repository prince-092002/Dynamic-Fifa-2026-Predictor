"""Data quality, provider freshness, and validation status."""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.loaders import load_json, missing  # noqa: E402
from theme import header  # noqa: E402
header("Data Quality & System Health", "Live provider · quality gate · validation", "Provider freshness, forecast quality gate, and validation status.", icon_name="signal")

health = load_json("system_health.json")
if not health:
    missing("System health export unavailable.")
    st.stop()

freshness = health.get("provider_freshness") or {}
gate = health.get("quality_gate") or {}

st.subheader("Provider freshness")
if freshness:
    left, mid, right, far = st.columns(4)
    left.metric("Provider", freshness.get("provider", "—"))
    mode = freshness.get("data_source_mode", "—")
    mid.metric("Data source mode", mode, "fresh" if mode == "fresh_api" else "not fresh", delta_color="normal" if mode == "fresh_api" else "off")
    age = freshness.get("data_age_minutes")
    right.metric("Data age", f"{age:.0f} min" if age is not None else "—")
    far.metric("Rate limited", str(freshness.get("rate_limited", "—")))
    left, mid, right, far = st.columns(4)
    left.metric("Request status", str(freshness.get("request_status", "—")))
    mid.metric("Fixture rows", freshness.get("fixture_row_count", "—"))
    right.metric("Completed fixtures", freshness.get("completed_fixture_count", "—"))
    far.metric("Cache / snapshot used", f"{freshness.get('cache_used')} / {freshness.get('snapshot_used')}")
    if freshness.get("cache_used") or freshness.get("snapshot_used"):
        st.warning("Displayed data comes from cached/snapshot files, not a fresh API response.")
else:
    missing("Provider freshness metadata unavailable.")

st.subheader("Forecast quality gate")
left, mid, right, far = st.columns(4)
left.metric("Forecast mode", str(gate.get("forecast_mode", "—")).replace("_", " "))
mid.metric("Source quality score", gate.get("source_quality_score", "—"))
right.metric("Current phase", str(gate.get("current_phase", "—")).replace("_", " ").title())
far.metric("Finalist forecast allowed", str(gate.get("finalist_prediction_allowed", "—")))
st.caption(f"Public label: {gate.get('public_label', '—')} · completed results: {gate.get('completed_result_count', '—')} · bracket fallback rate: {gate.get('fallback_usage_rate', '—')}")

st.subheader("Validation status")
validations = health.get("validations") or {}
left, right = st.columns(2)
for column, (name, counts) in zip([left, right], validations.items()):
    with column:
        st.markdown(f"**{name.replace('_', ' ').title()}**")
        if counts:
            inner = st.columns(3)
            inner[0].metric("Pass", counts.get("pass", 0))
            inner[1].metric("Warn", counts.get("warn", 0))
            inner[2].metric("Fail", counts.get("fail", 0))
            if counts.get("fail", 0):
                st.error("Failing checks present — inspect outputs/reports/.")
            elif counts.get("warn", 0):
                st.caption("Warnings are expected, documented conditions (e.g. TBD template slots, raw-feed duplicates handled downstream).")
        else:
            missing("Validation report unavailable.")
with st.expander("What the warnings mean"):
    st.markdown(
        """
- **Raw master duplicates** — the two Kaggle source feeds intentionally overlap; feature engineering deduplicates before any model use (a fail-capable check guards the deduplicated file).
- **Knockout placeholder team names** — the pre-tournament fixture template keeps TBD knockout slots; live bracket data resolves them.
"""
    )
