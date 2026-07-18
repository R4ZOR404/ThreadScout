"""
ThreadScout - Search Module v2.1
==================================
Playwright-based Threads search engine with unlimited continuous searching,
maximum concurrency, resource-blocking, and graceful shutdown.

The search runs indefinitely until the user presses Ctrl+C.
Only posts with actual Instagram usernames/links are collected.
Gracefully returns to main menu on stop — does NOT crash the program.
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
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
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
        end = self.end_time if self.end_time else time.time()
        if end and self.start_time:
            return end - self.start_time
        return 0.0

    @property
    def success_rate(self) -> float:
        if self.posts_checked == 0:
            return 0.0
        return (self.ig_found / self.posts_checked) * 100

    @property
    def ig_per_minute(self) -> float:
        if self.duration == 0:
            return 0.0
        return (self.ig_found / self.duration) * 60

    def to_dict(self) -> dict:
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


# ─── Blocked Resources ──────────────────────────────────────────────────────────

_BLOCKED_RESOURCE_TYPES = {"image", "media", "font", "stylesheet"}
_BLOCKED_PATTERNS = [
    "google-analytics", "facebook.com/tr", "doubleclick",
    "analytics", "tracking", ".png", ".jpg", ".jpeg",
    ".gif", ".svg", ".woff", ".woff2", ".ttf", ".ico",
]


# ─── Threads Searcher ───────────────────────────────────────────────────────────


class ThreadsSearcher:
    """
    Unlimited async Threads searcher with graceful shutdown.

    - Runs indefinitely, cycling keywords with shuffle
    - 10 concurrent browser tabs
    - Blocks images/fonts/CSS for speed
    - Only collects posts with confirmed IG
    - Ctrl+C gracefully stops and returns to menu
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

    # ── Browser Lifecycle ────────────────────────────────────────────────────

    async def _block_resources(self, route: Route) -> None:
        """Block unnecessary resources for speed."""
        request = route.request
        if request.resource_type in _BLOCKED_RESOURCE_TYPES:
            await route.abort()
            return
        url_lower = request.url.lower()
        for pattern in _BLOCKED_PATTERNS:
            if pattern in url_lower:
                await route.abort()
                return
        await route.continue_()

    async def _launch_browser(self) -> None:
        """Launch browser with maximum speed settings."""
        logger.info("Launching browser...")
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
        )
        await self._context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        await self._context.route("**/*", self._block_resources)
        logger.info("Browser launched successfully")

    async def _close_browser(self) -> None:
        """Safely close all browser resources."""
        try:
            if self._context:
                await self._context.close()
                self._context = None
            if self._browser:
                await self._browser.close()
                self._browser = None
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
            logger.info("Browser closed gracefully")
        except Exception as e:
            logger.warning(f"Browser close warning: {e}")

    # ── Page Operations ──────────────────────────────────────────────────────

    async def _scroll_page(self, page: Page) -> None:
        """Fast aggressive scroll to load maximum posts."""
        for _ in range(self.scroll_count):
            if self._stop_event.is_set():
                return
            await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
            await asyncio.sleep(SCROLL_DELAY + random.uniform(0.05, 0.2))

    async def _check_obstacles(self, page: Page) -> str | None:
        """Check for CAPTCHA or login walls."""
        try:
            for sel in ["iframe[src*='captcha']", "iframe[src*='recaptcha']", "[class*='captcha']"]:
                if await page.query_selector(sel):
                    return "CAPTCHA"
            for sel in ['[data-testid="login-button"]', 'text="Log in to see more"']:
                if await page.query_selector(sel):
                    return "Login required"
        except Exception:
            pass
        return None

    # ── Post Extraction ──────────────────────────────────────────────────────

    async def _extract_posts(self, page: Page, keyword: str) -> list[PostData]:
        """Extract ONLY posts with confirmed Instagram references."""
        posts: list[PostData] = []

        try:
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(0.8)

            # Try multiple selectors
            post_elements = []
            for selector in [
                '[data-pressable-container="true"]',
                'div[class*="post"]', 'article',
                'div[role="article"]', 'div[class*="Feed"]',
            ]:
                elements = await page.query_selector_all(selector)
                if elements:
                    post_elements = elements
                    break

            for element in post_elements:
                if self._stop_event.is_set():
                    break

                try:
                    text_content = await element.inner_text()
                    if not text_content or len(text_content.strip()) < 10:
                        continue

                    async with self._lock:
                        self.stats.posts_checked += 1

                    # Filter check
                    if not apply_filters(text_content).passed:
                        continue

                    async with self._lock:
                        self.stats.posts_passed += 1

                    # Extract Instagram — SKIP if not found
                    extraction = extract_instagram(text_content)
                    if not extraction.found:
                        continue

                    ig_ref = extraction.primary
                    ig_link = extraction.instagram_link

                    # Deduplicate by IG username
                    async with self._lock:
                        if ig_ref.lower() in self._seen_ig:
                            continue
                        self._seen_ig.add(ig_ref.lower())
                        self.stats.ig_found += 1

                    # Extract Threads username
                    username = ""
                    el = await element.query_selector(
                        'a[href*="/@"], span[class*="username"], a[role="link"][tabindex="0"]'
                    )
                    if el:
                        txt = await el.inner_text()
                        username = txt.strip()
                        if username and not username.startswith("@"):
                            username = f"@{username}"

                    # Extract post URL
                    post_url = ""
                    link_el = await element.query_selector(
                        'a[href*="/post/"], a[href*="/@"][href*="/p/"], a[role="link"][href*="/t/"]'
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

                    posts.append(PostData(
                        threads_username=username or "Unknown",
                        post_url=post_url,
                        post_content=text_content.strip()[:500],
                        keyword=keyword,
                        instagram=ig_ref,
                        instagram_link=ig_link,
                        date_scraped=get_timestamp(),
                    ))

                except Exception:
                    continue

        except PlaywrightTimeout:
            pass
        except Exception as e:
            logger.debug(f"Extract error: {e}")

        return posts

    # ── Single Keyword Search ────────────────────────────────────────────────

    async def _search_keyword(self, keyword: str, sem: asyncio.Semaphore) -> list[PostData]:
        """Search one keyword in its own browser tab."""
        async with sem:
            if self._stop_event.is_set() or not self._context:
                return []

            page: Page | None = None
            try:
                page = await self._context.new_page()
                page.set_default_timeout(self.timeout)

                url = f"{THREADS_SEARCH_URL}{quote_plus(keyword)}"
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)

                if resp and resp.status >= 400:
                    return []

                obstacle = await self._check_obstacles(page)
                if obstacle:
                    async with self._lock:
                        self.stats.errors.append(f"{obstacle}: {keyword}")
                    return []

                await asyncio.sleep(0.8)
                await self._scroll_page(page)

                posts = await self._extract_posts(page, keyword)

                async with self._lock:
                    self.stats.keywords_processed += 1

                await asyncio.sleep(random.uniform(SEARCH_DELAY_MIN, SEARCH_DELAY_MAX))
                return posts

            except (PlaywrightTimeout, Exception) as e:
                logger.debug(f"Keyword '{keyword}' error: {e}")
                return []
            finally:
                if page:
                    try:
                        await page.close()
                    except Exception:
                        pass

    # ── Live Dashboard ───────────────────────────────────────────────────────

    def _build_dashboard(self) -> Panel:
        """Build real-time stats dashboard."""
        elapsed = time.time() - self.stats.start_time if self.stats.start_time else 0

        t = Table(box=box.SIMPLE, show_header=False, padding=(0, 2), expand=True)
        t.add_column("M", style=f"bold {COLORS['white']}", width=28, no_wrap=True)
        t.add_column("V", style=f"bold {COLORS['orange']}", width=20, justify="right", no_wrap=True)

        t.add_row("🔄  Siklus keyword", str(self.stats.cycles_completed))
        t.add_row("🔑  Keyword diproses", str(self.stats.keywords_processed))
        t.add_row("📝  Posting diperiksa", str(self.stats.posts_checked))
        t.add_row("✅  Posting lolos filter", str(self.stats.posts_passed))
        t.add_row(
            "📸  Instagram ditemukan",
            f"[bold {COLORS['success']}]{self.stats.ig_found}[/]",
        )
        t.add_row("⚡  IG per menit", f"{self.stats.ig_per_minute:.1f}")
        t.add_row("⏱️   Waktu berjalan", format_duration(elapsed))

        if self.stats.errors:
            t.add_row("❌  Errors", str(len(self.stats.errors)))

        # Last 5 results
        if self.results:
            t.add_row("", "")
            t.add_row(f"[{COLORS['pink']}]── 5 Hasil Terbaru ──[/]", "")
            for post in self.results[-5:]:
                t.add_row(
                    f"  {post.instagram[:18]}",
                    f"[{COLORS['info']}]{post.instagram_link[:28]}[/]",
                )

        return Panel(
            t,
            title=f"[bold {COLORS['purple']}]━━━ 🔍 PENCARIAN UNLIMITED ━━━[/]",
            subtitle=f"[{COLORS['light_gray']}]Tekan Ctrl+C untuk berhenti dan kembali ke menu[/]",
            border_style=COLORS["pink"],
            box=box.DOUBLE_EDGE,
            padding=(1, 2),
        )

    # ── Main Search Loop ─────────────────────────────────────────────────────

    async def run_search(self, keywords: list[str]) -> list[dict]:
        """
        Run unlimited continuous search. Returns gracefully on Ctrl+C.

        This method catches all interrupts internally and guarantees
        a clean return to the caller (main menu). It NEVER raises
        KeyboardInterrupt or CancelledError to the caller.
        """
        self.results = []
        self.stats = SearchStats()
        self._seen_urls = set()
        self._seen_ig = set()
        self._stop_event.clear()
        self.stats.start_time = time.time()

        console.print()
        show_info(f"🚀 Memulai pencarian UNLIMITED — {len(keywords)} keyword")
        show_info(f"⚡ {self.max_concurrent} tab paralel | Resource blocking ON")
        show_info(f"📸 Hanya mengumpulkan posting dengan Instagram")
        console.print()

        try:
            # Launch browser
            with console.status(
                f"[{COLORS['pink']}]🚀 Meluncurkan browser...", spinner="dots"
            ):
                await self._launch_browser()

            show_success("Browser aktif — pencarian dimulai!")
            console.print()

            sem = asyncio.Semaphore(self.max_concurrent)
            cycle = 0

            # ★ UNLIMITED LOOP ★
            live = Live(
                self._build_dashboard(),
                console=console,
                refresh_per_second=2,
                transient=True,
            )
            live.start()

            try:
                while not self._stop_event.is_set():
                    cycle += 1
                    self.stats.cycles_completed = cycle

                    shuffled = keywords.copy()
                    random.shuffle(shuffled)

                    # Process in batches
                    batch_size = self.max_concurrent * 2
                    for i in range(0, len(shuffled), batch_size):
                        if self._stop_event.is_set():
                            break

                        batch = shuffled[i : i + batch_size]
                        tasks = [self._search_keyword(kw, sem) for kw in batch]

                        try:
                            results = await asyncio.gather(*tasks, return_exceptions=True)
                            for r in results:
                                if isinstance(r, list):
                                    self.results.extend(r)
                        except Exception:
                            pass

                        live.update(self._build_dashboard())

                    logger.info(f"Cycle {cycle}: {self.stats.ig_found} IG total")

            except KeyboardInterrupt:
                # ★ GRACEFUL STOP — caught here, NOT propagated ★
                pass
            except asyncio.CancelledError:
                pass
            finally:
                live.stop()

        except KeyboardInterrupt:
            # Also catch if interrupted during browser launch
            pass
        except Exception as e:
            logger.error(f"Search error: {e}")
            show_error(f"Error: {str(e)}")
        finally:
            self._stop_event.set()
            self.stats.end_time = time.time()

            # Always close browser cleanly
            try:
                with console.status(
                    f"[{COLORS['pink']}]Menutup browser...", spinner="dots"
                ):
                    await self._close_browser()
            except Exception:
                pass

        # ── Final Summary ────────────────────────────────────────────────────
        console.print()
        console.print(f"  [{COLORS['purple']}]{'━' * 50}[/]")
        show_success(
            f"Pencarian selesai! {self.stats.ig_found} Instagram ditemukan"
        )
        show_info(
            f"⚡ {self.stats.ig_per_minute:.1f} IG/menit | "
            f"⏱️ {format_duration(self.stats.duration)} | "
            f"🔄 {self.stats.cycles_completed} siklus"
        )
        show_info(
            f"📝 {self.stats.posts_checked} posting diperiksa | "
            f"✅ {self.stats.posts_passed} lolos filter"
        )
        if self.stats.errors:
            show_warning(f"❌ {len(self.stats.errors)} error (CAPTCHA/timeout)")
        console.print(f"  [{COLORS['purple']}]{'━' * 50}[/]")
        console.print()

        logger.info(
            f"FINAL: {self.stats.ig_found} IG, "
            f"{self.stats.cycles_completed} cycles, "
            f"{self.stats.duration:.1f}s"
        )

        return [post.to_dict() for post in self.results]

    def stop(self) -> None:
        """Signal search to stop."""
        self._stop_event.set()
