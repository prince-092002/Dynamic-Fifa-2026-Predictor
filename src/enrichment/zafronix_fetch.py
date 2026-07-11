"""Fetch bounded Zafronix World Cup datasets and run provider diagnostics.

One ``GET /tournaments/{year}`` returns the full tournament (metadata + teams with
finalPosition/knockoutPath + embedded squads), so the entire historical corpus is
fetched in ~1 + N(year) requests. Snapshots are sanitized and gitignored.
"""

from __future__ import annotations

import json

from src.enrichment.zafronix_config import REPORT_DIR, ensure_dirs
from src.live_state.providers.zafronix_provider import ZafronixProvider
from src.utils.dates import now_utc_iso


def diagnose_zafronix() -> dict:
    """Run provider diagnostics and write a machine-readable + human-readable report."""
    ensure_dirs()
    provider = ZafronixProvider()
    diag = provider.diagnose()
    (REPORT_DIR / "zafronix_provider_diagnostic.json").write_text(json.dumps(diag, indent=2), encoding="utf-8")
    _write_diagnostic_md(diag)
    return diag


def fetch_zafronix(years: list[int] | None = None) -> dict:
    """Fetch every tournament snapshot and record a schema/field inventory."""
    ensure_dirs()
    provider = ZafronixProvider()
    diag = provider.diagnose()
    (REPORT_DIR / "zafronix_provider_diagnostic.json").write_text(json.dumps(diag, indent=2), encoding="utf-8")
    _write_diagnostic_md(diag)

    if not provider.credentials_available():
        return {"status": "missing_key", "fetched": 0, "diagnostic": diag}

    target_years = years or diag.get("years_available") or []
    results = []
    schema_inventory: dict = {"endpoints": {}, "generated_at": now_utc_iso()}
    for year in target_years:
        env = provider.fetch_tournament(year)
        ok = bool(env.get("ok")) and env.get("data") is not None
        results.append({
            "year": year, "ok": ok, "status": env.get("status"),
            "from_cache": env.get("from_cache"), "stale": env.get("stale"),
        })
        if ok and "tournaments/{year}" not in schema_inventory["endpoints"]:
            schema_inventory["endpoints"]["tournaments/{year}"] = _inventory(env["data"])
    # index endpoint schema
    idx = provider.fetch_tournaments_index()
    if idx.get("ok") and isinstance(idx.get("data"), list) and idx["data"]:
        schema_inventory["endpoints"]["tournaments"] = {"item_fields": sorted(idx["data"][0].keys())}

    (REPORT_DIR / "zafronix_schema_inventory.json").write_text(json.dumps(schema_inventory, indent=2), encoding="utf-8")
    summary = {
        "status": "ok" if any(r["ok"] for r in results) else "failed",
        "years_requested": target_years,
        "fetched": sum(1 for r in results if r["ok"]),
        "failed": [r["year"] for r in results if not r["ok"]],
        "results": results,
        "diagnostic": diag,
    }
    (REPORT_DIR / "zafronix_fetch_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _inventory(tournament_payload: dict) -> dict:
    """Record the field names actually present in a tournament payload (no values)."""
    tour = tournament_payload.get("tournament", {}) if isinstance(tournament_payload, dict) else {}
    teams = tournament_payload.get("teams", []) if isinstance(tournament_payload, dict) else []
    team_fields, player_fields = set(), set()
    for team in teams:
        team_fields.update(team.keys())
        for player in team.get("squad", []) or []:
            player_fields.update(player.keys())
    return {
        "top_level_fields": sorted(tournament_payload.keys()) if isinstance(tournament_payload, dict) else [],
        "tournament_fields": sorted(tour.keys()) if isinstance(tour, dict) else [],
        "team_fields": sorted(team_fields),
        "player_fields": sorted(player_fields),
    }


def _write_diagnostic_md(diag: dict) -> None:
    lines = [
        "# Zafronix Provider Diagnostic",
        "",
        f"- Provider: {diag.get('provider')} (role: {diag.get('role')})",
        f"- Authentication available: {'yes' if diag.get('authentication_available') else 'no'} (key never printed)",
        f"- API reachable: {diag.get('api_reachable')}",
        f"- Base URL: {diag.get('base_url')}",
        f"- Health ok: {diag.get('health_ok')}",
        f"- Tournaments loaded (health): {diag.get('tournaments_loaded')}",
        f"- Stadiums (health): {diag.get('stadium_count')}",
        f"- Matches (health): {diag.get('match_count')}",
        f"- Tournament years available: {diag.get('year_count')} ({min(diag['years_available']) if diag.get('years_available') else 'n/a'}–{max(diag['years_available']) if diag.get('years_available') else 'n/a'})",
        f"- 2026 present: {diag.get('has_2026')}",
        f"- Rate-limit remaining (tournaments): {diag.get('rate_limit_remaining')}",
        f"- Checked at: {diag.get('checked_at')}",
        "",
        "Role note: Zafronix is a **secondary historical/squad enrichment** provider. "
        "football-data.org remains the primary authoritative live-tournament-state provider; "
        "Zafronix never overwrites live truth.",
        "",
        "No API key is printed or stored in this report.",
    ]
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "zafronix_provider_diagnostic.md").write_text("\n".join(lines), encoding="utf-8")
