"""Phase 5H-A — Zafronix enrichment tests.

Offline and CI-safe: these tests read the committed normalized tables under
data/processed/zafronix/ and never require the live Zafronix API or the private key.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.enrichment.zafronix_config import APPEARANCES_CSV, SQUADS_CSV
from src.enrichment.zafronix_entities import ALIAS_MAP, resolve_team
from src.enrichment.zafronix_features import (
    ALL_ZAFRONIX_FEATURES,
    build_pedigree_timeline,
    build_zafronix_features,
)
from src.live_state.providers.zafronix_provider import _sanitize

pytestmark = pytest.mark.skipif(
    not (APPEARANCES_CSV.exists() and SQUADS_CSV.exists()),
    reason="Zafronix normalized tables not present (run normalize-zafronix).",
)


# --- secret safety --------------------------------------------------------- #

def test_sanitize_strips_secret_fields():
    payload = {"X-API-Key": "zwc_free_secret", "api_key": "abc", "data": {"token": "t", "ok": True}}
    clean = _sanitize(payload)
    assert "X-API-Key" not in clean and "api_key" not in clean
    assert "token" not in clean["data"]
    assert clean["data"]["ok"] is True


def test_snapshots_and_processed_contain_no_api_key():
    """No tracked Zafronix artifact should contain a Zafronix key prefix."""
    for path in [APPEARANCES_CSV, SQUADS_CSV]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for prefix in ("zwc_pk_", "zwc_sk_", "zwc_free_"):
            assert prefix not in text


# --- entity resolution ----------------------------------------------------- #

def test_resolve_team_exact_and_alias():
    assert resolve_team("Brazil") == "Brazil"
    assert resolve_team("East Germany") == "German DR"
    assert "East Germany" in ALIAS_MAP


def test_historical_entities_kept_distinct():
    # West Germany must NOT be merged into modern Germany (and vice versa).
    assert resolve_team("West Germany") == "West Germany"
    assert resolve_team("Germany") == "Germany"
    assert resolve_team("West Germany") != resolve_team("Germany")
    assert resolve_team("Soviet Union") != resolve_team("Russia")


# --- pedigree timeline ----------------------------------------------------- #

def test_pedigree_timeline_known_values():
    tl = build_pedigree_timeline()
    brazil = tl[tl["canonical"] == "Brazil"].iloc[-1]
    assert brazil["prior_wc_titles"] == 5  # Brazil's historical World Cup titles
    assert brazil["prior_wc_appearances"] >= 20


def _matches(rows):
    return pd.DataFrame(rows)


# --- leakage safety -------------------------------------------------------- #

def test_pedigree_excludes_current_and_future_tournaments():
    """A match DURING the 2022 WC must not see 2022 results; a later match must."""
    df = _matches([
        {"match_id": "m_during", "date": "2022-12-01", "team_a": "Argentina",
         "team_b": "France", "tournament": "FIFA World Cup"},
        {"match_id": "m_after", "date": "2023-06-01", "team_a": "Argentina",
         "team_b": "France", "tournament": "Friendly"},
    ])
    feat = build_zafronix_features(df)
    # Argentina won 2022. During the tournament, titles-diff must reflect pre-2022 (2 titles:
    # 1978, 1986) vs France (1998, 2018 = 2) -> diff 0. After 2022, Argentina has 3 -> diff +1.
    during = feat.iloc[0]["z_prior_wc_titles_diff"]
    after = feat.iloc[1]["z_prior_wc_titles_diff"]
    assert during == 0, f"expected 0 during 2022 WC, got {during} (2022 title leaked)"
    assert after == 1, f"expected +1 after 2022 WC, got {after}"
    assert after > during


def test_no_pedigree_before_first_world_cup():
    df = _matches([{"match_id": "m", "date": "1900-01-01", "team_a": "Brazil",
                    "team_b": "Argentina", "tournament": "Friendly"}])
    feat = build_zafronix_features(df)
    assert feat.iloc[0]["z_prior_wc_appearances_diff"] == 0
    assert feat.iloc[0]["z_pedigree_available"] == 0


def test_squad_features_only_for_world_cup_finals():
    df = _matches([
        {"match_id": "wc", "date": "2018-06-20", "team_a": "Brazil",
         "team_b": "Germany", "tournament": "FIFA World Cup"},
        {"match_id": "friendly", "date": "2018-03-20", "team_a": "Brazil",
         "team_b": "Germany", "tournament": "Friendly"},
    ])
    feat = build_zafronix_features(df)
    assert feat.iloc[0]["z_squad_features_available"] == 1
    assert feat.iloc[1]["z_squad_features_available"] == 0
    # squad diffs are neutral (0) outside WC finals
    assert feat.iloc[1]["z_squad_avg_age_diff"] == 0


# --- determinism & imputation --------------------------------------------- #

def test_feature_determinism():
    df = _matches([{"match_id": "m", "date": "2014-07-08", "team_a": "Brazil",
                    "team_b": "Germany", "tournament": "FIFA World Cup"}])
    a = build_zafronix_features(df)
    b = build_zafronix_features(df)
    pd.testing.assert_frame_equal(a, b)


def test_all_features_numeric_and_no_nan():
    df = _matches([
        {"match_id": "1", "date": "2010-06-11", "team_a": "South Africa",
         "team_b": "Mexico", "tournament": "FIFA World Cup"},
        {"match_id": "2", "date": "2019-01-01", "team_a": "Nepal",
         "team_b": "Bhutan", "tournament": "Friendly"},
    ])
    feat = build_zafronix_features(df)
    assert list(feat.columns) == ALL_ZAFRONIX_FEATURES
    assert feat.notna().all().all()
    for c in feat.columns:
        assert pd.api.types.is_numeric_dtype(feat[c])


# --- production separation -------------------------------------------------- #

def test_challenger_artifacts_separate_from_production():
    from src.enrichment.zafronix_config import MODEL_DIR as CHALLENGER_DIR
    from src.modeling.model_config import MODEL_DIR as PRODUCTION_DIR

    assert CHALLENGER_DIR != PRODUCTION_DIR
    assert "phase5h" in str(CHALLENGER_DIR).lower()
