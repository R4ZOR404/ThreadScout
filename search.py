"""
ThreadScout - Search Module
=============================
Playwright-based Threads search engine with concurrent multi-tab browsing,
scrolling, and post extraction optimized for speed.
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
    TimeoutError as PlaywrightTimeout,
)
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    MofNCompleteColumn,
    TimeElapsedColumn,
)

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
from utils import get_timestamp


# ─── Data Classes ────────────────────────────────────────────────────────────────


@dataclass
class PostData:
    """Represents a single extracted Threads post."""
    threads_username: str = ""
    post_url: str = ""
    post_content: str = ""
    keyword: str = ""
    instagram: str = "Not Found"
    instagram_link: str = "Not Found"
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
    posts_checked: int = 0
    posts_passed: int = 0
    ig_found: int = 0
    start_time: float = 0.0
    end_time: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        """Total search duration in seconds."""
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return 0.0

    @property
    def success_rate(self) -> float:
        """Percentage of checked posts that yielded IG usernames."""
        if self.posts_checked == 0:
            return 0.0
        return (self.ig_found / self.posts_checked) * 100

    def to_dict(self) -> dict:
        """Convert to a dictionary for the statistics dashboard."""
        return {
            "keywords_processed": self.keywords_processed,
            "posts_checked": self.posts_checked,
            "posts_passed": self.posts_passed,
            "ig_found": self.ig_found,
            "duration": self.duration,
            "success_rate": self.success_rate,
        }


# ─── Threads Searcher ───────────────────────────────────────────────────────────


class ThreadsSearcher:
    """
    Async Playwright-based searcher for Threads.net posts.

    Uses concurrent browser tabs for parallel keyword searches to maximize
    speed. Targets 100+ Instagram results in under 1 minute.
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

        self.results: list[PostData] = []
        self.stats = SearchStats()
        self._seen_urls: set[str] = set()
        self._seen_ig: set[str] = set()
        self._lock = asyncio.Lock()

    async def _launch_browser(self) -> None:
        """Launch Playwright browser with anti-detection settings."""
        logger.info("Launching browser...")

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-images",
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

        # Remove webdriver detection
        await self._context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            """
        )

        logger.info("Browser launched successfully")

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
        """Scroll the page to load more posts."""
        for i in range(self.scroll_count):
            await page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
            await asyncio.sleep(SCROLL_DELAY + random.uniform(0.2, 0.5))

    async def _check_for_obstacles(self, page: Page) -> str | None:
        """
        Check if Threads is showing login wall or CAPTCHA.

        Returns:
            Error message if obstacle detected, None if clear.
        """
        try:
            # CAPTCHA check
            for selector in [
                "iframe[src*='captcha']", "iframe[src*='recaptcha']",
                "[class*='captcha']", "iframe[src*='challenge']",
            ]:
                if await page.query_selector(selector):
                    return "CAPTCHA"

            # Login wall check
            for selector in [
                'text="Log in"', 'text="Sign up"',
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
        Extract post data from the current page.

        Args:
            page: Playwright page instance.
            keyword: The keyword used for this search.

        Returns:
            List of extracted PostData objects.
        """
        posts: list[PostData] = []

        try:
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(1.5)

            # Try multiple selectors for Threads posts
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
                    logger.debug(
                        f"Found {len(elements)} elements with selector: {selector}"
                    )
                    break

            if not post_elements:
                logger.debug("No post elements found with known selectors")
                return posts

            for element in post_elements:
                try:
                    text_content = await element.inner_text()
                    if not text_content or len(text_content.strip()) < 10:
                        continue

                    # Thread-safe stats update
                    async with self._lock:
                        self.stats.posts_checked += 1

                    # Extract username from post
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
                            if href.startswith("/"):
                                post_url = f"https://www.threads.net{href}"
                            else:
                                post_url = href

                    # Skip duplicates (thread-safe)
                    async with self._lock:
                        if post_url and post_url in self._seen_urls:
                            continue
                        if post_url:
                            self._seen_urls.add(post_url)

                    # Apply content filters
                    filter_result = apply_filters(text_content)
                    if not filter_result.passed:
                        continue

                    async with self._lock:
                        self.stats.posts_passed += 1

                    # Extract Instagram references
                    extraction = extract_instagram(text_content)
                    ig_reference = extraction.primary
                    ig_link = extraction.instagram_link

                    if extraction.found:
                        # Skip if we already have this IG username
                        async with self._lock:
                            if ig_reference.lower() in self._seen_ig:
                                continue
                            self._seen_ig.add(ig_reference.lower())
                            self.stats.ig_found += 1

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
                    logger.debug(
                        f"Extracted: {username} | IG: {ig_reference} | Link: {ig_link}"
                    )

                except Exception as e:
                    logger.debug(f"Error extracting post element: {e}")
                    continue

        except PlaywrightTimeout:
            logger.warning(f"Timeout waiting for page content (keyword: {keyword})")
        except Exception as e:
            logger.error(f"Error extracting posts: {e}")

        return posts

    async def _search_single_keyword(
        self, keyword: str, semaphore: asyncio.Semaphore, progress=None, task_id=None
    ) -> list[PostData]:
        """
        Search Threads for a single keyword using its own tab.

        Args:
            keyword: The search keyword.
            semaphore: Semaphore to limit concurrent tabs.
            progress: Optional Rich progress bar.
            task_id: Optional progress task ID.

        Returns:
            List of PostData objects found for this keyword.
        """
        async with semaphore:
            if not self._context:
                return []

            page: Page | None = None
            try:
                # Create a new tab for this keyword
                page = await self._context.new_page()
                page.set_default_timeout(self.timeout)

                encoded_keyword = quote_plus(keyword)
                search_url = f"{THREADS_SEARCH_URL}{encoded_keyword}"

                logger.info(f"Searching keyword: '{keyword}'")

                # Navigate to search URL
                response = await page.goto(
                    search_url, wait_until="domcontentloaded", timeout=self.timeout
                )

                if response and response.status >= 400:
                    logger.warning(f"HTTP {response.status} for keyword '{keyword}'")
                    async with self._lock:
                        self.stats.errors.append(f"HTTP {response.status}: {keyword}")
                    return []

                # Check for obstacles
                obstacle = await self._check_for_obstacles(page)
                if obstacle:
                    logger.warning(f"{obstacle} detected for keyword '{keyword}'")
                    async with self._lock:
                        self.stats.errors.append(f"{obstacle}: {keyword}")
                    return []

                # Wait for initial content load
                await asyncio.sleep(1.5)

                # Scroll to load more posts
                await self._scroll_page(page)

                # Extract posts
                posts = await self._extract_posts_from_page(page, keyword)

                async with self._lock:
                    self.stats.keywords_processed += 1

                logger.info(f"Keyword '{keyword}': found {len(posts)} matching posts")

                # Update progress
                if progress and task_id is not None:
                    progress.advance(task_id)

                # Small delay before releasing the tab slot
                await asyncio.sleep(random.uniform(SEARCH_DELAY_MIN, SEARCH_DELAY_MAX))

                return posts

            except PlaywrightTimeout:
                logger.warning(f"Timeout: {keyword}")
                async with self._lock:
                    self.stats.errors.append(f"Timeout: {keyword}")
                if progress and task_id is not None:
                    progress.advance(task_id)
                return []

            except Exception as e:
                logger.error(f"Error ({keyword}): {str(e)}")
                async with self._lock:
                    self.stats.errors.append(f"Error ({keyword}): {str(e)}")
                if progress and task_id is not None:
                    progress.advance(task_id)
                return []

            finally:
                # Always close the tab
                if page:
                    try:
                        await page.close()
                    except Exception:
                        pass

    async def run_search(self, keywords: list[str]) -> list[dict]:
        """
        Execute the full search pipeline across all keywords concurrently.

        Uses multiple browser tabs in parallel (controlled by semaphore)
        to maximize throughput and achieve 100+ IG results in under 1 minute.

        Args:
            keywords: List of search keywords.

        Returns:
            List of result dictionaries ready for export.
        """
        self.results = []
        self.stats = SearchStats()
        self._seen_urls = set()
        self._seen_ig = set()
        self.stats.start_time = time.time()

        console.print()
        show_info(f"Memulai pencarian dengan {len(keywords)} keyword...")
        show_info(f"Mode: {self.max_concurrent} tab paralel untuk kecepatan maksimal")
        console.print()

        try:
            # Launch browser
            with console.status(
                f"[{COLORS['pink']}]🚀 Meluncurkan browser...",
                spinner="dots",
            ):
                await self._launch_browser()

            show_success("Browser berhasil diluncurkan")
            console.print()

            # Create semaphore for concurrent tab control
            semaphore = asyncio.Semaphore(self.max_concurrent)

            # Search all keywords concurrently with progress
            with Progress(
                SpinnerColumn(style=COLORS["pink"]),
                TextColumn(f"[{COLORS['white']}]🔍 Mencari"),
                BarColumn(
                    complete_style=COLORS["purple"],
                    finished_style=COLORS["success"],
                ),
                MofNCompleteColumn(),
                TextColumn(f"[{COLORS['light_gray']}]•"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task_id = progress.add_task("searching", total=len(keywords))

                # Launch all keyword searches concurrently
                tasks = [
                    self._search_single_keyword(kw, semaphore, progress, task_id)
                    for kw in keywords
                ]

                # Gather results from all concurrent searches
                all_results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in all_results:
                    if isinstance(result, list):
                        self.results.extend(result)
                    elif isinstance(result, Exception):
                        logger.error(f"Task exception: {result}")

        except Exception as e:
            logger.error(f"Search pipeline error: {e}")
            show_error(f"Error: {str(e)}")

        finally:
            # Close browser
            with console.status(
                f"[{COLORS['pink']}]Menutup browser...",
                spinner="dots",
            ):
                await self._close_browser()

            self.stats.end_time = time.time()

        # Summary
        console.print()
        show_success(
            f"Pencarian selesai! "
            f"Ditemukan {len(self.results)} posting dari "
            f"{self.stats.keywords_processed} keyword"
        )
        show_info(
            f"🎯 {self.stats.ig_found} Instagram ditemukan "
            f"dalam {self.stats.duration:.1f} detik"
        )

        if self.stats.errors:
            show_warning(f"{len(self.stats.errors)} error terjadi selama pencarian")

        logger.info(
            f"Search complete: {len(self.results)} results, "
            f"{self.stats.keywords_processed} keywords, "
            f"{self.stats.posts_checked} posts checked, "
            f"{self.stats.duration:.1f}s elapsed"
        )

        return [post.to_dict() for post in self.results]
