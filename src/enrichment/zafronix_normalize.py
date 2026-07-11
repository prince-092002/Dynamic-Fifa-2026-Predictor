"""Normalize Zafronix tournament snapshots into small, tracked tables.

Produces three CSVs under data/processed/zafronix/:
  - zafronix_tournaments.csv       (one row per tournament)
  - zafronix_team_appearances.csv  (one row per team-tournament: finish + knockout path)
  - zafronix_squad_players.csv     (one row per player-tournament: position, age, club)

Only fields with documented, leakage-safe temporal meaning are retained downstream;
in-tournament values (goals/cards/assists) are kept here for provenance/description but
are flagged and never used as pre-match model features.
"""

from __future__ import annotations

import json
import re

import pandas as pd

from src.enrichment.zafronix_config import (
    APPEARANCES_CSV,
    PROCESSED_DIR,
    SNAPSHOT_DIR,
    SQUADS_CSV,
    TOURNAMENTS_CSV,
    ensure_dirs,
)

# Knockout stage token -> canonical stage.
_STAGE_MAP = {
    "r64": "round_of_64", "round_of_64": "round_of_64",
    "r32": "round_of_32", "ro32": "round_of_32", "round_of_32": "round_of_32",
    "r16": "round_of_16", "ro16": "round_of_16", "round_of_16": "round_of_16",
    "qf": "quarter_final", "quarterfinal": "quarter_final", "quarter_final": "quarter_final", "quarter-final": "quarter_final",
    "sf": "semi_final", "semifinal": "semi_final", "semi_final": "semi_final", "semi-final": "semi_final",
    "final": "final",
    "3rd": "third_place", "third": "third_place", "third_place": "third_place", "3rd_place": "third_place",
    "3p": "third_place", "tp": "third_place",
}
_POSITION_GROUPS = {"GK": "GK", "DF": "DF", "MF": "MF", "FW": "FW"}


def _norm_stage(stage: str | None) -> str | None:
    if not stage:
        return None
    return _STAGE_MAP.get(str(stage).strip().lower())


def _score_from_result(result: str | None) -> tuple[int | None, int | None]:
    """Parse the leading 'X-Y' from a result string, from the listed team's perspective."""
    if not result:
        return None, None
    match = re.match(r"\s*(\d+)\s*[-–:]\s*(\d+)", str(result))
    if match:
        return int(match.group(1)), int(match.group(2))
    return None, None


def _position_group(position: str | None) -> str | None:
    if not position:
        return None
    token = str(position).strip().upper()
    if token in _POSITION_GROUPS:
        return token
    # map common long forms
    if token.startswith("GOAL"):
        return "GK"
    if token.startswith("DEF") or token in {"CB", "LB", "RB", "RWB", "LWB"}:
        return "DF"
    if token.startswith("MID") or token in {"CM", "DM", "AM", "LM", "RM"}:
        return "MF"
    if token.startswith("FOR") or token.startswith("ATT") or token in {"ST", "CF", "LW", "RW", "SS"}:
        return "FW"
    return None


