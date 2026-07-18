"""
ThreadScout - UI Module
========================
Rich-based terminal UI components: banner, menus, tables, dashboards, and prompts.
"""

from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from config import (
    APP_NAME,
    APP_TAGLINE,
    APP_VERSION,
    COLORS,
    GRADIENT_COLORS,
    THREAD_THEME,
)
from utils import safe_truncate, format_duration

# ─── Console Instance ───────────────────────────────────────────────────────────

console = Console(theme=THREAD_THEME)

# ─── ASCII Banner ───────────────────────────────────────────────────────────────

_BANNER_LINES: list[str] = [
    "████████╗██╗  ██╗██████╗ ███████╗ █████╗ ██████╗ ",
    "╚══██╔══╝██║  ██║██╔══██╗██╔════╝██╔══██╗██╔══██╗",
    "   ██║   ███████║██████╔╝█████╗  ███████║██║  ██║",
    "   ██║   ██╔══██║██╔══██╗██╔══╝  ██╔══██║██║  ██║",
    "   ██║   ██║  ██║██║  ██║███████╗██║  ██║██████╔╝",
    "   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═════╝",
]

_SCOUT_LINES: list[str] = [
    "███████╗ ██████╗ ██████╗ ██╗   ██╗████████╗",
    "██╔════╝██╔════╝██╔═══██╗██║   ██║╚══██╔══╝",
    "███████╗██║     ██║   ██║██║   ██║   ██║   ",
    "╚════██║██║     ██║   ██║██║   ██║   ██║   ",
    "███████║╚██████╗╚██████╔╝╚██████╔╝   ██║   ",
    "╚══════╝ ╚═════╝ ╚═════╝  ╚═════╝    ╚═╝   ",
]


def _gradient_text(text: str, colors: list[str]) -> Text:
    """
    Apply a gradient color effect across characters of text.

    Args:
        text: The string to colorize.
        colors: List of hex color codes for the gradient.

    Returns:
        Rich Text object with gradient styling.
    """
    rich_text = Text()
    if not text:
        return rich_text

    for i, char in enumerate(text):
        color_index = int(i / max(len(text) - 1, 1) * (len(colors) - 1))
        color_index = min(color_index, len(colors) - 1)
        rich_text.append(char, style=f"bold {colors[color_index]}")

    return rich_text


def show_banner() -> None:
    """Display the ThreadScout ASCII art banner with gradient colors."""
    console.print()

    # Render "THREAD" with gradient
    for line in _BANNER_LINES:
        colored_line = _gradient_text(line, GRADIENT_COLORS)
        console.print(Align.center(colored_line))

    # Render "SCOUT" with gradient (shifted colors)
    scout_gradient = GRADIENT_COLORS[2:] + GRADIENT_COLORS[:2]
    for line in _SCOUT_LINES:
        colored_line = _gradient_text(line, scout_gradient)
        console.print(Align.center(colored_line))

    # Version and tagline
    version_text = Text()
    version_text.append(f"  {APP_NAME} ", style=f"bold {COLORS['white']}")
    version_text.append(f"v{APP_VERSION}", style=f"bold {COLORS['orange']}")
    console.print(Align.center(version_text))

    tagline_text = Text(f"  {APP_TAGLINE}", style=f"italic {COLORS['pink']}")
    console.print(Align.center(tagline_text))

    # Decorative line
    line = Text("─" * 52, style=COLORS["purple"])
    console.print(Align.center(line))
    console.print()


