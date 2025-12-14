"""
Headless scraper using Playwright for dynamic content and anti-bot bypass
"""
import logging
import time
import random
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, Error as PlaywrightError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class HeadlessScraper(BaseScraper):
    """Scraper that uses Playwright for headless browsing"""

    def __init__(self, headless: bool = True, **kwargs):
        """
        Initialize headless scraper

        Args:
            headless: Whether to run browser in headless mode
            **kwargs: Arguments for BaseScraper
        """
        super().__init__(**kwargs)
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.context = None

    def _init_browser(self):
        """Initialize Playwright browser"""
        if not self.playwright:
            self.playwright = sync_playwright().start()

        if not self.browser:
            # Launch browser with options to evade detection
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-infobars',
                    '--window-position=0,0',
                    '--ignore-certifcate-errors',
                    '--ignore-certifcate-errors-spki-list',
                    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ]
            )

    def _get_context(self) -> BrowserContext:
        """Get or create browser context with stealth settings"""
        if not self.browser:
            self._init_browser()

        if not self.context:
            self.context = self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent=self.get_user_agent(),
                java_script_enabled=True,
                ignore_https_errors=True
            )

            # Add stealth scripts
            self.context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        return self.context

    def get_page(self) -> Page:
        """Get a new page in the current context"""
        context = self._get_context()
        page = context.new_page()
        return page

    def close(self):
        """Close browser and cleanup"""
        if self.context:
            self.context.close()
            self.context = None
        if self.browser:
            self.browser.close()
            self.browser = None
        if self.playwright:
            self.playwright.stop()
            self.playwright = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((PlaywrightError, TimeoutError)),
        reraise=False # Don't raise to caller, just return None on final failure (handled inside try/except if not reraised?)
    )
    def fetch_page_content(self, url: str, wait_for_selector: Optional[str] = None) -> Optional[str]:
        """
        Fetch page content using Playwright with retries

        Args:
            url: URL to fetch
            wait_for_selector: Optional CSS selector to wait for

        Returns:
            HTML content or None if failed
        """
        if not self._can_fetch(url):
            logger.warning(f"Blocked by robots.txt: {url}")
            return None

        self._wait_for_rate_limit(url)

        page = None
        try:
            page = self.get_page()
            
            # Navigate with smart waiting
            logger.info(f"Navigating to {url}")
            response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
            
            if not response:
                logger.warning(f"No response from {url}")
                return None
                
            if response.status >= 400:
                logger.warning(f"HTTP {response.status} from {url}")
                # Don't return None yet, sometimes error pages have useful info or it's a soft 404
            
            # Handle cookie banners or popups if needed (generic attempt)
            try:
                # Common cookie accept buttons
                page.click("text=Accept All", timeout=2000)
            except:
                pass

            # Wait for specific content
            if wait_for_selector:
                try:
                    page.wait_for_selector(wait_for_selector, timeout=10000)
                except Exception as e:
                    logger.warning(f"Timeout waiting for selector {wait_for_selector}: {e}")

            # Scroll to trigger lazy loading
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(2) # Wait for lazy load

            content = page.content()
            return content

        except Exception as e:
            logger.error(f"Error fetching {url} with Playwright: {e}")
            raise # Re-raise to trigger retry
        finally:
            if page:
                page.close()

    def __del__(self):
        """Cleanup on destruction"""
        self.close()
