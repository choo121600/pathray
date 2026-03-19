"""Playwright-based single page crawler."""

from dataclasses import dataclass
from urllib.parse import urljoin

from playwright.async_api import Browser
from playwright.async_api import TimeoutError as PlaywrightTimeout


@dataclass
class PageResult:
    """Result of crawling a single page."""

    url: str
    title: str | None
    status_code: int
    links: list[str]
    error: str | None = None


async def crawl_page(browser: Browser, url: str, timeout: int = 30000) -> PageResult:
    """Visit a single page and extract links and metadata.

    Args:
        browser: Playwright Browser instance.
        url: URL to visit.
        timeout: Navigation timeout in milliseconds (default 30s).

    Returns:
        PageResult with extracted data.
    """
    page = await browser.new_page()
    try:
        response = await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        status_code = response.status if response else 0

        title = await page.title()

        elements = await page.query_selector_all("a[href]")
        raw_hrefs = []
        for el in elements:
            href = await el.get_attribute("href")
            if href:
                raw_hrefs.append(href)

        links = []
        for href in raw_hrefs:
            absolute = urljoin(url, href)
            if absolute.startswith(("http://", "https://")):
                links.append(absolute)

        return PageResult(
            url=url,
            title=title or None,
            status_code=status_code,
            links=links,
        )
    except PlaywrightTimeout:
        return PageResult(
            url=url,
            title=None,
            status_code=0,
            links=[],
            error="Timeout",
        )
    except Exception as e:
        return PageResult(
            url=url,
            title=None,
            status_code=0,
            links=[],
            error=str(e),
        )
    finally:
        await page.close()
