"""Zafronix World Cup API provider.

ROLE: SECONDARY historical / squad / World Cup enrichment provider.

This provider is deliberately NOT a live-tournament-truth source. football-data.org
remains the primary authoritative live-tournament-state provider (fixtures, completed
results, standings, live bracket, tournament lifecycle). Zafronix is used only to enrich
the project with prior World Cup history and per-tournament squad rosters for offline,
leakage-safe feature engineering.

Design (fetch -> validate -> snapshot; never inside model/simulation loops):
- Auth via ``X-API-Key`` header (key read from env, never logged / never snapshotted).
- Bounded retries with Retry-After support and conditional requests via ETag caching.
- Sanitized JSON snapshots written under ``data/raw/zafronix/`` (gitignored, bulky).
- Last-known-good snapshots preserved; stale reads are disclosed, never passed as fresh.
- A single ``GET /tournaments/{year}`` returns the full tournament (metadata + every team
  with finalPosition/groupStage/knockoutPath + embedded 26-player squad), so the entire
  historical dataset is fetched in ~23 requests — no per-match or per-player fan-out.
"""

from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from src.config import DATA_DIR, ZAFRONIX_API_KEY, ZAFRONIX_BASE_URL
from src.utils.dates import now_utc_iso

PROVIDER = "zafronix"
PROVIDER_ROLE = "historical_and_squad_enrichment"
RAW_DIR = DATA_DIR / "raw" / "zafronix"
SNAPSHOT_DIR = RAW_DIR / "snapshots"
CACHE_PATH = RAW_DIR / "etag_cache.json"

# Sensitive keys that must never be written to a snapshot, log, or report.
# ``keyprefix`` is included because /me/usage echoes a partial key prefix — key material
# (even truncated) must not be persisted to a tracked artifact.
_SECRET_KEYS = {"x-api-key", "api_key", "apikey", "authorization", "token", "key", "secret", "keyprefix"}


