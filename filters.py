"""
ThreadScout - Filters Module
==============================
Regex-based filtering to identify Threads posts containing Instagram references.
"""

import re
from dataclasses import dataclass

from loguru import logger


@dataclass
class FilterResult:
    """Result of filtering a post's content."""
    passed: bool
    matched_patterns: list[str]


# ─── Compiled Filter Patterns ───────────────────────────────────────────────────
# Patterns that indicate a post might contain Instagram usernames or links.

_FILTER_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("@mention", re.compile(r"@\w{2,}", re.IGNORECASE)),
    ("instagram.com/", re.compile(r"instagram\.com/\w+", re.IGNORECASE)),
    ("ig:", re.compile(r"\big\s*:", re.IGNORECASE)),
    ("insta", re.compile(r"\binsta\b", re.IGNORECASE)),
    ("dm", re.compile(r"\bdm\b", re.IGNORECASE)),
]


def apply_filters(content: str) -> FilterResult:
    """
    Check if post content matches any of the filter patterns.

    A post passes the filter if it contains at least one pattern that suggests
    it includes an Instagram username, link, or reference.

    Args:
        content: The text content of a Threads post.

    Returns:
        FilterResult with pass/fail status and list of matched pattern names.
    """
    if not content or not content.strip():
        return FilterResult(passed=False, matched_patterns=[])

    matched: list[str] = []

    for pattern_name, regex in _FILTER_PATTERNS:
        if regex.search(content):
            matched.append(pattern_name)

    result = FilterResult(passed=len(matched) > 0, matched_patterns=matched)

    if result.passed:
        logger.debug(
            f"Post passed filter — matched: {', '.join(result.matched_patterns)}"
        )

    return result


def check_keyword_match(content: str, keyword: str) -> bool:
    """
    Verify that a post's content actually contains the searched keyword.

    Args:
        content: The text content of a Threads post.
        keyword: The keyword that was used for the search.

    Returns:
        True if the keyword is found in the content (case-insensitive).
    """
    if not content or not keyword:
        return False
    return keyword.lower() in content.lower()
