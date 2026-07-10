"""Tournament context features."""

from __future__ import annotations

import pandas as pd

from src.features.feature_config import FEATURE_INTERMEDIATE_DIR


def _importance(tournament: object, stage: object) -> int:
    text = f"{tournament or ''} {stage or ''}".lower()
    if "world cup" in text and any(word in text for word in ["final", "quarter", "semi", "round of", "knockout"]):
        return 5
    if "world cup" in text:
        return 4
    if any(word in text for word in ["euro", "copa", "africa cup", "asian cup", "gold cup", "nations"]):
        return 3
    if "qualif" in text:
        return 2
    if "friendly" in text:
        return 1
    return 2


def build_tournament_features(df: pd.DataFrame, output_name: str) -> pd.DataFrame:
    data = df.copy()
    stage = data.get("stage", pd.Series("", index=data.index)).fillna("").astype(str).str.lower()
    tournament = data.get("tournament", pd.Series("", index=data.index)).fillna("").astype(str).str.lower()
    combined = tournament + " " + stage
    output = pd.DataFrame({"match_id": data["match_id"]})
    output["is_world_cup_match"] = combined.str.contains("world cup", regex=False)
    output["is_friendly"] = combined.str.contains("friendly", regex=False)
    output["is_qualifier"] = combined.str.contains("qualif", regex=False)
    output["is_knockout"] = stage.str.contains("final|quarter|semi|round of|knockout", regex=True)
    output["is_group_stage"] = stage.str.contains("group", regex=False)
    neutral = data.get("neutral", pd.Series(False, index=data.index)).fillna(False)
    output["is_neutral"] = neutral.astype(str).str.lower().isin(["true", "1", "yes"])
    output["stage_encoded"] = pd.factorize(stage.fillna("unknown"))[0]
    output["tournament_importance_score"] = data.apply(lambda row: _importance(row.get("tournament"), row.get("stage")), axis=1)
    output.to_csv(FEATURE_INTERMEDIATE_DIR / output_name, index=False)
    return output
