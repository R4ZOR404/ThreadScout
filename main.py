"""
ThreadScout - Main Entry Point v2.1
=====================================
Professional interactive CLI for collecting Instagram references from
publicly accessible Threads posts. Features unlimited search with
graceful Ctrl+C handling that returns to menu instead of crashing.

Usage:
    python main.py          # Start the interactive menu
    python main.py --help   # Show help
"""

import asyncio
import signal
import sys
from pathlib import Path

import typer
from loguru import logger

from config import (
    APP_NAME,
    APP_VERSION,
    BROWSER_HEADLESS,
    COLORS,
    CONCURRENT_TABS,
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
    logger.remove()

    log_file = LOGS_DIR / get_log_filename()
    logger.add(
        log_file,
        rotation="00:00",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {module}:{function}:{line} | {message}",
        level="DEBUG",
        encoding="utf-8",
    )

    # Only show CRITICAL errors in terminal (Rich handles the rest)
    logger.add(
        sys.stderr,
        level="CRITICAL",
        format="{message}",
    )

    logger.info(f"{'=' * 60}")
    logger.info(f"{APP_NAME} v{APP_VERSION} started")
    logger.info(f"{'=' * 60}")


# ─── Menu Handlers ──────────────────────────────────────────────────────────────


async def handle_search() -> None:
    """
    Start unlimited search — runs until Ctrl+C.

    Ctrl+C is caught INSIDE the searcher and returns here gracefully.
    The main menu loop is never interrupted.
    """
    global _results, _stats, _search_performed

    try:
        keywords = load_keywords(KEYWORDS_FILE)
    except Exception as e:
        show_error(f"Gagal memuat keywords: {e}")
        return

    if not keywords:
        show_warning("Tidak ada keyword. Tambahkan keyword melalui menu 2.")
        return

    console.print()
    show_info(f"📋 Total {len(keywords)} keyword tersedia")
    show_info(f"⚡ Mode: {CONCURRENT_TABS} tab paralel | Pencarian unlimited")
    show_info(f"📸 Hanya mengumpulkan posting dengan Instagram")
    show_info(f"⏹️  Tekan Ctrl+C kapan saja untuk berhenti")
    console.print()

    if not confirm_action("Mulai pencarian unlimited?"):
        show_info("Pencarian dibatalkan.")
        return

    # The searcher handles Ctrl+C internally — it will NEVER crash here
    searcher = ThreadsSearcher()
    _results = await searcher.run_search(keywords)
    _stats = searcher.stats.to_dict()
    _search_performed = True

    logger.info(f"Search returned: {len(_results)} results")

    # Auto-suggest export if results found
    if _results:
        show_info(f"💡 Gunakan menu 4 (CSV) atau 5 (Excel) untuk mengekspor {len(_results)} hasil")


def handle_edit_keywords() -> None:
    """Manage keyword list: add, remove, view, reset."""
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
            new_kw = console.input(
                f"  [{COLORS['orange']}]▶[/] Masukkan keyword baru: "
            ).strip()
            if new_kw:
                if new_kw in keywords:
                    show_warning(f"Keyword '{new_kw}' sudah ada.")
                else:
                    keywords.append(new_kw)
                    save_keywords(KEYWORDS_FILE, keywords)
                    show_success(f"Keyword '{new_kw}' ditambahkan. Total: {len(keywords)}")
            else:
                show_warning("Keyword tidak boleh kosong.")

        elif choice == "2":
            show_keywords_list(keywords)
            idx_input = console.input(
                f"  [{COLORS['orange']}]▶[/] Nomor keyword yang dihapus: "
            ).strip()
            if idx_input.isdigit():
                idx = int(idx_input) - 1
                if 0 <= idx < len(keywords):
                    removed = keywords.pop(idx)
                    save_keywords(KEYWORDS_FILE, keywords)
                    show_success(f"Keyword '{removed}' dihapus. Sisa: {len(keywords)}")
                else:
                    show_error("Nomor tidak valid.")
            else:
                show_error("Masukkan nomor yang valid.")

        elif choice == "3":
            show_keywords_list(keywords)

        elif choice == "4":
            if confirm_action("Reset semua keyword ke default?"):
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
    """Display search results table."""
    if not _results:
        show_warning("Belum ada hasil. Jalankan pencarian terlebih dahulu (menu 1).")
        return
    show_results_table(_results)


def handle_export_csv() -> None:
    """Export results to CSV."""
    if not _results:
        show_warning("Belum ada data untuk diekspor.")
        return
    export_csv(_results)
    logger.info(f"CSV exported: {len(_results)} rows")


def handle_export_excel() -> None:
    """Export results to Excel."""
    if not _results:
        show_warning("Belum ada data untuk diekspor.")
        return
    export_excel(_results)
    logger.info(f"Excel exported: {len(_results)} rows")


def handle_statistics() -> None:
    """Display search statistics dashboard."""
    if not _search_performed:
        show_warning("Belum ada statistik. Jalankan pencarian terlebih dahulu.")
        return
    show_statistics(_stats)


def handle_settings() -> None:
    """Display current application settings."""
    settings = {
        "Browser Mode": "Headless" if BROWSER_HEADLESS else "Visible",
        "Concurrent Tabs": str(CONCURRENT_TABS),
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
    """
    Run the interactive main menu loop.

    This loop is designed to survive Ctrl+C during searches.
    Ctrl+C at the menu prompt simply re-shows the menu.
    """
    show_banner()

    while True:
        try:
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
                    # Auto-export if there are unsaved results
                    if _results:
                        show_info(f"💾 Menyimpan {len(_results)} hasil sebelum keluar...")
                        export_csv(_results)
                        export_excel(_results)

                    console.print()
                    show_info("Terima kasih telah menggunakan ThreadScout! 👋")
                    show_divider()
                    console.print()
                    logger.info("ThreadScout exited by user")
                    break
            else:
                show_error("Pilihan tidak valid. Gunakan angka 0-7.")

        except KeyboardInterrupt:
            # Ctrl+C at menu prompt → just re-show menu
            console.print()
            show_info("💡 Gunakan menu 0 untuk keluar dengan aman.")
            continue
        except EOFError:
            # Handle pipe/redirect end
            break

        console.print()


# ─── CLI Entry Point ────────────────────────────────────────────────────────────


@app.command()
def run(
    headless: bool = typer.Option(
        True,
        "--headless/--no-headless",
        help="Run browser in headless mode (default: headless)",
    ),
    scroll: int = typer.Option(
        SCROLL_COUNT,
        "--scroll",
        "-s",
        help="Number of page scroll-downs per keyword search",
    ),
) -> None:
    """
    🔍 ThreadScout v2.1 — Instagram Mutual Research Tool (Unlimited Edition)

    Kumpulkan username dan link Instagram dari posting Threads.
    Pencarian berjalan tanpa batas hingga Ctrl+C ditekan.
    """
    import config

    # Apply CLI overrides
    config.BROWSER_HEADLESS = headless
    config.SCROLL_COUNT = scroll

    # Initialize
    ensure_directories()
    setup_logging()

    logger.info(f"CLI: headless={headless}, scroll={scroll}")

    try:
        asyncio.run(main_menu())
    except KeyboardInterrupt:
        # Final fallback — should rarely reach here
        console.print()
        show_info("ThreadScout dihentikan. Sampai jumpa! 👋")
        logger.info("ThreadScout interrupted at top level")
    except Exception as e:
        show_error(f"Fatal error: {e}")
        logger.critical(f"Fatal error: {e}", exc_info=True)
        raise typer.Exit(code=1)


# ─── Direct Execution ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
