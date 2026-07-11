"""Entity resolution: Zafronix team names -> training-dataset canonical names.

Findings from the actual data (see zafronix_entity_resolution_report.csv):
90 of 91 Zafronix World Cup team names match a training-dataset name exactly. The
training dataset already preserves historically distinct national teams under separate
names (West Germany, East Germany, Soviet Union, Yugoslavia, FR Yugoslavia, Serbia and
Montenegro, Czechoslovakia, Zaire, ...), so exact matching is historically correct and
does NOT merge distinct entities.

The single non-exact case is 'East Germany' -> 'German DR'. No fuzzy string matching is
used; only an explicit, auditable alias map. Historically distinct successor entities are
deliberately kept separate (documented below) rather than silently combined.
"""

from __future__ import annotations

import json

import pandas as pd

from src.enrichment.zafronix_config import REPORT_DIR, ensure_dirs
from src.enrichment.zafronix_normalize import load_normalized

# Explicit alias: Zafronix name -> training canonical name (only where the strings differ).
ALIAS_MAP: dict[str, str] = {
    "East Germany": "German DR",
}

# Successor / historically distinct entities intentionally NOT merged. Attaching one
# entity's World Cup pedigree to another would be a modelling judgement, not a fact, so
# each is resolved to its own name and this decision is documented, not hidden.
HISTORICAL_DISTINCT_NOTES: dict[str, str] = {
    "West Germany": "Kept separate from 'Germany' (post-1990). Pre-1990 pedigree is not inherited by 'Germany'.",
    "German DR": "East Germany — dissolved 1990; kept fully separate.",
    "Soviet Union": "Kept separate from 'Russia' and other post-Soviet states.",
    "Yugoslavia": "Kept separate from 'FR Yugoslavia', 'Serbia and Montenegro', 'Serbia', and other successors.",
    "FR Yugoslavia": "Kept separate from 'Yugoslavia' and 'Serbia and Montenegro'.",
    "Serbia and Montenegro": "Kept separate from 'Serbia' and 'FR Yugoslavia'.",
    "Czechoslovakia": "Kept separate from 'Czech Republic' and 'Slovakia'.",
    "Zaire": "Kept separate from 'DR Congo' (same country, distinct dataset name).",
    "Dutch East Indies": "1938 entity; kept separate from 'Indonesia'.",
}


def resolve_team(name: str | None) -> str | None:
    """Return the canonical training name for a Zafronix team name."""
    if name is None or (isinstance(name, float)):
        return None
    key = str(name).strip()
    return ALIAS_MAP.get(key, key)


def training_team_names() -> set[str]:
    from src.modeling.model_config import TRAINING_DATASET_PATH

    df = pd.read_csv(TRAINING_DATASET_PATH, usecols=["team_a", "team_b"])
    return set(df["team_a"].dropna()) | set(df["team_b"].dropna())


def build_entity_resolution() -> dict:
    """Resolve every Zafronix team name and write alias + resolution + unresolved reports."""
    ensure_dirs()
    _, appearances, _ = load_normalized()
    train_names = training_team_names()
    zafronix_names = sorted(appearances["team_raw"].dropna().unique()) if not appearances.empty else []

    rows, unresolved = [], []
    for name in zafronix_names:
        canonical = resolve_team(name)
        method = (
            "exact" if name == canonical and canonical in train_names
            else "alias" if name in ALIAS_MAP and canonical in train_names
            else "unresolved"
        )
        matched = canonical in train_names
        rows.append({
            "zafronix_name": name,
            "canonical_name": canonical,
            "match_method": method,
            "matched_in_training": matched,
            "historical_note": HISTORICAL_DISTINCT_NOTES.get(canonical, ""),
        })
        if not matched:
            unresolved.append({"zafronix_name": name, "attempted_canonical": canonical,
                               "reason": "no exact/alias match in training team names"})

    report = pd.DataFrame(rows)
    unresolved_df = pd.DataFrame(unresolved, columns=["zafronix_name", "attempted_canonical", "reason"])
    report.to_csv(REPORT_DIR / "zafronix_entity_resolution_report.csv", index=False)
    unresolved_df.to_csv(REPORT_DIR / "zafronix_unresolved_entities.csv", index=False)

    aliases = {
        "generated_note": "Zafronix -> training canonical team-name resolution. Explicit map only; no fuzzy matching.",
        "alias_map": ALIAS_MAP,
        "historical_distinct_notes": HISTORICAL_DISTINCT_NOTES,
        "counts": {
            "zafronix_names": len(zafronix_names),
            "exact": int((report["match_method"] == "exact").sum()) if not report.empty else 0,
            "alias": int((report["match_method"] == "alias").sum()) if not report.empty else 0,
            "unresolved": len(unresolved),
        },
    }
    (REPORT_DIR / "zafronix_team_aliases.json").write_text(json.dumps(aliases, indent=2), encoding="utf-8")

    return {
        "zafronix_names": len(zafronix_names),
        "resolved": len(zafronix_names) - len(unresolved),
        "unresolved": len(unresolved),
        "unresolved_names": [u["zafronix_name"] for u in unresolved],
        "resolution_rate": round((len(zafronix_names) - len(unresolved)) / max(len(zafronix_names), 1), 4),
    }
