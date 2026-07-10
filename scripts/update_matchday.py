"""Scheduler-friendly matchday update entry point."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.update.update_runner import run_update


if __name__ == "__main__":
    result = run_update(mode="matchday", force=False)
    print(result)