def show_menu() -> None:
    """Display the main interactive menu."""
    menu_items = [
        ("1", "🔍", "Start Search", "Mulai pencarian keyword di Threads"),
        ("2", "📝", "Edit Keywords", "Kelola daftar kata kunci"),
        ("3", "📊", "View Results", "Lihat hasil pencarian terbaru"),
        ("4", "📄", "Export CSV", "Ekspor hasil ke format CSV"),
        ("5", "📗", "Export Excel", "Ekspor hasil ke format Excel"),
        ("6", "📈", "Statistics", "Dashboard statistik pencarian"),
        ("7", "⚙️ ", "Settings", "Pengaturan aplikasi"),
        ("0", "🚪", "Exit", "Keluar dari ThreadScout"),
    ]

    table = Table(
        show_header=False,
        box=box.SIMPLE,
        padding=(0, 2),
        show_edge=False,
    )
    table.add_column("No", style=f"bold {COLORS['orange']}", width=4)
    table.add_column("Icon", width=4)
    table.add_column("Menu", style=f"bold {COLORS['white']}", width=18)
    table.add_column("Description", style=COLORS["light_gray"])

    for num, icon, title, desc in menu_items:
        table.add_row(num, icon, title, desc)

    panel = Panel(
        table,
        title=f"[bold {COLORS['purple']}]━━━ MAIN MENU ━━━[/]",
        border_style=COLORS["purple"],
        box=box.DOUBLE_EDGE,
        padding=(1, 2),
    )

    console.print(Align.center(panel, width=72))


def prompt_menu_choice() -> str:
    """
    Prompt the user for a menu selection.

    Returns:
        The user's menu choice as a string.
    """
    console.print()
    choice = console.input(
        f"  [{COLORS['orange']}]▶[/] Pilih menu [{COLORS['pink']}](0-7)[/]: "
    )
    return choice.strip()


def show_results_table(results: list[dict]) -> None:
    """
    Display search results in a formatted Rich table.

    Args:
        results: List of result dictionaries.
    """
    if not results:
        show_warning("Belum ada hasil pencarian.")
        return

    table = Table(
        title=f"[bold {COLORS['purple']}]📊 Hasil Pencarian[/]",
        box=box.ROUNDED,
        border_style=COLORS["purple"],
        header_style=f"bold {COLORS['pink']}",
        show_lines=True,
        padding=(0, 1),
    )

    table.add_column("No", style=f"bold {COLORS['orange']}", width=4, justify="center")
    table.add_column("Threads", style=f"bold {COLORS['white']}", width=14)
    table.add_column("Instagram", style=f"bold {COLORS['pink']}", width=16)
    table.add_column("IG Link", style=f"{COLORS['info']}", width=28)
    table.add_column("Keyword", style=COLORS["orange"], width=12)
    table.add_column("Content", style=COLORS["light_gray"], width=25)

    for i, row in enumerate(results[:50], start=1):  # Cap display at 50 rows
        ig_link = str(row.get("Instagram Link", "Not Found"))
        table.add_row(
            str(i),
            str(row.get("Threads", "N/A")),
            str(row.get("Instagram", "Not Found")),
            safe_truncate(ig_link, 28),
            str(row.get("Keyword", "")),
            safe_truncate(str(row.get("Post Content", "")), 25),
        )

    console.print()
    console.print(Align.center(table))

    if len(results) > 50:
        show_info(f"Menampilkan 50 dari {len(results)} hasil. Ekspor untuk melihat semua.")
    console.print()


def show_statistics(stats: dict) -> None:
    """
    Display search statistics in a dashboard panel.

    Args:
        stats: Dictionary with statistics data.
    """
    stats_table = Table(
        box=box.SIMPLE_HEAVY,
        show_header=False,
        padding=(0, 3),
        border_style=COLORS["purple"],
    )
    stats_table.add_column("Metric", style=f"bold {COLORS['white']}", width=35)
    stats_table.add_column("Value", style=f"bold {COLORS['orange']}", width=20, justify="right")

    items = [
        ("🔄  Siklus keyword", str(stats.get("cycles_completed", 0))),
        ("🔑  Keyword diproses", str(stats.get("keywords_processed", 0))),
        ("📝  Posting diperiksa", str(stats.get("posts_checked", 0))),
        ("✅  Posting lolos filter", str(stats.get("posts_passed", 0))),
        ("📸  Instagram ditemukan", str(stats.get("ig_found", 0))),
        ("⚡  IG per menit", f"{stats.get('ig_per_minute', 0):.1f}"),
        ("⏱️   Waktu proses", format_duration(stats.get("duration", 0))),
        ("📊  Persentase ekstraksi", f"{stats.get('success_rate', 0):.1f}%"),
    ]

    for metric, value in items:
        stats_table.add_row(metric, value)

    panel = Panel(
        stats_table,
        title=f"[bold {COLORS['purple']}]━━━ STATISTICS DASHBOARD ━━━[/]",
        border_style=COLORS["pink"],
        box=box.DOUBLE_EDGE,
        padding=(1, 2),
    )

    console.print()
    console.print(Align.center(panel, width=72))
    console.print()


