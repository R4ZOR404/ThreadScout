"""
ThreadScout - Configuration Module
===================================
Centralized configuration for paths, colors, themes, and app constants.
"""

from pathlib import Path
from rich.theme import Theme

# ─── App Metadata ───────────────────────────────────────────────────────────────

APP_NAME: str = "ThreadScout"
APP_VERSION: str = "2.0"
APP_TAGLINE: str = "Instagram Mutual Research Tool — Unlimited Edition"

# ─── Directory Paths ────────────────────────────────────────────────────────────

BASE_DIR: Path = Path(__file__).resolve().parent
OUTPUT_DIR: Path = BASE_DIR / "output"
LOGS_DIR: Path = BASE_DIR / "logs"
CONFIG_DIR: Path = BASE_DIR / "config"

# ─── File Paths ─────────────────────────────────────────────────────────────────

KEYWORDS_FILE: Path = CONFIG_DIR / "keywords.json"
CSV_OUTPUT: Path = OUTPUT_DIR / "result.csv"
EXCEL_OUTPUT: Path = OUTPUT_DIR / "result.xlsx"

# ─── Instagram-Inspired Color Palette ───────────────────────────────────────────

COLORS = {
    "purple": "#833AB4",
    "pink": "#E1306C",
    "orange": "#F77737",
    "yellow": "#FCAF45",
    "white": "#FFFFFF",
    "light_gray": "#B0B0B0",
    "dark": "#1A1A2E",
    "dark_surface": "#16213E",
    "accent_blue": "#0F3460",
    "success": "#2ECC71",
    "error": "#E74C3C",
    "warning": "#F39C12",
    "info": "#3498DB",
}

# ─── Rich Theme ─────────────────────────────────────────────────────────────────

THREAD_THEME = Theme({
    "title": f"bold {COLORS['purple']}",
    "subtitle": f"italic {COLORS['pink']}",
    "highlight": f"bold {COLORS['orange']}",
    "success": f"bold {COLORS['success']}",
    "error": f"bold {COLORS['error']}",
    "warning": f"bold {COLORS['warning']}",
    "info": f"bold {COLORS['info']}",
    "menu.number": f"bold {COLORS['orange']}",
    "menu.text": COLORS["white"],
    "menu.active": f"bold {COLORS['pink']}",
    "table.header": f"bold {COLORS['purple']}",
    "table.cell": COLORS["light_gray"],
    "panel.border": COLORS["purple"],
    "progress.bar": COLORS["pink"],
    "dim": COLORS["light_gray"],
})

# ─── Gradient Colors for Banner ─────────────────────────────────────────────────

GRADIENT_COLORS: list[str] = [
    "#833AB4",  # Purple
    "#9B30B4",
    "#B327B0",
    "#C9239E",
    "#E1306C",  # Pink
    "#E84D5E",
    "#EF6A50",
    "#F77737",  # Orange
]

# ─── Browser Settings (Optimized for Maximum Speed) ─────────────────────────────

BROWSER_HEADLESS: bool = True
BROWSER_TIMEOUT: int = 10000  # milliseconds (aggressive timeout)
SCROLL_COUNT: int = 5  # number of scroll-downs per keyword search
SCROLL_DELAY: float = 0.3  # seconds between scrolls (minimal)
SEARCH_DELAY_MIN: float = 0.2  # minimum delay between keyword searches
SEARCH_DELAY_MAX: float = 0.5  # maximum delay between keyword searches
CONCURRENT_TABS: int = 10  # number of browser tabs running in parallel

# ─── Threads URLs ───────────────────────────────────────────────────────────────

THREADS_BASE_URL: str = "https://www.threads.net"
THREADS_SEARCH_URL: str = f"{THREADS_BASE_URL}/search?q="

# ─── Instagram URL ──────────────────────────────────────────────────────────────

INSTAGRAM_BASE_URL: str = "https://www.instagram.com"

# ─── Filter Patterns ────────────────────────────────────────────────────────────

FILTER_PATTERNS: list[str] = [
    r"@\w+",
    r"instagram\.com/",
    r"ig\s*:",
    r"insta",
    r"\bdm\b",
]

# ─── Ensure Required Directories Exist ──────────────────────────────────────────


def ensure_directories() -> None:
    """Create required directories if they don't exist."""
    for directory in [OUTPUT_DIR, LOGS_DIR, CONFIG_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
