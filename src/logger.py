"""Logging helpers for the fetch and cleaning pipeline."""

import logging
from logging.handlers import RotatingFileHandler

from src.config import PIPELINE_LOG_PATH, ensure_project_directories


def get_logger(name: str = "fifa_data_pipeline") -> logging.Logger:
    """Return a configured logger that writes to console and a log file."""
    ensure_project_directories()
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        PIPELINE_LOG_PATH, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger

