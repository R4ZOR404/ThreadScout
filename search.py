"""
ThreadScout - Search Module v2.0
==================================
Playwright-based Threads search engine with unlimited continuous searching,
maximum concurrency, and resource-blocking for extreme speed.

The search runs indefinitely until the user presses Ctrl+C.
Only posts with actual Instagram usernames/links are collected.
"""

import asyncio
import random
import time
from dataclasses import dataclass, field
from urllib.parse import quote_plus

from loguru import logger
from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
    Route,
    TimeoutError as PlaywrightTimeout,
)
from rich.live import Live
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.align import Align
from rich import box

from config import (
    BROWSER_HEADLESS,
    BROWSER_TIMEOUT,
    COLORS,
    CONCURRENT_TABS,
    SCROLL_COUNT,
    SCROLL_DELAY,
    SEARCH_DELAY_MIN,
    SEARCH_DELAY_MAX,
    THREADS_SEARCH_URL,
)
from extractor import extract_instagram
from filters import apply_filters
from ui import console, show_error, show_info, show_success, show_warning
from utils import get_timestamp, format_duration


# ─── Data Classes ────────────────────────────────────────────────────────────────


@dataclass
class PostData:
    """Represents a single extracted Threads post with confirmed IG reference."""
    threads_username: str = ""
    post_url: str = ""
    post_content: str = ""
    keyword: str = ""
    instagram: str = ""
    instagram_link: str = ""
    date_scraped: str = ""

    def to_dict(self) -> dict:
        """Convert to a dictionary matching export columns."""
        return {
            "Threads": self.threads_username,
            "Instagram": self.instagram,
            "Instagram Link": self.instagram_link,
            "Keyword": self.keyword,
            "Post URL": self.post_url,
            "Post Content": self.post_content,
            "Date Scraped": self.date_scraped,
        }


@dataclass
class SearchStats:
    """Tracks statistics across a search session."""
    keywords_processed: int = 0
    cycles_completed: int = 0
    posts_checked: int = 0
    posts_passed: int = 0
    ig_found: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        """Total search duration in seconds."""
        end = self.end_time if self.end_time else time.time()
        if end and self.start_time:
            return end - self.start_time
        return 0.0

    @property
    def success_rate(self) -> float:
        """Percentage of checked posts that yielded IG usernames."""
        if self.posts_checked == 0:
            return 0.0
        return (self.ig_found / self.posts_checked) * 100

    @property
    def ig_per_minute(self) -> float:
        """Instagram accounts found per minute."""
        if self.duration == 0:
            return 0.0
        return (self.ig_found / self.duration) * 60

    def to_dict(self) -> dict:
        """Convert to a dictionary for the statistics dashboard."""
        return {
            "keywords_processed": self.keywords_processed,
            "cycles_completed": self.cycles_completed,
            "posts_checked": self.posts_checked,
            "posts_passed": self.posts_passed,
            "ig_found": self.ig_found,
            "duration": self.duration,
            "success_rate": self.success_rate,
            "ig_per_minute": self.ig_per_minute,
        }


# ─── Blocked Resource Types ─────────────────────────────────────────────────────
# Block these to speed up page loading dramatically

_BLOCKED_RESOURCE_TYPES = {"image", "media", "font", "stylesheet"}
_BLOCKED_URL_PATTERNS = [
    "google-analytics", "facebook.com/tr", "doubleclick",
    "analytics", "tracking", "ads", ".png", ".jpg", ".jpeg",
    ".gif", ".svg", ".woff", ".woff2", ".ttf", ".ico",
]


# ─── Threads Searcher ───────────────────────────────────────────────────────────


class ThreadsSearcher:
    """
    Async Playwright-based unlimited searcher for Threads.net posts.

    Key features:
    - Runs indefinitely until Ctrl+C
    - 10 concurrent browser tabs for maximum speed
    - Blocks images/fonts/CSS/ads for faster page loads
    - Only collects posts with confirmed Instagram references
    - Live dashboard showing real-time progress
    - Cycles through all keywords repeatedly
    """

    def __init__(
        self,
        headless: bool = BROWSER_HEADLESS,
        timeout: int = BROWSER_TIMEOUT,
        scroll_count: int = SCROLL_COUNT,
        max_concurrent: int = CONCURRENT_TABS,
    ) -> None:
        self.headless = headless
        self.timeout = timeout
        self.scroll_count = scroll_count
        self.max_concurrent = max_concurrent

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._stop_event = asyncio.Event()

        self.results: list[PostData] = []
        self.stats = SearchStats()
        self._seen_urls: set[str] = set()
        self._seen_ig: set[str] = set()
        self._lock = asyncio.Lock()

    async def _block_resources(self, route: Route) -> None:
        """Block unnecessary resources to speed up loading."""
        request = route.request
        if request.resource_type in _BLOCKED_RESOURCE_TYPES:
            await route.abort()
            return
        url = request.url.lower()
        for pattern in _BLOCKED_URL_PATTERNS:
            if pattern in url:
                await route.abort()
                return
        await route.continue_()

    async def _launch_browser(self) -> None:
        """Launch Playwright browser with maximum speed settings."""
        logger.info("Launching browser (speed-optimized)...")

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-extensions",
                "--disable-background-networking",
                "--disable-default-apps",
                "--disable-sync",
                "--no-first-run",
                "--disable-translate",
                "--hide-scrollbars",
                "--mute-audio",
                "--disable-notifications",
            ],
        )

        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="id-ID",
            timezone_id="Asia/Jakarta",
            java_script_enabled=True,
        )

        # Remove webdriver detection
        await self._context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            """
        )

        # Block heavy resources globally
        await self._context.route("**/*", self._block_resources)

        logger.info("Browser launched (resources blocked for speed)")

    async def _close_browser(self) -> None:
        """Safely close the browser and all resources."""
        try:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            logger.info("Browser closed")
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")

    async def _scroll_page(self, page: Page) -> None:
        """Fast scroll the page to load more posts."""
        for _ in range(self.scroll_count):
            await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            await asyncio.sleep(SCROLL_DELAY + random.uniform(0.1, 0.3))

    async def _check_for_obstacles(self, page: Page) -> str | None:
        """Check if Threads is showing login wall or CAPTCHA."""
        try:
            for selector in [
                "iframe[src*='captcha']", "iframe[src*='recaptcha']",
                "[class*='captcha']",
            ]:
                if await page.query_selector(selector):
                    return "CAPTCHA"
            for selector in [
                '[data-testid="login-button"]', 'text="Log in to see more"',
            ]:
                if await page.query_selector(selector):
                    return "Login required"
        except Exception:
            pass
        return None

    async def _extract_posts_from_page(
        self, page: Page, keyword: str
    ) -> list[PostData]:
        """
        Extract ONLY posts with confirmed Instagram references.

        Posts without Instagram username/link are completely skipped.
        """
        posts: list[PostData] = []

        try:
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(1.0)

            # Try selectors for Threads posts
            post_selectors = [
                '[data-pressable-container="true"]',
                'div[class*="post"]',
                'article',
                'div[role="article"]',
                'div[class*="Feed"]',
            ]

            post_elements = []
            for selector in post_selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    post_elements = elements
                    break

            if not post_elements:
                return posts

            for element in post_elements:
                if self._stop_event.is_set():
                    break

                try:
                    text_content = await element.inner_text()
                    if not text_content or len(text_content.strip()) < 10:
                        continue

                    async with self._lock:
                        self.stats.posts_checked += 1

                    # Apply content filters
                    filter_result = apply_filters(text_content)
                    if not filter_result.passed:
                        continue

                    async with self._lock:
                        self.stats.posts_passed += 1

                    # Extract Instagram references
                    extraction = extract_instagram(text_content)

                    # ★ ONLY collect posts with actual Instagram found ★
                    if not extraction.found:
                        continue

                    ig_reference = extraction.primary
                    ig_link = extraction.instagram_link

                    # Skip duplicates
                    async with self._lock:
                        if ig_reference.lower() in self._seen_ig:
                            continue
                        self._seen_ig.add(ig_reference.lower())
                        self.stats.ig_found += 1

                    # Extract Threads username
                    username = ""
                    username_el = await element.query_selector(
                        'a[href*="/@"], span[class*="username"], '
                        'a[role="link"][tabindex="0"]'
                    )
                    if username_el:
                        username_text = await username_el.inner_text()
                        username = username_text.strip()
                        if username and not username.startswith("@"):
                            username = f"@{username}"

                    # Extract post URL
                    post_url = ""
                    link_el = await element.query_selector(
                        'a[href*="/post/"], a[href*="/@"][href*="/p/"], '
                        'a[role="link"][href*="/t/"]'
                    )
                    if link_el:
                        href = await link_el.get_attribute("href")
                        if href:
                            post_url = f"https://www.threads.net{href}" if href.startswith("/") else href

                    # Deduplicate by URL
                    async with self._lock:
                        if post_url and post_url in self._seen_urls:
                            continue
                        if post_url:
                            self._seen_urls.add(post_url)

                    post = PostData(
                        threads_username=username or "Unknown",
                        post_url=post_url,
                        post_content=text_content.strip()[:500],
                        keyword=keyword,
                        instagram=ig_reference,
                        instagram_link=ig_link,
                        date_scraped=get_timestamp(),
                    )

                    posts.append(post)

                except Exception as e:
                    logger.debug(f"Error extracting element: {e}")
                    continue

        except PlaywrightTimeout:
            logger.warning(f"Timeout for keyword: {keyword}")
        except Exception as e:
            logger.error(f"Extraction error: {e}")

        return posts

    async def _search_single_keyword(
        self, keyword: str, semaphore: asyncio.Semaphore
    ) -> list[PostData]:
        """Search Threads for a single keyword using its own tab."""
        async with semaphore:
            if self._stop_event.is_set() or not self._context:
                return []

            page: Page | None = None
            try:
                page = await self._context.new_page()
                page.set_default_timeout(self.timeout)

                encoded_keyword = quote_plus(keyword)
                search_url = f"{THREADS_SEARCH_URL}{encoded_keyword}"

                response = await page.goto(
                    search_url, wait_until="domcontentloaded", timeout=self.timeout
                )

                if response and response.status >= 400:
                    async with self._lock:
                        self.stats.errors.append(f"HTTP {response.status}: {keyword}")
                    return []

                obstacle = await self._check_for_obstacles(page)
                if obstacle:
                    async with self._lock:
                        self.stats.errors.append(f"{obstacle}: {keyword}")
                    return []

                await asyncio.sleep(1.0)
                await self._scroll_page(page)

                posts = await self._extract_posts_from_page(page, keyword)

                async with self._lock:
                    self.stats.keywords_processed += 1

                # Minimal delay
                await asyncio.sleep(random.uniform(SEARCH_DELAY_MIN, SEARCH_DELAY_MAX))

                return posts

            except PlaywrightTimeout:
                async with self._lock:
                    self.stats.errors.append(f"Timeout: {keyword}")
                return []
            except Exception as e:
                async with self._lock:
                    self.stats.errors.append(f"Error ({keyword}): {str(e)[:50]}")
                return []
            finally:
                if page:
                    try:
                        await page.close()
                    except Exception:
                        pass

    def _build_live_dashboard(self) -> Panel:
        """Build the real-time statistics dashboard for Live display."""
        elapsed = time.time() - self.stats.start_time if self.stats.start_time else 0

        # Stats table
        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
        table.add_column("Metric", style=f"bold {COLORS['white']}", width=28)
        table.add_column("Value", style=f"bold {COLORS['orange']}", width=18, justify="right")

        table.add_row("🔄  Siklus keyword", str(self.stats.cycles_completed))
        table.add_row("🔑  Keyword diproses", str(self.stats.keywords_processed))
        table.add_row("📝  Posting diperiksa", str(self.stats.posts_checked))
        table.add_row("✅  Posting lolos filter", str(self.stats.posts_passed))
        table.add_row(
            "📸  Instagram ditemukan",
            f"[bold {COLORS['success']}]{self.stats.ig_found}[/]",
        )
        table.add_row("⚡  IG per menit", f"{self.stats.ig_per_minute:.1f}")
        table.add_row("⏱️   Waktu berjalan", format_duration(elapsed))
        table.add_row("❌  Errors", str(len(self.stats.errors)))

        # Recent results preview (last 5)
        if self.results:
            table.add_row("", "")
            table.add_row(
                f"[bold {COLORS['pink']}]── Hasil Terbaru ──[/]",
                "",
            )
            for post in self.results[-5:]:
                ig_display = post.instagram[:20]
                table.add_row(
                    f"  {ig_display}",
                    post.instagram_link[:30] if post.instagram_link != "Not Found" else "",
                )

        # Footer
        footer = Text()
        footer.append("\n  Tekan ", style=COLORS["light_gray"])
        footer.append("Ctrl+C", style=f"bold {COLORS['orange']}")
        footer.append(" untuk berhenti", style=COLORS["light_gray"])

        panel_content = Text()
        panel_content.append_text(Text.from_ansi(table.__rich_console__(console, console.options).__str__() if False else ""))

        panel = Panel(
            table,
            title=f"[bold {COLORS['purple']}]━━━ 🔍 PENCARIAN UNLIMITED AKTIF ━━━[/]",
            subtitle=f"[{COLORS['light_gray']}]Ctrl+C untuk berhenti[/]",
            border_style=COLORS["pink"],
            box=box.DOUBLE_EDGE,
            padding=(1, 2),
        )

        return panel

    async def run_search(self, keywords: list[str]) -> list[dict]:
        """
        Execute UNLIMITED continuous search across all keywords.

        The search loops through all keywords repeatedly, running multiple
        keywords in parallel via browser tabs. It continues indefinitely
        until the user presses Ctrl+C.

        Only posts with confirmed Instagram usernames/links are collected.

        Args:
            keywords: List of search keywords.

        Returns:
            List of result dictionaries (only those with IG found).
        """
        self.results = []
        self.stats = SearchStats()
        self._seen_urls = set()
        self._seen_ig = set()
        self._stop_event.clear()
        self.stats.start_time = time.time()

        console.print()
        show_info(f"🚀 Memulai pencarian UNLIMITED dengan {len(keywords)} keyword")
        show_info(f"⚡ Mode: {self.max_concurrent} tab paralel | Resource blocking ON")
        show_info(f"📸 Hanya mengumpulkan posting dengan Instagram yang ditemukan")
        show_warning("Tekan Ctrl+C kapan saja untuk menghentikan pencarian")
        console.print()

        try:
            # Launch browser
            with console.status(
                f"[{COLORS['pink']}]🚀 Meluncurkan browser...",
                spinner="dots",
            ):
                await self._launch_browser()

            show_success("Browser diluncurkan (mode kecepatan maksimal)")
            console.print()

            semaphore = asyncio.Semaphore(self.max_concurrent)
            cycle = 0

            # ★ INFINITE LOOP — runs until Ctrl+C ★
            with Live(
                self._build_live_dashboard(),
                console=console,
                refresh_per_second=2,
                transient=False,
            ) as live:
                while not self._stop_event.is_set():
                    cycle += 1
                    self.stats.cycles_completed = cycle

                    # Shuffle keywords each cycle for variety
                    shuffled = keywords.copy()
                    random.shuffle(shuffled)

                    # Process keywords in batches for this cycle
                    batch_size = self.max_concurrent * 2
                    for i in range(0, len(shuffled), batch_size):
                        if self._stop_event.is_set():
                            break

                        batch = shuffled[i : i + batch_size]

                        # Launch batch concurrently
                        tasks = [
                            self._search_single_keyword(kw, semaphore)
                            for kw in batch
                        ]

                        batch_results = await asyncio.gather(
                            *tasks, return_exceptions=True
                        )

                        for result in batch_results:
                            if isinstance(result, list):
                                self.results.extend(result)
                            elif isinstance(result, Exception):
                                logger.error(f"Task exception: {result}")

                        # Update live dashboard
                        live.update(self._build_live_dashboard())

                    logger.info(
                        f"Cycle {cycle} complete: "
                        f"{self.stats.ig_found} IG found total"
                    )

        except KeyboardInterrupt:
            show_info("\n⏹️  Pencarian dihentikan oleh pengguna")
        except Exception as e:
            logger.error(f"Search pipeline error: {e}")
            show_error(f"Error: {str(e)}")
        finally:
            self._stop_event.set()

            # Close browser
            with console.status(
                f"[{COLORS['pink']}]Menutup browser...",
                spinner="dots",
            ):
                await self._close_browser()

            self.stats.end_time = time.time()

        # Final Summary
        console.print()
        console.print(
            f"  [{COLORS['purple']}]{'━' * 50}[/]"
        )
        show_success(
            f"Total {self.stats.ig_found} Instagram ditemukan "
            f"dari {self.stats.posts_checked} posting"
        )
        show_info(
            f"⚡ Kecepatan: {self.stats.ig_per_minute:.1f} IG/menit | "
            f"Waktu: {format_duration(self.stats.duration)} | "
            f"Siklus: {self.stats.cycles_completed}"
        )

        if self.stats.errors:
            show_warning(f"{len(self.stats.errors)} error selama pencarian")

        logger.info(
            f"FINAL: {len(self.results)} results, "
            f"{self.stats.ig_found} IG, "
            f"{self.stats.cycles_completed} cycles, "
            f"{self.stats.duration:.1f}s, "
            f"{self.stats.ig_per_minute:.1f} IG/min"
        )

        return [post.to_dict() for post in self.results]

    def stop(self) -> None:
        """Signal the search to stop after current batch."""
        self._stop_event.set()