class ZafronixProvider:
    """Client for the Zafronix World Cup API (enrichment-only)."""

    def __init__(
        self,
        api_key: str | None = ZAFRONIX_API_KEY,
        base_url: str = ZAFRONIX_BASE_URL,
        max_retries: int = 3,
        timeout: int = 40,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.timeout = timeout
        self.role = PROVIDER_ROLE
        self.last_statuses: dict[str, int | str] = {}
        self.last_rate_limit: dict[str, str] = {}

    # -- identity -------------------------------------------------------- #
    def provider_name(self) -> str:
        return PROVIDER

    def credentials_available(self) -> bool:
        return bool(self.api_key)

    def _headers(self, etag: str | None = None) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        if etag:
            headers["If-None-Match"] = etag
        return headers

    # -- cache ----------------------------------------------------------- #
    def _load_cache(self) -> dict[str, dict]:
        if CACHE_PATH.exists():
            try:
                return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_cache(self, cache: dict[str, dict]) -> None:
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text(json.dumps(cache, indent=2), encoding="utf-8")

    # -- request --------------------------------------------------------- #
    def get(self, path: str, snapshot_name: str | None = None, use_cache: bool = True) -> dict:
        """GET ``path`` (conditional if cached), snapshot the sanitized payload, return it.

        Returns a dict envelope: ``{"ok", "status", "data", "from_cache", "stale", "path"}``.
        Never raises on network/HTTP failure — falls back to last-known-good snapshot.
        """
        SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        snapshot_name = snapshot_name or (path.strip("/").replace("/", "_") or "root") + ".json"
        snapshot_path = SNAPSHOT_DIR / snapshot_name
        cache = self._load_cache() if use_cache else {}
        etag = cache.get(path, {}).get("etag") if use_cache else None

        if not self.credentials_available():
            self.last_statuses[path] = "missing_key"
            return self._last_known_good(path, snapshot_path, status="missing_key")

        url = f"{self.base_url}/{path.lstrip('/')}"
        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = requests.get(url, headers=self._headers(etag), timeout=self.timeout)
                status = resp.status_code
                self.last_statuses[path] = status
                self.last_rate_limit[path] = resp.headers.get("X-RateLimit-Remaining", "")
                if status == 304:  # not modified — reuse snapshot on disk
                    return self._last_known_good(path, snapshot_path, status=304, from_cache=True)
                if status == 429:
                    retry_after = _to_float(resp.headers.get("Retry-After"))
                    wait = retry_after if (retry_after and 0 < retry_after <= 20) else min(2 ** attempt, 20)
                    if attempt < self.max_retries:
                        time.sleep(wait)
                        continue
                    return self._last_known_good(path, snapshot_path, status=429)
                if status >= 500 and attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 10))
                    continue
                try:
                    data = resp.json()
                except Exception:
                    data = {"raw_text": resp.text[:500]}
                if status == 200:
                    sanitized = _sanitize(data)
                    snapshot_path.write_text(json.dumps(sanitized, indent=2), encoding="utf-8")
                    new_etag = resp.headers.get("ETag")
                    if use_cache and new_etag:
                        cache[path] = {"etag": new_etag, "fetched_at": now_utc_iso(),
                                       "hash": _hash(sanitized)}
                        self._save_cache(cache)
                    return {"ok": True, "status": 200, "data": sanitized, "from_cache": False,
                            "stale": False, "path": str(snapshot_path)}
                # 4xx other than 429 — do not retry; surface last-known-good if present
                last_error = {"status": status, "body": _sanitize(data)}
                return self._last_known_good(path, snapshot_path, status=status, error=last_error)
            except requests.RequestException as exc:
                last_error = {"error": str(exc)}
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 10))
                    continue
                self.last_statuses[path] = "request_failed"
        return self._last_known_good(path, snapshot_path, status="request_failed", error=last_error)

    def _last_known_good(self, path: str, snapshot_path: Path, status, from_cache: bool = False,
                         error: dict | None = None) -> dict:
        if snapshot_path.exists():
            try:
                data = json.loads(snapshot_path.read_text(encoding="utf-8"))
            except Exception:
                data = None
            if data is not None:
                stale = not (status == 200 or (status == 304 and from_cache))
                return {"ok": True, "status": status, "data": data, "from_cache": True,
                        "stale": stale, "path": str(snapshot_path), "error": error}
        return {"ok": False, "status": status, "data": None, "from_cache": False,
                "stale": True, "path": str(snapshot_path), "error": error}

    # -- typed fetch helpers -------------------------------------------- #
    def fetch_health(self) -> dict:
        return self.get("/health", "health.json", use_cache=False)

    def fetch_usage(self) -> dict:
        return self.get("/me/usage", "me_usage.json", use_cache=False)

    def fetch_tournaments_index(self) -> dict:
        return self.get("/tournaments", "tournaments_index.json")

    def fetch_tournament(self, year: int) -> dict:
        return self.get(f"/tournaments/{year}", f"tournament_{year}.json")

    def tournament_years(self) -> list[int]:
        idx = self.fetch_tournaments_index()
        rows = idx.get("data") if isinstance(idx.get("data"), list) else []
        years = []
        for row in rows or []:
            year = row.get("year")
            if isinstance(year, int) and 1900 <= year <= 2100:
                years.append(year)
        return sorted(set(years))

    # -- diagnostics ----------------------------------------------------- #
    def diagnose(self) -> dict:
        """Health + coverage probe. Never prints or returns the API key."""
        health = self.fetch_health()
        usage = self.fetch_usage()
        years = self.tournament_years()
        reachable = bool(health.get("ok")) and health.get("status") in (200, 304)
        health_data = health.get("data") or {}
        return {
            "provider": PROVIDER,
            "role": self.role,
            "authentication_available": self.credentials_available(),
            "api_reachable": reachable,
            "base_url": self.base_url,
            "health_ok": bool(health_data.get("ok")) if isinstance(health_data, dict) else False,
            "tournaments_loaded": health_data.get("tournamentsLoaded") if isinstance(health_data, dict) else None,
            "stadium_count": health_data.get("stadiumCount") if isinstance(health_data, dict) else None,
            "match_count": health_data.get("matchCount") if isinstance(health_data, dict) else None,
            "years_available": years,
            "year_count": len(years),
            "has_2026": 2026 in years,
            "rate_limit_remaining": self.last_rate_limit.get("/tournaments", ""),
            "usage": _sanitize(usage.get("data")) if usage.get("ok") else None,
            "checked_at": now_utc_iso(),
        }


# --------------------------------------------------------------------------- #
# module helpers
# --------------------------------------------------------------------------- #

def _sanitize(payload: Any) -> Any:
    if isinstance(payload, dict):
        return {k: _sanitize(v) for k, v in payload.items() if str(k).lower() not in _SECRET_KEYS}
    if isinstance(payload, list):
        return [_sanitize(item) for item in payload]
    return payload


def _hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]


def _to_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
