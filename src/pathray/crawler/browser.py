"""Browser management utilities using Playwright."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from playwright.async_api import Browser, async_playwright


@asynccontextmanager
async def launch_browser(headless: bool = True) -> AsyncIterator[Browser]:
    """Launch a Playwright Chromium browser instance.

    Usage:
        async with launch_browser() as browser:
            page = await browser.new_page()
            await page.goto("https://example.com")
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        try:
            yield browser
        finally:
            await browser.close()
