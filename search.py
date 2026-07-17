"""
ThreadScout - Search Module
=============================
Playwright-based Threads search engine with async browsing, scrolling,
and post extraction.
"""

import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime
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
    date_scraped: str = ""

    def to_dict(self) -> dict:
        """Convert to a dictionary matching export columns."""
        return {
            "Threads": self.threads_username,
            "Instagram": self.instagram,
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

    Navigates to Threads search, scrolls to load posts, and extracts
    post content, usernames, and Instagram references.
    """

    def __init__(
        self,
        headless: bool = BROWSER_HEADLESS,
        timeout: int = BROWSER_TIMEOUT,
        scroll_count: int = SCROLL_COUNT,
    ) -> None:
        self.headless = headless
        self.timeout = timeout
        self.scroll_count = scroll_count

        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

        self.results: list[PostData] = []
        self.stats = SearchStats()
        self._seen_urls: set[str] = set()

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

        self._page = await self._context.new_page()
        self._page.set_default_timeout(self.timeout)

        logger.info("Browser launched successfully")

    async def _close_browser(self) -> None:
        """Safely close the browser and all resources."""
        try:
            if self._page:
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            logger.info("Browser closed")
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")

    async def _scroll_page(self) -> None:
        """Scroll the page to load more posts."""
        if not self._page:
            return

        for i in range(self.scroll_count):
            await self._page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(SCROLL_DELAY + random.uniform(0.5, 1.5))
            logger.debug(f"Scroll {i + 1}/{self.scroll_count}")

    async def _check_for_login_wall(self) -> bool:
        """
        Check if Threads is showing a login requirement.

        Returns:
            True if login wall is detected, False otherwise.
        """
        if not self._page:
            return False

        try:
            # Check for common login wall indicators
            login_indicators = [
                'text="Log in"',
                'text="Sign up"',
                '[data-testid="login-button"]',
                'text="Log in to see more"',
            ]
            for selector in login_indicators:
                element = await self._page.query_selector(selector)
                if element:
                    logger.warning("Login wall detected")
                    return True
            return False
        except Exception:
            return False

    async def _check_for_captcha(self) -> bool:
        """
        Check if a CAPTCHA challenge is present.

        Returns:
            True if CAPTCHA is detected, False otherwise.
        """
        if not self._page:
            return False

        try:
            captcha_indicators = [
                "iframe[src*='captcha']",
                "iframe[src*='recaptcha']",
                "[class*='captcha']",
                "iframe[src*='challenge']",
            ]
            for selector in captcha_indicators:
                element = await self._page.query_selector(selector)
                if element:
                    logger.warning("CAPTCHA detected")
                    return True
            return False
        except Exception:
            return False

    async def _extract_posts_from_page(self, keyword: str) -> list[PostData]:
        """
        Extract post data from the current page.

        Args:
            keyword: The keyword used for this search.

        Returns:
            List of extracted PostData objects.
        """
        if not self._page:
            return []

        posts: list[PostData] = []

        try:
            # Wait for content to load
            await self._page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)

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
                elements = await self._page.query_selector_all(selector)
                if elements:
                    post_elements = elements
                    logger.debug(
                        f"Found {len(elements)} elements with selector: {selector}"
                    )
                    break

            if not post_elements:
                # Fallback: try to extract text content from the page
                logger.debug("No post elements found with known selectors")
                return posts

            for element in post_elements:
                try:
                    # Extract text content
                    text_content = await element.inner_text()
                    if not text_content or len(text_content.strip()) < 10:
                        continue

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

                    # Skip if we've already seen this URL
                    if post_url and post_url in self._seen_urls:
                        continue
                    if post_url:
                        self._seen_urls.add(post_url)

                    # Apply content filters
                    filter_result = apply_filters(text_content)
                    if not filter_result.passed:
                        continue

                    self.stats.posts_passed += 1

                    # Extract Instagram references
                    extraction = extract_instagram(text_content)
                    ig_reference = extraction.primary

                    if extraction.found:
                        self.stats.ig_found += 1

                    post = PostData(
                        threads_username=username or "Unknown",
                        post_url=post_url,
                        post_content=text_content.strip()[:500],
                        keyword=keyword,
                        instagram=ig_reference,
                        date_scraped=get_timestamp(),
                    )

                    posts.append(post)
                    logger.debug(
                        f"Extracted post: {username} | IG: {ig_reference}"
                    )

                except Exception as e:
                    logger.debug(f"Error extracting post element: {e}")
                    continue

        except PlaywrightTimeout:
            logger.warning(f"Timeout waiting for page content (keyword: {keyword})")
        except Exception as e:
            logger.error(f"Error extracting posts: {e}")

        return posts

    async def search_keyword(self, keyword: str) -> list[PostData]:
        """
        Search Threads for a specific keyword and extract matching posts.

        Args:
            keyword: The search keyword.

        Returns:
            List of PostData objects found for this keyword.
        """
        if not self._page:
            return []

        encoded_keyword = quote_plus(keyword)
        search_url = f"{THREADS_SEARCH_URL}{encoded_keyword}"

        logger.info(f"Searching keyword: '{keyword}'")

        try:
            # Navigate to search URL
            response = await self._page.goto(
                search_url, wait_until="domcontentloaded", timeout=self.timeout
            )

            if response and response.status >= 400:
                logger.warning(
                    f"HTTP {response.status} for keyword '{keyword}'"
                )
                self.stats.errors.append(
                    f"HTTP {response.status}: {keyword}"
                )
                return []

            # Check for obstacles
            if await self._check_for_captcha():
                show_warning(f"CAPTCHA terdeteksi saat mencari '{keyword}'")
                self.stats.errors.append(f"CAPTCHA: {keyword}")
                return []

            if await self._check_for_login_wall():
                show_warning(
                    f"Login diperlukan untuk melanjutkan pencarian '{keyword}'"
                )
                self.stats.errors.append(f"Login required: {keyword}")
                return []

            # Wait for initial content
            await asyncio.sleep(3)

            # Scroll to load more posts
            await self._scroll_page()

            # Extract posts
            posts = await self._extract_posts_from_page(keyword)
            self.stats.keywords_processed += 1

            logger.info(
                f"Keyword '{keyword}': found {len(posts)} matching posts"
            )
            return posts

        except PlaywrightTimeout:
            error_msg = f"Timeout: {keyword}"
            logger.warning(error_msg)
            self.stats.errors.append(error_msg)
            show_warning(f"Timeout saat mencari '{keyword}'")
            return []

        except ConnectionError:
            error_msg = f"Connection error: {keyword}"
            logger.error(error_msg)
            self.stats.errors.append(error_msg)
            show_error("Koneksi terputus. Periksa internet Anda.")
            return []

        except Exception as e:
            error_msg = f"Error ({keyword}): {str(e)}"
            logger.error(error_msg)
            self.stats.errors.append(error_msg)
            return []

    async def run_search(self, keywords: list[str]) -> list[dict]:
        """
        Execute the full search pipeline across all keywords.

        Args:
            keywords: List of search keywords.

        Returns:
            List of result dictionaries ready for export.
        """
        import time

        self.results = []
        self.stats = SearchStats()
        self._seen_urls = set()
        self.stats.start_time = time.time()

        console.print()
        show_info(f"Memulai pencarian dengan {len(keywords)} keyword...")
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

            # Search each keyword with progress
            with Progress(
                SpinnerColumn(style=COLORS["pink"]),
                TextColumn(f"[{COLORS['white']}]Mencari"),
                BarColumn(
                    complete_style=COLORS["purple"],
                    finished_style=COLORS["success"],
                ),
                MofNCompleteColumn(),
                TextColumn(f"[{COLORS['light_gray']}]•"),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "searching", total=len(keywords)
                )

                for i, keyword in enumerate(keywords):
                    progress.update(
                        task,
                        description=f"[{COLORS['white']}]🔍 [{COLORS['orange']}]{keyword}",
                    )

                    # Search this keyword
                    posts = await self.search_keyword(keyword)
                    self.results.extend(posts)

                    progress.advance(task)

                    # Polite delay between searches
                    if i < len(keywords) - 1:
                        delay = random.uniform(
                            SEARCH_DELAY_MIN, SEARCH_DELAY_MAX
                        )
                        await asyncio.sleep(delay)

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

        if self.stats.errors:
            show_warning(f"{len(self.stats.errors)} error terjadi selama pencarian")

        logger.info(
            f"Search complete: {len(self.results)} results, "
            f"{self.stats.keywords_processed} keywords, "
            f"{self.stats.posts_checked} posts checked"
        )

        return [post.to_dict() for post in self.results]
