"""
ThreadScout - Main Entry Point
================================
Interactive CLI application for collecting Instagram references from
publicly accessible Threads posts based on keyword searches.

Usage:
    python main.py          # Start the interactive menu
    python main.py --help   # Show help
"""

import asyncio
import sys
import time
from pathlib import Path

import typer
from loguru import logger

from config import (
    APP_NAME,
    APP_VERSION,
    BROWSER_HEADLESS,
    COLORS,
    KEYWORDS_FILE,
    LOGS_DIR,
    SCROLL_COUNT,
    SEARCH_DELAY_MAX,
    SEARCH_DELAY_MIN,
    ensure_directories,
)
from exporter import export_csv, export_excel
from search import ThreadsSearcher
from ui import (
    confirm_action,
    console,
    prompt_menu_choice,
    show_banner,
    show_divider,
    show_error,
    show_info,
    show_keyword_edit_menu,
    show_keywords_list,
    show_menu,
    show_results_table,
    show_settings,
    show_statistics,
    show_success,
    show_warning,
)
from utils import (
    get_log_filename,
    get_timestamp,
    load_keywords,
    save_keywords,
)

# ─── Typer CLI App ──────────────────────────────────────────────────────────────

app = typer.Typer(
    name=APP_NAME,
    help=f"{APP_NAME} v{APP_VERSION} — Instagram Mutual Research Tool",
    add_completion=False,
    no_args_is_help=False,
)

# ─── Application State ─────────────────────────────────────────────────────────

_results: list[dict] = []
_stats: dict = {}
_search_performed: bool = False


# ─── Logging Setup ──────────────────────────────────────────────────────────────


def setup_logging() -> None:
    """Configure Loguru with daily rotating log files."""
    # Remove default handler
    logger.remove()

    # File handler: daily rotating log
    log_file = LOGS_DIR / get_log_filename()
    logger.add(
        log_file,
        rotation="00:00",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {module}:{function}:{line} | {message}",
        level="DEBUG",
        encoding="utf-8",
    )

    # Minimal stderr handler for critical errors only
    logger.add(
        sys.stderr,
        level="CRITICAL",
        format="{message}",
    )

    logger.info(f"{'='*60}")
    logger.info(f"{APP_NAME} v{APP_VERSION} started")
    logger.info(f"{'='*60}")


# ─── Menu Handlers ──────────────────────────────────────────────────────────────


async def handle_search() -> None:
    """Handle the Start Search menu option."""
    global _results, _stats, _search_performed

    try:
        keywords = load_keywords(KEYWORDS_FILE)
    except (FileNotFoundError, Exception) as e:
        show_error(f"Gagal memuat keywords: {e}")
        return

    if not keywords:
        show_warning("Tidak ada keyword ditemukan. Tambahkan keyword terlebih dahulu.")
        return

    show_info(f"Total {len(keywords)} keyword akan diproses")
    console.print()

    # Ask if user wants to limit keywords
    limit_input = console.input(
        f"  [{COLORS['orange']}]▶[/] Jumlah keyword (Enter = semua, atau angka): "
    ).strip()

    if limit_input.isdigit():
        limit = int(limit_input)
        keywords = keywords[:limit]
        show_info(f"Dibatasi ke {len(keywords)} keyword pertama")

    if not confirm_action(f"Mulai pencarian dengan {len(keywords)} keyword?"):
        show_info("Pencarian dibatalkan.")
        return

    # Run the search
    searcher = ThreadsSearcher()
    _results = await searcher.run_search(keywords)
    _stats = searcher.stats.to_dict()
    _search_performed = True

    # Log results
    logger.info(f"Search completed: {len(_results)} results")

    # Show brief statistics
    console.print()
    show_statistics(_stats)


def handle_edit_keywords() -> None:
    """Handle the Edit Keywords menu option."""
    try:
        keywords = load_keywords(KEYWORDS_FILE)
    except FileNotFoundError:
        keywords = []
        show_warning("File keywords tidak ditemukan. Membuat file baru.")

    while True:
        console.print()
        show_keyword_edit_menu()
        choice = console.input(
            f"  [{COLORS['orange']}]▶[/] Pilih opsi [{COLORS['pink']}](0-4)[/]: "
        ).strip()

        if choice == "1":
            # Add keyword
            new_kw = console.input(
                f"  [{COLORS['orange']}]▶[/] Masukkan keyword baru: "
            ).strip()
            if new_kw:
                if new_kw in keywords:
                    show_warning(f"Keyword '{new_kw}' sudah ada.")
                else:
                    keywords.append(new_kw)
                    save_keywords(KEYWORDS_FILE, keywords)
                    show_success(f"Keyword '{new_kw}' berhasil ditambahkan.")
            else:
                show_warning("Keyword tidak boleh kosong.")

        elif choice == "2":
            # Remove keyword
            show_keywords_list(keywords)
            idx_input = console.input(
                f"  [{COLORS['orange']}]▶[/] Nomor keyword yang dihapus: "
            ).strip()
            if idx_input.isdigit():
                idx = int(idx_input) - 1
                if 0 <= idx < len(keywords):
                    removed = keywords.pop(idx)
                    save_keywords(KEYWORDS_FILE, keywords)
                    show_success(f"Keyword '{removed}' berhasil dihapus.")
                else:
                    show_error("Nomor tidak valid.")
            else:
                show_error("Masukkan nomor yang valid.")

        elif choice == "3":
            # View all
            show_keywords_list(keywords)

        elif choice == "4":
            # Reset to default
            if confirm_action("Reset semua keyword ke default?"):
                from config import KEYWORDS_FILE as kf

                # Reload original defaults by reading the packaged file
                default_keywords = [
                    "moots", "mutual", "mutualan", "mutual ig",
                    "mutual instagram", "ig", "IG", "instagram",
                    "drop ig", "spill ig", "bagi ig", "share ig",
                    "add ig", "follow ig", "follow back", "fb",
                    "follback", "f4f", "lfl", "sfs", "talk",
                    "need friends", "looking for friends", "looking moots",
                    "open moots", "open mutual", "let's be mutual",
                    "anyone?", "cari teman", "cari mutual", "teman baru",
                    "ngobrol yuk", "ayo mutualan", "dm ig", "dm me",
                    "chat yuk", "mabar", "kenalan", "moots pls",
                    "moots?", "moots dong", "moots yuk", "mutuals",
                    "moots id", "ig?", "ig dong", "drop username",
                    "drop @", "drop your ig", "leave your ig",
                    "comment your ig", "share your username",
                    "#moots", "#mutual", "#mutualan", "#instagram",
                    "#followback", "#f4f", "#friends", "#talk",
                    "#newfriends",
                ]
                keywords = default_keywords
                save_keywords(KEYWORDS_FILE, keywords)
                show_success(f"Keywords direset ke default ({len(keywords)} keyword).")

        elif choice == "0":
            break

        else:
            show_error("Pilihan tidak valid.")


