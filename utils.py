"""
ThreadScout - Utilities Module
===============================
Shared helper functions for file I/O, date formatting, and safe operations.
"""

import json
from datetime import datetime
from pathlib import Path

# pyrefly: ignore [missing-import]
from loguru import logger


def load_json(filepath: Path) -> dict | list:
    """
    Load and parse a JSON file.

    Args:
        filepath: Path to the JSON file.

    Returns:
        Parsed JSON content (dict or list).

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.debug(f"Loaded JSON from {filepath}")
        return data
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {filepath}: {e}")
        raise


def save_json(filepath: Path, data: dict | list) -> None:
    """
    Save data to a JSON file with pretty formatting.

    Args:
        filepath: Destination file path.
        data: Data to serialize (dict or list).
    """
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.debug(f"Saved JSON to {filepath}")
    except PermissionError:
        logger.error(f"Permission denied writing to {filepath}")
        raise
    except OSError as e:
        logger.error(f"Error writing to {filepath}: {e}")
        raise


def load_keywords(filepath: Path) -> list[str]:
    """
    Load keywords from the keywords.json file.

    Args:
        filepath: Path to keywords.json.

    Returns:
        List of keyword strings.
    """
    data = load_json(filepath)
    keywords = data.get("keywords", []) if isinstance(data, dict) else data
    logger.info(f"Loaded {len(keywords)} keywords from {filepath.name}")
    return keywords


def save_keywords(filepath: Path, keywords: list[str]) -> None:
    """
    Save keywords list to the keywords.json file.

    Args:
        filepath: Path to keywords.json.
        keywords: List of keyword strings to save.
    """
    save_json(filepath, {"keywords": keywords})
    logger.info(f"Saved {len(keywords)} keywords to {filepath.name}")


def get_timestamp() -> str:
    """
    Get the current timestamp formatted for display.

    Returns:
        Formatted timestamp string (e.g., '2026-07-17 18:30:00').
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_date_string() -> str:
    """
    Get today's date formatted for filenames.

    Returns:
        Date string (e.g., '2026-07-17').
    """
    return datetime.now().strftime("%Y-%m-%d")


def get_log_filename() -> str:
    """
    Generate the daily log filename.

    Returns:
        Log filename (e.g., '2026-07-17.log').
    """
    return f"{get_date_string()}.log"


def safe_truncate(text: str, max_length: int = 80) -> str:
    """
    Safely truncate text to a maximum length with ellipsis.

    Args:
        text: Text to truncate.
        max_length: Maximum allowed length.

    Returns:
        Truncated text with '...' if it exceeded max_length.
    """
    if not text:
        return ""
    text = text.replace("\n", " ").replace("\r", "").strip()
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."


def format_duration(seconds: float) -> str:
    """
    Format a duration in seconds to a human-readable string.

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted string (e.g., '2m 35s' or '45s').
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    if minutes < 60:
        return f"{minutes}m {remaining_seconds:.0f}s"
    hours = int(minutes // 60)
    remaining_minutes = minutes % 60
    return f"{hours}h {remaining_minutes}m {remaining_seconds:.0f}s"