def show_keywords_list(keywords: list[str]) -> None:
    """
    Display the current keywords in a formatted panel.

    Args:
        keywords: List of keyword strings.
    """
    # Display in 3-column layout
    keyword_texts = []
    for i, kw in enumerate(keywords, 1):
        text = Text()
        text.append(f"{i:3d}. ", style=COLORS["orange"])
        text.append(kw, style=COLORS["white"])
        keyword_texts.append(text)

    # Split into 3 columns
    col_size = (len(keyword_texts) + 2) // 3
    columns_data = []
    for col_start in range(0, len(keyword_texts), col_size):
        col_text = Text()
        for kt in keyword_texts[col_start : col_start + col_size]:
            col_text.append_text(kt)
            col_text.append("\n")
        columns_data.append(col_text)

    panel = Panel(
        Columns(columns_data, padding=(0, 3)),
        title=f"[bold {COLORS['purple']}]━━━ KEYWORDS ({len(keywords)}) ━━━[/]",
        border_style=COLORS["purple"],
        box=box.DOUBLE_EDGE,
        padding=(1, 2),
    )

    console.print()
    console.print(panel)
    console.print()


def show_keyword_edit_menu() -> None:
    """Display the keyword editing submenu options."""
    console.print(f"  [{COLORS['orange']}]1[/] ➕  Tambah keyword")
    console.print(f"  [{COLORS['orange']}]2[/] ➖  Hapus keyword")
    console.print(f"  [{COLORS['orange']}]3[/] 📋  Lihat semua keyword")
    console.print(f"  [{COLORS['orange']}]4[/] 🔄  Reset ke default")
    console.print(f"  [{COLORS['orange']}]0[/] ↩️   Kembali ke menu utama")
    console.print()


def show_settings(settings: dict) -> None:
    """
    Display current application settings.

    Args:
        settings: Dictionary of setting key-value pairs.
    """
    table = Table(
        box=box.SIMPLE_HEAVY,
        show_header=True,
        header_style=f"bold {COLORS['pink']}",
        border_style=COLORS["purple"],
        padding=(0, 2),
    )
    table.add_column("Setting", style=f"bold {COLORS['white']}", width=28)
    table.add_column("Value", style=f"bold {COLORS['orange']}", width=25, justify="right")

    for key, value in settings.items():
        table.add_row(key, str(value))

    panel = Panel(
        table,
        title=f"[bold {COLORS['purple']}]━━━ SETTINGS ━━━[/]",
        border_style=COLORS["purple"],
        box=box.DOUBLE_EDGE,
        padding=(1, 2),
    )

    console.print()
    console.print(Align.center(panel, width=72))
    console.print()


# ─── Status Messages ────────────────────────────────────────────────────────────


def show_success(message: str) -> None:
    """Display a success message."""
    console.print(f"  [{COLORS['success']}]✔[/]  {message}")


def show_error(message: str) -> None:
    """Display an error message."""
    console.print(f"  [{COLORS['error']}]✖[/]  {message}")


def show_warning(message: str) -> None:
    """Display a warning message."""
    console.print(f"  [{COLORS['warning']}]⚠[/]  {message}")


def show_info(message: str) -> None:
    """Display an info message."""
    console.print(f"  [{COLORS['info']}]ℹ[/]  {message}")


def show_divider() -> None:
    """Display a horizontal divider."""
    line = Text("─" * 60, style=COLORS["purple"])
    console.print(Align.center(line))


def confirm_action(prompt: str) -> bool:
    """
    Ask the user for a yes/no confirmation.

    Args:
        prompt: The confirmation question.

    Returns:
        True if the user confirms (y/yes), False otherwise.
    """
    response = console.input(
        f"  [{COLORS['warning']}]?[/]  {prompt} [{COLORS['pink']}](y/n)[/]: "
    )
    return response.strip().lower() in ("y", "yes")
