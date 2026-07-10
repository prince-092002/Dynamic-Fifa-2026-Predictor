"""Environment and data presence checks for real-data loading."""

import shutil
from pathlib import Path

from src.config import PROJECT_ROOT, RAW_MANUAL_DIR, PROCESSED_DIR, RAW_DIR, REPORTS_DIR, ensure_project_directories
from src.loading.data_health import csv_status
from src.loading.manual_sources import MANUAL_FILES
from src.loading.reports import PROCESSED_REQUIREMENTS
from src.utils.files import has_real_rows


EXPECTED_ENV_KEYS = [
    "API_FOOTBALL_KEY",
    "API_FOOTBALL_WORLD_CUP_LEAGUE_ID",
    "KAGGLE_API_TOKEN",
    "KAGGLE_USERNAME",
    "KAGGLE_KEY",
    "SPORTMONKS_KEY",
]


def _parse_env_file(path: Path) -> dict[str, str]:
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def ensure_env_file() -> tuple[Path, bool]:
    """Create .env from .env.example if needed."""
    ensure_project_directories()
    env_path = PROJECT_ROOT / ".env"
    example_path = PROJECT_ROOT / ".env.example"
    if env_path.exists():
        return env_path, False
    if example_path.exists():
        shutil.copy2(example_path, env_path)
    else:
        env_path.write_text(
            "API_FOOTBALL_KEY=\nAPI_FOOTBALL_WORLD_CUP_LEAGUE_ID=\nKAGGLE_API_TOKEN=\nKAGGLE_USERNAME=\nKAGGLE_KEY=\nSPORTMONKS_KEY=\n",
            encoding="utf-8",
        )
    return env_path, True


def check_environment(create_missing_env: bool = True) -> dict:
    """Return yes/no environment, manual fallback, and processed-data readiness facts."""
    env_path = PROJECT_ROOT / ".env"
    created = False
    if create_missing_env and not env_path.exists():
        env_path, created = ensure_env_file()

    env_values = _parse_env_file(env_path)
    env_checks = {
        ".env exists": env_path.exists(),
        ".env created this run": created,
    }
    for key in EXPECTED_ENV_KEYS:
        env_checks[f"{key} present"] = bool(env_values.get(key))

    manual_checks = {}
    for kind, (final_name, template_name) in MANUAL_FILES.items():
        final_path = RAW_MANUAL_DIR / final_name
        template_path = RAW_MANUAL_DIR / template_name
        manual_checks[f"{final_name} has real rows"] = has_real_rows(final_path)
        manual_checks[f"{template_name} has real rows"] = has_real_rows(template_path)

    processed_checks = {}
    for filename, required_columns in PROCESSED_REQUIREMENTS.items():
        processed_checks[f"{filename} has real rows"] = has_real_rows(PROCESSED_DIR / filename, required_columns)

    return {
        "env_path": str(env_path),
        "created_env": created,
        "env": env_checks,
        "manual": manual_checks,
        "processed": processed_checks,
    }


def print_environment_check(result: dict) -> None:
    """Print and save a compact table without exposing secret values."""
    if result.get("created_env"):
        print(".env did not exist, so it was created from .env.example. Fill in credentials before API/Kaggle loading.")
    rows = environment_check_rows(result)
    widths = [max(len(str(row[i])) for row in [["Item", "Status", "Details"], *rows]) for i in range(3)]
    print(f"{'Item'.ljust(widths[0])} | {'Status'.ljust(widths[1])} | Details")
    print("-" * (sum(widths) + 6))
    for item, status, details in rows:
        print(f"{item.ljust(widths[0])} | {status.ljust(widths[1])} | {details}")
    write_env_check_report(rows)


def environment_check_rows(result: dict) -> list[list[str]]:
    env_path = PROJECT_ROOT / ".env"
    rows = [
        [".env", "FOUND" if env_path.exists() else "MISSING", "credentials file; values hidden"],
        [".gitignore", "FOUND" if (PROJECT_ROOT / ".gitignore").exists() else "MISSING", "should protect .env and tokens"],
    ]
    env_values = _parse_env_file(env_path)
    for key in EXPECTED_ENV_KEYS:
        present = bool(env_values.get(key))
        optional = key in {"API_FOOTBALL_WORLD_CUP_LEAGUE_ID", "SPORTMONKS_KEY"}
        rows.append([key, "FOUND" if present else "MISSING", "value hidden" if present else ("optional" if optional else "not set")])
    folders = [
        ("raw folder", RAW_DIR),
        ("processed folder", PROCESSED_DIR),
        ("reports folder", REPORTS_DIR),
        ("manual folder", RAW_MANUAL_DIR),
    ]
    for label, path in folders:
        rows.append([label, "FOUND" if path.exists() else "MISSING", str(path)])
    for kind, (final_name, template_name) in MANUAL_FILES.items():
        final_path = RAW_MANUAL_DIR / final_name
        template_path = RAW_MANUAL_DIR / template_name
        rows.append([final_name, "FOUND" if final_path.exists() else "MISSING", "manual fallback file"])
        rows.append([template_name, "FOUND" if template_path.exists() else "MISSING", "manual template"])
    for filename, required in PROCESSED_REQUIREMENTS.items():
        info = csv_status(PROCESSED_DIR / filename, required)
        rows.append([filename, info["status"], f"{info['rows']} rows"])
    return rows


def write_env_check_report(rows: list[list[str]]) -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["# Environment Check Report", "", "| Item | Status | Details |", "|---|---|---|"]
    for item, status, details in rows:
        lines.append(f"| `{item}` | {status} | {details} |")
    path = REPORTS_DIR / "env_check_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return str(path)
