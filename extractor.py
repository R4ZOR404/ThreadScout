"""
ThreadScout - Extractor Module
================================
Extracts Instagram usernames and links from Threads post content.
"""

import re
from dataclasses import dataclass, field

from loguru import logger


@dataclass
class ExtractionResult:
    """Result of extracting Instagram references from a post."""
    usernames: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)

    @property
    def found(self) -> bool:
        """Whether any Instagram reference was found."""
        return bool(self.usernames or self.links)

    @property
    def primary(self) -> str:
        """
        Return the primary Instagram reference for display.
        Prefers usernames over links. Returns 'Not Found' if empty.
        """
        if self.usernames:
            return self.usernames[0]
        if self.links:
            return self.links[0]
        return "Not Found"

    @property
    def all_references(self) -> list[str]:
        """Return all found references (usernames + links)."""
        return self.usernames + self.links


# ─── Compiled Extraction Patterns ───────────────────────────────────────────────

# Matches @username patterns (2-30 alphanumeric chars, dots, underscores)
_PATTERN_AT_MENTION = re.compile(
    r"@([a-zA-Z0-9][a-zA-Z0-9._]{1,29})", re.IGNORECASE
)

# Matches instagram.com/username links
_PATTERN_IG_LINK = re.compile(
    r"(?:https?://)?(?:www\.)?instagram\.com/([a-zA-Z0-9._]{2,30})/?",
    re.IGNORECASE,
)

# Matches "ig: username" or "IG: username" patterns
_PATTERN_IG_COLON = re.compile(
    r"\big\s*:\s*@?([a-zA-Z0-9][a-zA-Z0-9._]{1,29})", re.IGNORECASE
)

# Matches "insta: username" or "instagram: username" patterns
_PATTERN_INSTA_COLON = re.compile(
    r"\b(?:insta|instagram)\s*:\s*@?([a-zA-Z0-9][a-zA-Z0-9._]{1,29})",
    re.IGNORECASE,
)

# ─── Exclusion List ─────────────────────────────────────────────────────────────
# Common non-username @ mentions to filter out (e.g., platform accounts)

_EXCLUDED_USERNAMES: set[str] = {
    "everyone",
    "here",
    "channel",
    "all",
    "threads",
    "instagram",
    "meta",
    "admin",
    "moderator",
    "mod",
    "support",
    "help",
    "team",
}


def _clean_username(username: str) -> str | None:
    """
    Validate and clean an extracted username.

    Args:
        username: Raw extracted username string.

    Returns:
        Cleaned username with @ prefix, or None if invalid.
    """
    if not username:
        return None

    # Remove trailing dots and underscores
    username = username.rstrip(".").rstrip("_")

    # Must be at least 2 chars
    if len(username) < 2:
        return None

    # Exclude common non-personal usernames
    if username.lower() in _EXCLUDED_USERNAMES:
        return None

    return f"@{username}"


def extract_instagram(content: str) -> ExtractionResult:
    """
    Extract Instagram usernames and links from post content.

    Applies multiple regex patterns to find:
    - @username mentions
    - instagram.com/ links
    - ig: username references
    - insta: / instagram: username references

    Results are deduplicated and cleaned.

    Args:
        content: The text content of a Threads post.

    Returns:
        ExtractionResult with found usernames and links.
    """
    if not content or not content.strip():
        return ExtractionResult()

    usernames: list[str] = []
    links: list[str] = []
    seen: set[str] = set()

    # --- Extract ig: and insta: patterns first (higher confidence) ---
    for pattern in [_PATTERN_IG_COLON, _PATTERN_INSTA_COLON]:
        for match in pattern.finditer(content):
            cleaned = _clean_username(match.group(1))
            if cleaned and cleaned.lower() not in seen:
                seen.add(cleaned.lower())
                usernames.append(cleaned)

    # --- Extract instagram.com/ links ---
    for match in _PATTERN_IG_LINK.finditer(content):
        raw_username = match.group(1)
        link = f"instagram.com/{raw_username}"
        cleaned = _clean_username(raw_username)

        if cleaned and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            usernames.append(cleaned)
            links.append(link)
        elif link.lower() not in {l.lower() for l in links}:
            links.append(link)

    # --- Extract @mentions ---
    for match in _PATTERN_AT_MENTION.finditer(content):
        cleaned = _clean_username(match.group(1))
        if cleaned and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            usernames.append(cleaned)

    if usernames or links:
        logger.debug(
            f"Extracted {len(usernames)} username(s), {len(links)} link(s)"
        )

    return ExtractionResult(usernames=usernames, links=links)
