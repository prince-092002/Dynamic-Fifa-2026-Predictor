"""Backup helpers for processed data files."""

from datetime import datetime
from pathlib import Path
import shutil

from src.config import BACKUPS_DIR, PROCESSED_DIR, ensure_project_directories


IMPORTANT_PROCESSED_FILES = [
    PROCESSED_DIR / "fixtures_2026.csv",
    PROCESSED_DIR / "results_2026.csv",
    PROCESSED_DIR / "matches_master.csv",
    PROCESSED_DIR / "team_ratings.csv",
    PROCESSED_DIR / "team_stats_2026.csv",
    PROCESSED_DIR / "player_stats_2026.csv",
]


def _timestamp_folder() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = BACKUPS_DIR / stamp
    counter = 1
    while folder.exists():
        folder = BACKUPS_DIR / f"{stamp}_{counter}"
        counter += 1
    return folder


def create_backup(file_path: Path, backup_folder: Path | None = None) -> Path | None:
    """Copy one file into a timestamped backup folder."""
    ensure_project_directories()
    file_path = Path(file_path)
    if not file_path.exists():
        return None
    backup_folder = backup_folder or _timestamp_folder()
    backup_folder.mkdir(parents=True, exist_ok=False if not backup_folder.exists() else True)
    backup_path = backup_folder / file_path.name
    shutil.copy2(file_path, backup_path)
    return backup_path


def create_backups_for_processed_files() -> Path:
    """Back up all important processed files that currently exist."""
    ensure_project_directories()
    backup_folder = _timestamp_folder()
    backup_folder.mkdir(parents=True, exist_ok=False)
    for path in IMPORTANT_PROCESSED_FILES:
        create_backup(path, backup_folder)
    return backup_folder


def restore_backup(original_file_path: Path, backup_file_path: Path) -> Path:
    """Restore one backup file to its original processed path."""
    original_file_path = Path(original_file_path)
    backup_file_path = Path(backup_file_path)
    original_file_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_file_path, original_file_path)
    return original_file_path

