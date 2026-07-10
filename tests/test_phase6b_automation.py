"""Phase 6B automation tests: commit safety, fail-closed publication, history dedup.

All tests run against temporary directories; production outputs are never modified.
"""

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.public_export import commit_safety  # noqa: E402
from src.public_export.commit_safety import classify_changed_files, is_allowlisted, scan_files_for_secrets  # noqa: E402


class TestCommitAllowlist:
    def test_public_data_json_is_allowlisted(self):
        assert is_allowlisted("public_data/champion_forecast.json")
        assert is_allowlisted("public_data/latest_overview.json")

    def test_history_and_manifest_are_allowlisted(self):
        assert is_allowlisted("outputs/live_state/champion_probability_history.csv")
        assert is_allowlisted("outputs/live_state/latest_live_run_manifest.json")
        assert is_allowlisted("outputs/reports/portfolio/latest_portfolio_refresh_manifest.json")

    def test_secrets_and_snapshots_are_never_allowlisted(self):
        assert not is_allowlisted(".env")
        assert not is_allowlisted("kaggle.json")
        assert not is_allowlisted("outputs/live_state/provider_snapshots/football_data_org/football_data_org_matches_2026.json")
        assert not is_allowlisted("outputs/live_state/api_football_live_fixtures.json")
        assert not is_allowlisted("website/node_modules/left-pad/index.js")

    def test_source_code_is_not_allowlisted(self):
        for path in ["src/live_state/live_pipeline.py", "main.py", "website/app/page.tsx", "dashboard/app.py"]:
            assert not is_allowlisted(path)

    def test_classification_buckets(self):
        result = classify_changed_files(
            [
                "public_data/teams.json",  # commit
                "outputs/live_state/live_champion_probabilities.csv",  # commit
                "data/processed/matches_master.csv",  # tolerated volatile
                "outputs/reports/live_state/live_validation_report.md",  # tolerated volatile
                "src/config.py",  # unexpected!
            ]
        )
        assert "public_data/teams.json" in result["to_commit"]
        assert "outputs/live_state/live_champion_probabilities.csv" in result["to_commit"]
        assert "data/processed/matches_master.csv" in result["tolerated"]
        assert result["unexpected"] == ["src/config.py"]

    def test_forbidden_files_are_tolerated_but_never_committed(self):
        """Snapshots regenerate on every refresh: they must not block automation,
        and they must never be staged for commit."""
        result = classify_changed_files(["outputs/live_state/provider_snapshots/football_data_org/raw.json"])
        assert not result["to_commit"], "sanitized snapshots must never be auto-committed"
        assert not result["unexpected"], "routine snapshot regeneration must not block automation"
        assert result["tolerated"] == ["outputs/live_state/provider_snapshots/football_data_org/raw.json"]

    def test_windows_path_separators_normalized(self):
        assert is_allowlisted("public_data\\teams.json")


class TestSecretAndPathScans:
    def test_secret_hit_detected(self, tmp_path):
        (tmp_path / "leaky.json").write_text('{"token": "SUPERSECRETVALUE123"}', encoding="utf-8")
        result = scan_files_for_secrets(["leaky.json"], base_dir=tmp_path, secrets=["SUPERSECRETVALUE123"])
        assert result["secret_hits"] == ["leaky.json"] and not result["clean"]

    def test_private_path_hit_detected(self, tmp_path):
        (tmp_path / "pathy.json").write_text('{"report": "C:\\\\Users\\\\someone\\\\project"}', encoding="utf-8")
        result = scan_files_for_secrets(["pathy.json"], base_dir=tmp_path, secrets=[])
        assert result["private_path_hits"] == ["pathy.json"]

    def test_clean_file_passes(self, tmp_path):
        (tmp_path / "clean.json").write_text('{"team": "France", "probability": 0.29}', encoding="utf-8")
        result = scan_files_for_secrets(["clean.json"], base_dir=tmp_path, secrets=["SUPERSECRETVALUE123"])
        assert result["clean"]


