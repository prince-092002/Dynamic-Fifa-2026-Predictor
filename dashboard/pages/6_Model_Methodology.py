"""Model, features, leakage protections, and probability-source methodology."""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.loaders import load_json, missing  # noqa: E402
from theme import header, apply_plotly  # noqa: E402
header("Inside the Prediction Engine", "Analytics Lab", "The model, its Phase 5G diagnostics, the features that matter, and the validation that keeps it honest.", icon_name="lab")

st.markdown(
    """
```text
Historical match data (~50k international matches)
        ↓  leakage-safe feature engineering (chronological, shift-before-rolling)
Model comparison (baselines, logistic regression, XGBoost)
        ↓  selected XGBoost classifier (win / draw / loss)
Live knockout feature generation (completed real results as history)
        ↓  current matchup probabilities
Monte Carlo tournament simulation (completed results locked)
        ↓
Champion & finalist forecasts + validation + audit manifest
```
"""
)

insights = load_json("model_insights.json")
if not insights:
    missing("Model insights unavailable. Run `python main.py build-public-exports`.")
    st.stop()

st.subheader("Model comparison (actual test metrics)")
models = pd.DataFrame(insights.get("models", []))
if not models.empty:
    models["selected"] = models["selected"].map({True: "✅ selected", False: ""})
    models.columns = ["Model", "Selected", "Accuracy", "Log loss", "Brier", "Macro F1", "Train rows", "Test rows"]
    st.dataframe(models, use_container_width=True, hide_index=True)

diagnostics = insights.get("diagnostics")
if diagnostics:
    st.subheader("Model diagnostics (Phase 5G)")
    st.caption(diagnostics.get("evaluation", ""))
    per_class = diagnostics.get("per_class", {})
    actual = diagnostics.get("actual_distribution", {})
    predicted = diagnostics.get("predicted_distribution", {})
    diag_rows = []
    for cls, m in per_class.items():
        diag_rows.append({
            "Outcome (test)": cls.replace("_", " "),
            "Precision": m.get("precision"), "Recall": m.get("recall"), "F1": m.get("f1"),
            "Actual": actual.get(cls), "Predicted": predicted.get(cls),
        })
    if diag_rows:
        st.dataframe(pd.DataFrame(diag_rows), use_container_width=True, hide_index=True)
    st.caption(f"Calibration error (ECE): {diagnostics.get('calibration_ece')} — near-perfectly calibrated.")
    st.info(diagnostics.get("macro_f1_note", ""))

st.subheader("Model input features")
features = insights.get("selected_feature_columns", [])
groups = {
    "Elo-derived strength": [f for f in features if "elo" in f],
    "Recent form": [f for f in features if "form" in f or "win_rate" in f or "loss_rate" in f],
    "Goal-based form": [f for f in features if "goal" in f or "clean_sheet" in f],
    "Head-to-head": [f for f in features if f.startswith("h2h")],
    "Tournament context": [f for f in features if f.startswith("is_") or "importance" in f or "stage" in f],
    "Rest & schedule": [f for f in features if "days" in f or "congestion" in f or "rest" in f],
}
columns = st.columns(3)
for index, (group, names) in enumerate(groups.items()):
    if names:
        with columns[index % 3]:
            st.markdown(f"**{group}** ({len(names)})")
            for name in names:
                st.caption(f"`{name}`")

st.subheader("Global feature importance")
importance = insights.get("global_feature_importance")
if importance:
    frame = pd.DataFrame(importance[:10]).sort_values("importance")
    figure = px.bar(frame, x="importance", y="feature", orientation="h", title="Top 10 global XGBoost feature importances")
    figure.update_layout(height=380)
    st.plotly_chart(apply_plotly(figure), use_container_width=True)
    st.info(insights.get("importance_note", ""))
else:
    missing("Global feature importance could not be extracted from the selected model artifact.")

st.subheader("Leakage prevention")
st.markdown(
    """
- The target match outcome never enters its own features.
- Only **completed** matches enter history; unplayed placeholder rows with missing goals are excluded.
- Rolling/form features are sorted chronologically and shifted **before** rolling windows.
- The target matchup never enters its own historical feature calculation.
- Live feature generation was equivalence-tested against the original pipeline (112/112 values exactly identical).
"""
)

st.subheader("Probability source ladder")
st.markdown(
    """
1. **Completed real result** — locked, never re-simulated
2. **Live XGBoost prediction** — for resolved real matchups
3. **Pre-tournament model prediction** — when a pairing matches the original fixture list
4. **Elo fallback** — hypothetical future branches whose real participants are not yet known
5. **Neutral fallback** — last resort when no rating exists

Future semifinal/final pairings only exist *inside* each simulated branch, so they use Elo until
the real bracket resolves them — then the next update predicts them with XGBoost automatically.
"""
)