def normalize_zafronix() -> dict:
    ensure_dirs()
    snapshots = sorted(SNAPSHOT_DIR.glob("tournament_*.json"))
    tournaments, appearances, players = [], [], []
    for path in snapshots:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        tour = payload.get("tournament", {}) or {}
        teams = payload.get("teams", []) or []
        year = tour.get("year")
        if year is None:
            continue
        is_completed = tour.get("champion") not in (None, "")
        tournaments.append({
            "year": year,
            "edition": tour.get("edition"),
            "host": "; ".join(tour.get("host", [])) if isinstance(tour.get("host"), list) else tour.get("host"),
            "start_date": (tour.get("datesIso") or {}).get("start"),
            "end_date": (tour.get("datesIso") or {}).get("end"),
            "teams_count": tour.get("teamsCount") or len(teams),
            "matches_count": tour.get("matchesCount"),
            "champion": tour.get("champion"),
            "runner_up": tour.get("runnerUp"),
            "third_place": tour.get("thirdPlace"),
            "total_goals": tour.get("totalGoals"),
            "is_completed": is_completed,
        })
        for team in teams:
            name = team.get("name")
            if not name:
                continue
            group = team.get("groupStage") or {}
            ko = team.get("knockoutPath") or []
            ko_stages = {s for s in (_norm_stage(k.get("stage")) for k in ko) if s}
            ko_wins = sum(1 for k in ko if bool(k.get("won")))
            ko_gf = ko_ga = 0
            ko_scored_known = False
            for k in ko:
                gf, ga = _score_from_result(k.get("result"))
                if gf is not None:
                    ko_gf += gf
                    ko_ga += ga
                    ko_scored_known = True
            final_pos = team.get("finalPosition")
            reached_final = "final" in ko_stages or final_pos in (1, 2)
            reached_sf = reached_final or "semi_final" in ko_stages or final_pos in (1, 2, 3, 4)
            reached_qf = reached_sf or "quarter_final" in ko_stages
            reached_r16 = reached_qf or "round_of_16" in ko_stages
            reached_r32 = reached_r16 or "round_of_32" in ko_stages
            grp_gf = group.get("gf")
            grp_ga = group.get("ga")
            appearances.append({
                "year": year,
                "team_raw": name,
                "code": team.get("code"),
                "iso": team.get("iso"),
                "confederation": team.get("confederation"),
                "final_position": final_pos,
                "is_champion": bool(final_pos == 1),
                "is_runner_up": bool(final_pos == 2),
                "reached_final": bool(reached_final),
                "reached_semi": bool(reached_sf),
                "reached_quarter": bool(reached_qf),
                "reached_r16": bool(reached_r16),
                "reached_r32": bool(reached_r32),
                "grp_played": group.get("played"),
                "grp_won": group.get("won"),
                "grp_drawn": group.get("drawn"),
                "grp_lost": group.get("lost"),
                "grp_gf": grp_gf,
                "grp_ga": grp_ga,
                "grp_pts": group.get("pts"),
                "ko_matches": len(ko),
                "ko_wins": ko_wins,
                "ko_gf": ko_gf if ko_scored_known else None,
                "ko_ga": ko_ga if ko_scored_known else None,
                "tourn_gf": (grp_gf or 0) + (ko_gf if ko_scored_known else 0) if grp_gf is not None else None,
                "tourn_ga": (grp_ga or 0) + (ko_ga if ko_scored_known else 0) if grp_ga is not None else None,
                "squad_size": len(team.get("squad", []) or []),
                "squad_is_preliminary": bool(team.get("_squadIsPreliminary", False)),
            })
            for pl in team.get("squad", []) or []:
                club = pl.get("club") or {}
                players.append({
                    "year": year,
                    "team_raw": name,
                    "jersey": pl.get("jersey"),
                    "name": pl.get("name"),
                    "position": pl.get("position"),
                    "position_group": _position_group(pl.get("position")),
                    "born": pl.get("born"),
                    "age_at_tournament": pl.get("ageAtTournament"),
                    "club_name": club.get("name"),
                    "club_country": club.get("country"),
                    "caps_at_start": pl.get("caps"),               # ~0% populated (documented)
                    "national_goals_at_start": pl.get("nationalGoals"),  # ~0% populated (documented)
                })

    tdf = pd.DataFrame(tournaments).sort_values("year").reset_index(drop=True)
    adf = pd.DataFrame(appearances).sort_values(["year", "team_raw"]).reset_index(drop=True)
    pdf = pd.DataFrame(players).sort_values(["year", "team_raw", "jersey"]).reset_index(drop=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    tdf.to_csv(TOURNAMENTS_CSV, index=False)
    adf.to_csv(APPEARANCES_CSV, index=False)
    pdf.to_csv(SQUADS_CSV, index=False)
    return {
        "tournaments": len(tdf),
        "appearances": len(adf),
        "players": len(pdf),
        "years": tdf["year"].tolist(),
        "paths": {"tournaments": str(TOURNAMENTS_CSV), "appearances": str(APPEARANCES_CSV), "squads": str(SQUADS_CSV)},
    }


def load_normalized() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    tdf = pd.read_csv(TOURNAMENTS_CSV) if TOURNAMENTS_CSV.exists() else pd.DataFrame()
    adf = pd.read_csv(APPEARANCES_CSV) if APPEARANCES_CSV.exists() else pd.DataFrame()
    pdf = pd.read_csv(SQUADS_CSV) if SQUADS_CSV.exists() else pd.DataFrame()
    return tdf, adf, pdf