class TestFailClosedPublication:
    def test_invalid_staged_exports_preserve_last_good(self, tmp_path, monkeypatch):
        """A failing staged validation must never replace existing public data."""
        from src.public_export import publish

        fake_public = tmp_path / "public_data"
        fake_public.mkdir()
        (fake_public / "latest_overview.json").write_text('{"known_good": true}', encoding="utf-8")
        monkeypatch.setattr(publish, "PUBLIC_DATA_DIR", fake_public)
        monkeypatch.setattr(publish, "build_public_exports", lambda target_dir: {"written": ["latest_overview.json"], "skipped": [], "directory": str(target_dir)})
        monkeypatch.setattr(publish, "validate_public_exports", lambda directory=None, write_report=True: {"status": "fail", "rows": [{"check": "x", "status": "fail", "message": "boom"}], "checks": 1, "failed": 1, "report": "n/a"})
        result = publish.safe_publish_public_exports()
        assert result["status"] == "rejected" and result["published"] is False
        assert json.loads((fake_public / "latest_overview.json").read_text(encoding="utf-8")) == {"known_good": True}

    def test_valid_staged_exports_promote_and_report_changes(self, tmp_path, monkeypatch):
        from src.public_export import publish

        fake_public = tmp_path / "public_data"
        fake_public.mkdir()
        (fake_public / "latest_overview.json").write_text('{"old": 1}', encoding="utf-8")

        def fake_build(target_dir):
            Path(target_dir, "latest_overview.json").write_text('{"new": 2}', encoding="utf-8")
            return {"written": ["latest_overview.json"], "skipped": [], "directory": str(target_dir)}

        calls = {"n": 0}

        def fake_validate(directory=None, write_report=True):
            calls["n"] += 1
            return {"status": "pass", "rows": [], "checks": 1, "failed": 0, "report": "n/a"}

        monkeypatch.setattr(publish, "PUBLIC_DATA_DIR", fake_public)
        monkeypatch.setattr(publish, "build_public_exports", fake_build)
        monkeypatch.setattr(publish, "validate_public_exports", fake_validate)
        result = publish.safe_publish_public_exports()
        assert result["status"] == "published"
        assert result["changed_files"] == ["latest_overview.json"]
        assert json.loads((fake_public / "latest_overview.json").read_text(encoding="utf-8")) == {"new": 2}
        assert calls["n"] >= 2  # staged validation + final validation


class TestForecastHistoryDeduplication:
    def test_same_run_id_never_duplicates(self, tmp_path, monkeypatch):
        from src.live_state import run_audit

        fake_live = tmp_path / "live_state"
        fake_live.mkdir()
        pd.DataFrame([{"team": "France", "champion_probability": 0.3}, {"team": "Spain", "champion_probability": 0.2}]).to_csv(fake_live / "live_champion_probabilities.csv", index=False)
        pd.DataFrame([{"team": "France", "reach_final_probability": 0.4}]).to_csv(fake_live / "team_reach_final_probabilities.csv", index=False)
        pd.DataFrame([{"finalist_team_1": "Argentina", "finalist_team_2": "France", "probability": 0.26}]).to_csv(fake_live / "finalist_pair_probabilities.csv", index=False)
        monkeypatch.setattr(run_audit, "LIVE_STATE_DIR", fake_live)
        monkeypatch.setattr(run_audit, "ensure_live_directories", lambda: None)
        run_audit.append_forecast_history("run-1", "quarterfinal", 1000, "football_data_org", "true_live_forecast")
        run_audit.append_forecast_history("run-1", "quarterfinal", 1000, "football_data_org", "true_live_forecast")  # rerun same id
        run_audit.append_forecast_history("run-2", "quarterfinal", 1000, "football_data_org", "true_live_forecast")
        history = pd.read_csv(fake_live / "champion_probability_history.csv")
        assert len(history) == 4  # 2 teams x 2 unique runs
        assert history.duplicated(subset=["run_id", "team"]).sum() == 0

    def test_history_is_append_only_across_runs(self, tmp_path, monkeypatch):
        from src.live_state import run_audit

        fake_live = tmp_path / "live_state"
        fake_live.mkdir()
        pd.DataFrame([{"team": "France", "champion_probability": 0.3}]).to_csv(fake_live / "live_champion_probabilities.csv", index=False)
        monkeypatch.setattr(run_audit, "LIVE_STATE_DIR", fake_live)
        monkeypatch.setattr(run_audit, "ensure_live_directories", lambda: None)
        run_audit.append_forecast_history("run-1", "quarterfinal", 1000, "p", "m")
        first = pd.read_csv(fake_live / "champion_probability_history.csv")
        pd.DataFrame([{"team": "France", "champion_probability": 0.35}]).to_csv(fake_live / "live_champion_probabilities.csv", index=False)
        run_audit.append_forecast_history("run-2", "semifinal", 1000, "p", "m")
        second = pd.read_csv(fake_live / "champion_probability_history.csv")
        assert len(second) == len(first) + 1
        assert float(second[second["run_id"] == "run-1"]["champion_probability"].iloc[0]) == 0.3  # old snapshot untouched


class TestManifestAndGitHelpers:
    def test_git_changed_files_parses_porcelain(self, tmp_path):
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
        (tmp_path / "tracked.txt").write_text("v1", encoding="utf-8")
        subprocess.run(["git", "add", "tracked.txt"], cwd=tmp_path, check=True)
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"], cwd=tmp_path, check=True)
        (tmp_path / "tracked.txt").write_text("v2", encoding="utf-8")
        (tmp_path / "new file.json").write_text("{}", encoding="utf-8")
        changed = commit_safety.git_changed_files(tmp_path)
        assert "tracked.txt" in changed and "new file.json" in changed

    def test_manifest_has_no_absolute_paths(self):
        manifest_path = PROJECT_ROOT / "outputs" / "reports" / "portfolio" / "latest_portfolio_refresh_manifest.json"
        if not manifest_path.exists():
            pytest.skip("portfolio refresh has not run yet")
        text = manifest_path.read_text(encoding="utf-8")
        assert not commit_safety.PRIVATE_PATH_PATTERN.search(text)
