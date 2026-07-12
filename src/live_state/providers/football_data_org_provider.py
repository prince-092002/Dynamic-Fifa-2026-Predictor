"""football-data.org live provider for FIFA World Cup data."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import requests

from src.config import (
    FOOTBALL_DATA_ORG_COMPETITION_CODE,
    FOOTBALL_DATA_ORG_COMPETITION_ID,
    FOOTBALL_DATA_ORG_KEY,
    FOOTBALL_DATA_ORG_SEASON,
)
from src.live_state.current_phase_detector import detect_current_tournament_phase
from src.live_state.live_config import LIVE_STATE_DIR, coerce_bool_series
from src.live_state.live_source_config import ensure_source_verification_directories
from src.simulation.tournament_structure import is_tbd_team
from src.utils.dates import now_utc_iso

BASE_URL = "https://api.football-data.org/v4"
PROVIDER = "football_data_org"
SNAPSHOT_DIR = LIVE_STATE_DIR / "provider_snapshots" / PROVIDER
REPORT_DIR = LIVE_STATE_DIR.parent / "reports" / "live_state" / "providers"

FIXTURE_COLUMNS = [
    "fixture_id", "match_id", "date", "round", "stage", "group", "team_a", "team_b", "team_a_id", "team_b_id",
    "team_a_goals", "team_b_goals", "team_a_penalty_goals", "team_b_penalty_goals", "winner", "status_short",
    "status_long", "elapsed", "is_completed", "is_live", "is_scheduled", "is_knockout", "venue", "city",
    "country", "source", "provider", "last_updated",
]
TEAM_COLUMNS = ["team_id", "team", "short_name", "tla", "crest", "country", "source", "provider", "last_updated"]
STANDING_COLUMNS = [
    "group", "rank", "team", "team_id", "played", "wins", "draws", "losses", "goals_for", "goals_against",
    "goal_difference", "points", "form", "qualification_status", "source", "provider", "last_updated",
]
BRACKET_COLUMNS = [
    "fixture_id", "match_id", "round", "stage", "team_a", "team_b", "winner", "status", "is_completed",
    "is_live", "is_scheduled", "is_tbd", "bracket_source", "provider", "last_updated",
]

STAGE_MAP = {
    "GROUP_STAGE": "Group Stage",
    "LAST_32": "Round of 32",
    "ROUND_OF_32": "Round of 32",
    "ROUND_OF_16": "Round of 16",
    "LAST_16": "Round of 16",
    "QUARTER_FINALS": "Quarterfinal",
    "SEMI_FINALS": "Semifinal",
    "FINAL": "Final",
    "THIRD_PLACE": "Third Place Playoff",
}

COMPLETED = {"FINISHED"}
LIVE = {"IN_PLAY", "PAUSED"}
SCHEDULED = {"TIMED", "SCHEDULED"}
POSTPONED = {"POSTPONED", "SUSPENDED"}
CANCELLED = {"CANCELED", "CANCELLED"}


class FootballDataOrgProvider:
    """Provider implementation for football-data.org."""

    def __init__(
        self,
        token: str | None = FOOTBALL_DATA_ORG_KEY,
        competition_code: str = FOOTBALL_DATA_ORG_COMPETITION_CODE,
        competition_id: str = FOOTBALL_DATA_ORG_COMPETITION_ID,
        season: str = FOOTBALL_DATA_ORG_SEASON,
    ) -> None:
        self.token = token
        self.competition_code = str(competition_code or "WC")
        self.competition_id = str(competition_id or "2000")
        self.season = str(season or "2026")
        self.last_payloads: dict[str, dict] = {}
        self.last_statuses: dict[str, int | str] = {}

    def provider_name(self) -> str:
        return PROVIDER

    def credentials_available(self) -> bool:
        return bool(self.token)

    def _headers(self) -> dict[str, str]:
        return {"X-Auth-Token": self.token or ""}

    def _request(self, endpoint: str, snapshot_name: str, params: dict[str, Any] | None = None) -> dict:
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        if not self.credentials_available():
            payload = {"error": "FOOTBALL_DATA_ORG_KEY is not set", "response": []}
            status = "missing_key"
        else:
            try:
                response = requests.get(f"{BASE_URL}/{endpoint.lstrip('/')}", headers=self._headers(), params=params, timeout=30)
                if response.status_code == 429:
                    # Honor the server's Retry-After once, capped so diagnostics never stall.
                    retry_after = pd.to_numeric(response.headers.get("Retry-After"), errors="coerce")
                    if pd.notna(retry_after) and 0 < retry_after <= 15:
                        time.sleep(float(retry_after))
                        response = requests.get(f"{BASE_URL}/{endpoint.lstrip('/')}", headers=self._headers(), params=params, timeout=30)
                status = response.status_code
                try:
                    payload = response.json()
                except Exception:
                    payload = {"raw_text": response.text[:1000]}
            except Exception as exc:
                status = "request_failed"
                payload = {"error": str(exc), "response": []}
        self.last_payloads[snapshot_name] = payload
        self.last_statuses[snapshot_name] = status
        path = SNAPSHOT_DIR / snapshot_name
        path.write_text(json.dumps(_sanitize(payload), indent=2), encoding="utf-8")
        return payload

    def diagnose(self) -> dict:
        competition_wc = self.fetch_competition(use_id=False)
        competition_id = self.fetch_competition(use_id=True)
        matches = self.fetch_matches(use_id=False)
        self.fetch_matches(use_id=True)
        teams = self.fetch_teams(use_id=False)
        self.fetch_teams(use_id=True)
        standings = self.fetch_standings(use_id=False)
        self.fetch_standings(use_id=True)
        finished = self._request(f"competitions/{self.competition_code}/matches", "football_data_org_matches_finished_2026.json", {"season": self.season, "status": "FINISHED"})
        scheduled = self._request(f"competitions/{self.competition_code}/matches", "football_data_org_matches_scheduled_2026.json", {"season": self.season, "status": "SCHEDULED"})
        self._diagnose_optional_stage_filters()
        fixtures_df = self.normalize_fixtures(matches)
        teams_df = self.normalize_teams(teams)
        standings_df = self.normalize_standings(standings)
        if standings_df.empty:
            standings_df = self.compute_standings_from_completed_matches(fixtures_df)
        bracket_df = self.normalize_bracket(fixtures_df)
        self._save_normalized(fixtures_df, teams_df, standings_df, bracket_df)
        used_cached = False
        if fixtures_df.empty:
            cached_fixtures = _read(LIVE_STATE_DIR / "football_data_org_fixtures_normalized.csv")
            if not cached_fixtures.empty:
                fixtures_df = cached_fixtures
                teams_df = _read(LIVE_STATE_DIR / "football_data_org_teams_normalized.csv")
                standings_df = _read(LIVE_STATE_DIR / "football_data_org_standings_normalized.csv")
                bracket_df = _read(LIVE_STATE_DIR / "football_data_org_bracket_normalized.csv")
                used_cached = True
        summary = self.source_quality_summary(fixtures_df, teams_df, standings_df, bracket_df)
        summary["used_cached_normalized_data"] = used_cached
        if used_cached:
            summary["limitations"].append("Latest football-data.org request was rate limited; using previously saved normalized provider data.")
        self.write_provider_freshness(summary, fixtures_df)
        report = self._write_report(summary, fixtures_df, teams_df, standings_df)
        return {
            "provider": PROVIDER,
            "status": summary["provider_status"],
            "summary": summary,
            "report": report,
            "fixtures": fixtures_df,
            "teams": teams_df,
            "standings": standings_df,
            "bracket": bracket_df,
            "raw": {
                "competition_wc": competition_wc,
                "competition_2000": competition_id,
                "matches": matches,
                "teams": teams,
                "standings": standings,
                "finished": finished,
                "scheduled": scheduled,
            },
        }

    def fetch_competition(self, use_id: bool = False) -> dict:
        identifier = self.competition_id if use_id else self.competition_code
        return self._request(f"competitions/{identifier}", f"football_data_org_competition_{identifier.lower()}.json")

    def fetch_matches(self, use_id: bool = False) -> dict:
        identifier = self.competition_id if use_id else self.competition_code
        suffix = "2000" if use_id else "2026"
        return self._request(f"competitions/{identifier}/matches", f"football_data_org_matches_{suffix}.json", {"season": self.season})

    def fetch_teams(self, use_id: bool = False) -> dict:
        identifier = self.competition_id if use_id else self.competition_code
        suffix = "2000" if use_id else "2026"
        return self._request(f"competitions/{identifier}/teams", f"football_data_org_teams_{suffix}.json", {"season": self.season})

    def fetch_standings(self, use_id: bool = False) -> dict:
        identifier = self.competition_id if use_id else self.competition_code
        suffix = "2000" if use_id else "2026"
        return self._request(f"competitions/{identifier}/standings", f"football_data_org_standings_{suffix}.json", {"season": self.season})

    def fetch_bracket(self) -> dict:
        return self.fetch_matches(use_id=False)

    def normalize_fixtures(self, raw_data: dict) -> pd.DataFrame:
        rows = []
        for match in raw_data.get("matches", []) if isinstance(raw_data, dict) else []:
            home = match.get("homeTeam") or {}
            away = match.get("awayTeam") or {}
            score = match.get("score") or {}
            full_time = score.get("fullTime") or {}
            penalties = score.get("penalties") or {}
            status = str(match.get("status") or "UNKNOWN").upper()
            # Recover from a malformed/missing provider status (e.g. a timestamp returned in
            # the status field): a match carrying a decisive full-time result is finished, so
            # normalize it to FINISHED rather than treating a completed match as unplayed.
            if status not in COMPLETED and status not in LIVE and _result_is_decided(score, full_time, penalties):
                status = "FINISHED"
            stage_raw = str(match.get("stage") or "UNKNOWN").upper()
            stage = STAGE_MAP.get(stage_raw, "Unknown" if stage_raw == "UNKNOWN" else stage_raw.replace("_", " ").title())
            winner = self._winner(match, home, away, full_time, penalties, status)
            rows.append(
                {
                    "fixture_id": match.get("id"),
                    "match_id": f"football_data_org_{match.get('id')}",
                    "date": match.get("utcDate"),
                    "round": match.get("stage") or match.get("group"),
                    "stage": stage,
                    "group": match.get("group"),
                    "team_a": home.get("name"),
                    "team_b": away.get("name"),
                    "team_a_id": home.get("id"),
                    "team_b_id": away.get("id"),
                    "team_a_goals": full_time.get("home"),
                    "team_b_goals": full_time.get("away"),
                    "team_a_penalty_goals": penalties.get("home"),
                    "team_b_penalty_goals": penalties.get("away"),
                    "winner": winner,
                    "status_short": status,
                    "status_long": status,
                    "elapsed": match.get("minute"),
                    "is_completed": status in COMPLETED,
                    "is_live": status in LIVE,
                    "is_scheduled": status in SCHEDULED,
                    "is_knockout": stage != "Group Stage",
                    "venue": "",
                    "city": "",
                    "country": "",
                    "source": PROVIDER,
                    "provider": PROVIDER,
                    "last_updated": match.get("lastUpdated") or now_utc_iso(),
                }
            )
        return pd.DataFrame(rows, columns=FIXTURE_COLUMNS)

    def normalize_teams(self, raw_data: dict) -> pd.DataFrame:
        rows = []
        for team in raw_data.get("teams", []) if isinstance(raw_data, dict) else []:
            area = team.get("area") or {}
            rows.append(
                {
                    "team_id": team.get("id"),
                    "team": team.get("name"),
                    "short_name": team.get("shortName"),
                    "tla": team.get("tla"),
                    "crest": team.get("crest"),
                    "country": area.get("name"),
                    "source": PROVIDER,
                    "provider": PROVIDER,
                    "last_updated": team.get("lastUpdated") or now_utc_iso(),
                }
            )
        return pd.DataFrame(rows, columns=TEAM_COLUMNS)

    def normalize_standings(self, raw_data: dict) -> pd.DataFrame:
        rows = []
        for standing in raw_data.get("standings", []) if isinstance(raw_data, dict) else []:
            group = standing.get("group") or standing.get("stage") or standing.get("type")
            for entry in standing.get("table", []) or []:
                team = entry.get("team") or {}
                rows.append(
                    {
                        "group": group,
                        "rank": entry.get("position"),
                        "team": team.get("name"),
                        "team_id": team.get("id"),
                        "played": entry.get("playedGames"),
                        "wins": entry.get("won"),
                        "draws": entry.get("draw"),
                        "losses": entry.get("lost"),
                        "goals_for": entry.get("goalsFor"),
                        "goals_against": entry.get("goalsAgainst"),
                        "goal_difference": entry.get("goalDifference"),
                        "points": entry.get("points"),
                        "form": entry.get("form"),
                        "qualification_status": entry.get("position") or "unknown",
                        "source": PROVIDER,
                        "provider": PROVIDER,
                        "last_updated": now_utc_iso(),
                    }
                )
        return pd.DataFrame(rows, columns=STANDING_COLUMNS)

    def compute_standings_from_completed_matches(self, fixtures: pd.DataFrame) -> pd.DataFrame:
        rows: dict[tuple[str, str], dict] = {}
        if fixtures.empty:
            return pd.DataFrame(columns=STANDING_COLUMNS)
        completed = coerce_bool_series(fixtures.get("is_completed", pd.Series(dtype=bool)))
        group_matches = fixtures[fixtures.get("stage", pd.Series(dtype=str)).eq("Group Stage") & completed]
        for _, match in group_matches.iterrows():
            group = match.get("group") or "Group Stage"
            team_a = match.get("team_a")
            team_b = match.get("team_b")
            if pd.isna(team_a) or pd.isna(team_b):
                continue
            for team, team_id in [(team_a, match.get("team_a_id")), (team_b, match.get("team_b_id"))]:
                rows.setdefault(
                    (str(group), str(team)),
                    {
                        "group": group,
                        "rank": 0,
                        "team": team,
                        "team_id": team_id,
                        "played": 0,
                        "wins": 0,
                        "draws": 0,
                        "losses": 0,
                        "goals_for": 0,
                        "goals_against": 0,
                        "goal_difference": 0,
                        "points": 0,
                        "form": "",
                        "qualification_status": "unknown",
                        "source": "computed_from_football_data_org_matches",
                        "provider": PROVIDER,
                        "last_updated": now_utc_iso(),
                    },
                )
            ga = pd.to_numeric(match.get("team_a_goals"), errors="coerce")
            gb = pd.to_numeric(match.get("team_b_goals"), errors="coerce")
            if pd.isna(ga) or pd.isna(gb):
                continue
            a = rows[(str(group), str(team_a))]
            b = rows[(str(group), str(team_b))]
            a["played"] += 1
            b["played"] += 1
            a["goals_for"] += int(ga)
            a["goals_against"] += int(gb)
            b["goals_for"] += int(gb)
            b["goals_against"] += int(ga)
            if ga > gb:
                a["wins"] += 1
                b["losses"] += 1
                a["points"] += 3
            elif gb > ga:
                b["wins"] += 1
                a["losses"] += 1
                b["points"] += 3
            else:
                a["draws"] += 1
                b["draws"] += 1
                a["points"] += 1
                b["points"] += 1
        df = pd.DataFrame(rows.values())
        if df.empty:
            return df
        df["goal_difference"] = df["goals_for"] - df["goals_against"]
        ranked = []
        for group, group_df in df.groupby("group", sort=True):
            ordered = group_df.sort_values(["points", "goal_difference", "goals_for", "team"], ascending=[False, False, False, True]).copy()
            ordered["rank"] = range(1, len(ordered) + 1)
            ranked.append(ordered)
        output = pd.concat(ranked, ignore_index=True) if ranked else df
        for column in STANDING_COLUMNS:
            if column not in output:
                output[column] = pd.NA
        return output[STANDING_COLUMNS]

    def normalize_bracket(self, raw_data) -> pd.DataFrame:
        fixtures = raw_data if isinstance(raw_data, pd.DataFrame) else self.normalize_fixtures(raw_data)
        rows = []
        knockout = fixtures[coerce_bool_series(fixtures.get("is_knockout", pd.Series(dtype=bool)))] if not fixtures.empty else pd.DataFrame()
        for _, row in knockout.iterrows():
            is_tbd = is_tbd_team(row.get("team_a")) or is_tbd_team(row.get("team_b"))
            rows.append(
                {
                    "fixture_id": row.get("fixture_id"),
                    "match_id": row.get("match_id"),
                    "round": row.get("round"),
                    "stage": row.get("stage"),
                    "team_a": row.get("team_a"),
                    "team_b": row.get("team_b"),
                    "winner": row.get("winner"),
                    "status": row.get("status_short"),
                    "is_completed": row.get("is_completed"),
                    "is_live": row.get("is_live"),
                    "is_scheduled": row.get("is_scheduled"),
                    "is_tbd": is_tbd,
                    "bracket_source": "football_data_org_scheduled_tbd" if is_tbd else "football_data_org_live",
                    "provider": PROVIDER,
                    "last_updated": row.get("last_updated"),
                }
            )
        return pd.DataFrame(rows, columns=BRACKET_COLUMNS)

    def source_quality_summary(
        self,
        fixtures_df: pd.DataFrame | None = None,
        teams_df: pd.DataFrame | None = None,
        standings_df: pd.DataFrame | None = None,
        bracket_df: pd.DataFrame | None = None,
    ) -> dict:
        fixtures = fixtures_df if fixtures_df is not None else _read(LIVE_STATE_DIR / "football_data_org_fixtures_normalized.csv")
        teams = teams_df if teams_df is not None else _read(LIVE_STATE_DIR / "football_data_org_teams_normalized.csv")
        standings = standings_df if standings_df is not None else _read(LIVE_STATE_DIR / "football_data_org_standings_normalized.csv")
        bracket = bracket_df if bracket_df is not None else _read(LIVE_STATE_DIR / "football_data_org_bracket_normalized.csv")
        completed = int(coerce_bool_series(fixtures.get("is_completed", pd.Series(dtype=bool))).sum()) if not fixtures.empty else 0
        live = int(coerce_bool_series(fixtures.get("is_live", pd.Series(dtype=bool))).sum()) if not fixtures.empty else 0
        scheduled = int(coerce_bool_series(fixtures.get("is_scheduled", pd.Series(dtype=bool))).sum()) if not fixtures.empty else 0
        limitations = []
        provider_status = "unknown_error"
        endpoint_statuses = set(str(value) for value in self.last_statuses.values())
        payload_text = json.dumps(_sanitize(self.last_payloads), default=str).lower()[:5000]
        if not self.credentials_available():
            provider_status = "credentials_missing"
            limitations.append("FOOTBALL_DATA_ORG_KEY is missing.")
        elif fixtures.empty and ("401" in endpoint_statuses or "unauthorized" in payload_text):
            provider_status = "unauthorized"
            limitations.append("Token was rejected or unauthorized.")
        elif fixtures.empty and "429" in endpoint_statuses:
            provider_status = "rate_limited"
            limitations.append("Rate limit reached before core match data could be loaded.")
        elif fixtures.empty and "403" in endpoint_statuses:
            provider_status = "forbidden_plan"
            limitations.append("Endpoint is forbidden for this token/plan.")
        elif fixtures.empty:
            provider_status = "no_2026_rows"
            limitations.append("No 2026 match rows were returned.")
        elif completed > 0 and not standings.empty:
            provider_status = "available_true_live"
        elif completed > 0 or live > 0:
            provider_status = "available_partial_live"
            limitations.append("Standings or bracket may still need computed/fallback support.")
        elif scheduled > 0:
            provider_status = "available_schedule_only"
            limitations.append("Matches exist, but no completed/live 2026 rows were returned.")
        else:
            provider_status = "endpoint_error"
            limitations.append("Endpoints returned data that could not support current-state forecasting.")
        if not fixtures.empty and "429" in endpoint_statuses:
            limitations.append("One or more optional diagnostic endpoints were rate limited after core data loaded.")
        if not fixtures.empty and "403" in endpoint_statuses:
            limitations.append("One or more optional diagnostic endpoints were forbidden after core data loaded.")
        stages = sorted([str(value) for value in fixtures.get("stage", pd.Series(dtype=str)).dropna().unique()]) if not fixtures.empty else []
        groups = sorted([str(value) for value in fixtures.get("group", pd.Series(dtype=str)).dropna().unique() if str(value).strip()]) if not fixtures.empty else []
        return {
            "provider": PROVIDER,
            "credentials_available": self.credentials_available(),
            "provider_status": provider_status,
            "fixture_rows": len(fixtures),
            "completed_rows": completed,
            "live_rows": live,
            "scheduled_rows": scheduled,
            "teams_rows": len(teams),
            "standings_rows": len(standings),
            "bracket_rows": len(bracket),
            "stages_detected": stages,
            "groups_detected": groups,
            "can_support_true_live": provider_status == "available_true_live",
            "can_support_partial_live": provider_status in {"available_true_live", "available_partial_live", "available_schedule_only"},
            "limitations": limitations,
            "used_cached_normalized_data": False,
            "used_saved_snapshot_data": False,
        }

    def write_provider_freshness(self, summary: dict, fixtures: pd.DataFrame) -> str:
        """Honest, structured freshness metadata for the latest provider interaction.

        data_source_mode distinguishes fresh_api / cached_normalized / saved_snapshot /
        unavailable so stale data can never silently pass as fresh. The quality gate
        stays the sole authority on forecast mode.
        """
        matches_status = str(self.last_statuses.get("football_data_org_matches_2026.json", "not_run"))
        rate_limited = "429" in {str(v) for v in self.last_statuses.values()}
        if summary.get("used_saved_snapshot_data"):
            mode = "saved_snapshot"
        elif summary.get("used_cached_normalized_data"):
            mode = "cached_normalized"
        elif matches_status == "200" and not fixtures.empty:
            mode = "fresh_api"
        elif fixtures.empty:
            mode = "unavailable"
        else:
            mode = "cached_normalized"
        normalized_path = LIVE_STATE_DIR / "football_data_org_fixtures_normalized.csv"
        normalized_at = None
        age_minutes = None
        if normalized_path.exists():
            mtime = datetime.fromtimestamp(normalized_path.stat().st_mtime, tz=timezone.utc)
            normalized_at = mtime.replace(microsecond=0).isoformat()
            age_minutes = round((datetime.now(timezone.utc) - mtime).total_seconds() / 60, 1)
        completed = int(coerce_bool_series(fixtures.get("is_completed", pd.Series(dtype=bool))).sum()) if not fixtures.empty else 0
        payload = {
            "provider": PROVIDER,
            "request_status": matches_status,
            "data_source_mode": mode,
            "fetched_at": now_utc_iso() if mode == "fresh_api" else None,
            "normalized_at": normalized_at,
            "fixture_row_count": int(len(fixtures)),
            "completed_fixture_count": completed,
            "cache_used": mode == "cached_normalized",
            "snapshot_used": mode == "saved_snapshot",
            "data_age_minutes": 0.0 if mode == "fresh_api" else age_minutes,
            "rate_limited": rate_limited,
            "provider_status": summary.get("provider_status"),
        }
        path = LIVE_STATE_DIR / "live_provider_freshness.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return str(path)

    def _save_normalized(self, fixtures: pd.DataFrame, teams: pd.DataFrame, standings: pd.DataFrame, bracket: pd.DataFrame) -> None:
        LIVE_STATE_DIR.mkdir(parents=True, exist_ok=True)
        _write_normalized_csv(LIVE_STATE_DIR / "football_data_org_fixtures_normalized.csv", fixtures)
        _write_normalized_csv(LIVE_STATE_DIR / "football_data_org_teams_normalized.csv", teams)
        _write_normalized_csv(LIVE_STATE_DIR / "football_data_org_standings_normalized.csv", standings)
        _write_normalized_csv(LIVE_STATE_DIR / "football_data_org_bracket_normalized.csv", bracket)

    def _write_report(self, summary: dict, fixtures: pd.DataFrame, teams: pd.DataFrame, standings: pd.DataFrame) -> str:
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        phase = detect_current_tournament_phase(fixtures)["current_phase"] if not fixtures.empty else "unknown"
        status = fixtures.get("status_short", pd.Series(dtype=str)).astype(str) if not fixtures.empty else pd.Series(dtype=str)
        result_set = self.last_payloads.get("football_data_org_matches_2026.json", {}).get("resultSet", {})
        report_path = REPORT_DIR / "football_data_org_provider_report.md"
        lines = [
            "# football-data.org Provider Report",
            "",
            f"- Provider: {PROVIDER}",
            f"- Token present: {'yes' if self.credentials_available() else 'no'}",
            f"- Base URL: {BASE_URL}",
            f"- Competition code used: {self.competition_code}",
            f"- Competition ID used: {self.competition_id}",
            f"- Competition metadata status: WC={self.last_statuses.get('football_data_org_competition_wc.json', 'not_run')}, 2000={self.last_statuses.get('football_data_org_competition_2000.json', 'not_run')}",
            f"- Matches endpoint HTTP status: {self.last_statuses.get('football_data_org_matches_2026.json', 'not_run')}",
            f"- Matches row count: {len(fixtures)}",
            f"- resultSet count: {result_set.get('count', 'unknown') if isinstance(result_set, dict) else 'unknown'}",
            f"- Finished matches count: {int(status.eq('FINISHED').sum())}",
            f"- Scheduled matches count: {int(status.isin(['TIMED', 'SCHEDULED']).sum())}",
            f"- Live/in-play matches count: {int(status.isin(['IN_PLAY', 'PAUSED']).sum())}",
            f"- Teams endpoint HTTP status: {self.last_statuses.get('football_data_org_teams_2026.json', 'not_run')}",
            f"- Teams row count: {len(teams)}",
            f"- Standings endpoint HTTP status: {self.last_statuses.get('football_data_org_standings_2026.json', 'not_run')}",
            f"- Standings row count: {len(standings)}",
            f"- Normalized data source: {_normalized_data_source(summary)}",
            f"- Stages detected: {', '.join(summary['stages_detected']) if summary['stages_detected'] else 'none'}",
            f"- Groups detected: {', '.join(summary['groups_detected']) if summary['groups_detected'] else 'none'}",
            f"- Current phase detected: {phase}",
            f"- Can support live forecast: {'yes' if summary['can_support_true_live'] else 'partial' if summary['can_support_partial_live'] else 'no'}",
            f"- Provider status: {summary['provider_status']}",
            "",
            "## Limitations",
            "",
        ]
        lines.extend(f"- {item}" for item in summary["limitations"]) if summary["limitations"] else lines.append("- None")
        lines.extend(["", "## Exact Next Action", "", _next_action(summary), "", "No API token is printed or saved."])
        report_path.write_text("\n".join(lines), encoding="utf-8")
        return str(report_path)

    def _winner(self, match: dict, home: dict, away: dict, full_time: dict, penalties: dict, status: str):
        score = match.get("score") or {}
        winner = score.get("winner")
        if status != "FINISHED":
            return None
        if winner == "HOME_TEAM":
            return home.get("name")
        if winner == "AWAY_TEAM":
            return away.get("name")
        hg = full_time.get("home")
        ag = full_time.get("away")
        if hg is not None and ag is not None and hg != ag:
            return home.get("name") if hg > ag else away.get("name")
        hp = penalties.get("home")
        ap = penalties.get("away")
        if hp is not None and ap is not None and hp != ap:
            return home.get("name") if hp > ap else away.get("name")
        return "Draw" if winner == "DRAW" else None

    def _diagnose_optional_stage_filters(self) -> None:
        for stage in ["GROUP_STAGE", "LAST_32", "ROUND_OF_16", "QUARTER_FINALS", "SEMI_FINALS", "FINAL"]:
            self._request(
                f"competitions/{self.competition_code}/matches",
                f"football_data_org_matches_{stage.lower()}_2026.json",
                {"season": self.season, "stage": stage},
            )


def _result_is_decided(score: dict, full_time: dict, penalties: dict) -> bool:
    """True when a match carries a decisive final result, regardless of its status string."""
    if (score or {}).get("winner") in {"HOME_TEAM", "AWAY_TEAM", "DRAW"}:
        return True
    if full_time.get("home") is not None and full_time.get("away") is not None:
        return True
    if penalties.get("home") is not None and penalties.get("away") is not None:
        return True
    return False


def _sanitize(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {key: _sanitize(value) for key, value in payload.items() if key.lower() not in {"token", "x-auth-token"}}
    if isinstance(payload, list):
        return [_sanitize(item) for item in payload]
    return payload


def _read(path) -> pd.DataFrame:
    try:
        return pd.read_csv(path) if path.exists() else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


def _write_normalized_csv(path, df: pd.DataFrame) -> None:
    existing = _read(path)
    if df.empty and not existing.empty:
        return
    df.to_csv(path, index=False)


def _normalized_data_source(summary: dict) -> str:
    if summary.get("used_cached_normalized_data"):
        return "cached normalized file"
    if summary.get("used_saved_snapshot_data"):
        return "saved provider snapshot"
    return "latest provider response"


def _next_action(summary: dict) -> str:
    status = summary["provider_status"]
    if status == "credentials_missing":
        return "Add FOOTBALL_DATA_ORG_KEY to local .env, then rerun diagnose-football-data-org."
    if status in {"unauthorized", "forbidden_plan"}:
        return "Check token permissions and football-data.org plan access for World Cup 2026."
    if status == "no_2026_rows":
        return "Keep the quality gate in fallback/insufficient mode until football-data.org exposes 2026 rows."
    if status == "available_schedule_only":
        return "Use the provider as schedule-only; do not label forecasts true-live until completed/live rows exist."
    if status in {"available_true_live", "available_partial_live"}:
        return "Run select-live-provider and live-quality-gate to decide whether forecasts are allowed."
    return "Review snapshots and provider report before using this provider."