def handle_view_results() -> None:
    """Handle the View Results menu option."""
    if not _results:
        show_warning("Belum ada hasil pencarian. Jalankan pencarian terlebih dahulu.")
        return
    show_results_table(_results)


def handle_export_csv() -> None:
    """Handle the Export CSV menu option."""
    if not _results:
        show_warning("Belum ada data untuk diekspor. Jalankan pencarian terlebih dahulu.")
        return
    export_csv(_results)
    logger.info("CSV export completed")


def handle_export_excel() -> None:
    """Handle the Export Excel menu option."""
    if not _results:
        show_warning("Belum ada data untuk diekspor. Jalankan pencarian terlebih dahulu.")
        return
    export_excel(_results)
    logger.info("Excel export completed")


def handle_statistics() -> None:
    """Handle the Statistics menu option."""
    if not _search_performed:
        show_warning("Belum ada statistik. Jalankan pencarian terlebih dahulu.")
        return
    show_statistics(_stats)


def handle_settings() -> None:
    """Handle the Settings menu option."""
    settings = {
        "Browser Mode": "Headless" if BROWSER_HEADLESS else "Visible",
        "Scroll Count": str(SCROLL_COUNT),
        "Search Delay": f"{SEARCH_DELAY_MIN}-{SEARCH_DELAY_MAX}s",
        "Keywords File": str(KEYWORDS_FILE),
        "Output Directory": str(Path("output").resolve()),
        "Logs Directory": str(LOGS_DIR),
        "Version": APP_VERSION,
    }
    show_settings(settings)


# ─── Main Menu Loop ─────────────────────────────────────────────────────────────


async def main_menu() -> None:
    """Run the interactive main menu loop."""
    show_banner()

    while True:
        show_menu()
        choice = prompt_menu_choice()

        if choice == "1":
            await handle_search()
        elif choice == "2":
            handle_edit_keywords()
        elif choice == "3":
            handle_view_results()
        elif choice == "4":
            handle_export_csv()
        elif choice == "5":
            handle_export_excel()
        elif choice == "6":
            handle_statistics()
        elif choice == "7":
            handle_settings()
        elif choice == "0":
            console.print()
            if confirm_action("Keluar dari ThreadScout?"):
                console.print()
                show_info("Terima kasih telah menggunakan ThreadScout! 👋")
                show_divider()
                console.print()
                logger.info("ThreadScout exited by user")
                break
        else:
            show_error("Pilihan tidak valid. Gunakan angka 0-7.")

        console.print()


# ─── CLI Entry Point ────────────────────────────────────────────────────────────


@app.command()
def run(
    headless: bool = typer.Option(
        True,
        "--headless/--no-headless",
        help="Run browser in headless mode",
    ),
    scroll: int = typer.Option(
        SCROLL_COUNT,
        "--scroll",
        "-s",
        help="Number of scroll-downs per keyword",
    ),
) -> None:
    """
    🔍 ThreadScout — Instagram Mutual Research Tool

    Kumpulkan username Instagram dari posting Threads berdasarkan keyword.
    """
    import config

    # Apply CLI overrides
    config.BROWSER_HEADLESS = headless
    config.SCROLL_COUNT = scroll

    # Initialize
    ensure_directories()
    setup_logging()

    logger.info(f"CLI args: headless={headless}, scroll={scroll}")

    try:
        asyncio.run(main_menu())
    except KeyboardInterrupt:
        console.print()
        show_info("ThreadScout dihentikan oleh pengguna.")
        logger.info("ThreadScout interrupted by user (KeyboardInterrupt)")
    except Exception as e:
        show_error(f"Fatal error: {e}")
        logger.critical(f"Fatal error: {e}", exc_info=True)
        raise typer.Exit(code=1)


# ─── Direct Execution ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
