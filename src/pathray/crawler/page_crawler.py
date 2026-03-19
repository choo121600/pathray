"""Playwright-based single page crawler."""

import asyncio
from collections import OrderedDict
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from playwright.async_api import Browser
from playwright.async_api import TimeoutError as PlaywrightTimeout

_MAX_ROBOT_CACHE = 100
_robot_cache: OrderedDict[str, RobotFileParser] = OrderedDict()


async def _check_robots(url: str) -> bool:
    """Check if url is allowed by robots.txt. Returns True if allowed."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    if robots_url not in _robot_cache:
        rp = RobotFileParser()
        rp.set_url(robots_url)
        try:
            await asyncio.to_thread(rp.read)
        except Exception:
            rp.allow_all = True
        _robot_cache[robots_url] = rp
        if len(_robot_cache) > _MAX_ROBOT_CACHE:
            _robot_cache.popitem(last=False)

    return _robot_cache[robots_url].can_fetch("*", url)


@dataclass
class PageResult:
    """Result of crawling a single page."""

    url: str
    title: str | None
    status_code: int
    links: list[str]
    error: str | None = None


async def crawl_page(
    browser: Browser,
    url: str,
    timeout: int = 30000,
    *,
    respect_robots: bool = True,
) -> PageResult:
    """Visit a single page and extract links and metadata.

    Args:
        browser: Playwright Browser instance.
        url: URL to visit.
        timeout: Navigation timeout in milliseconds (default 30s).
        respect_robots: Check robots.txt before crawling.

    Returns:
        PageResult with extracted data.
    """
    if respect_robots and not await _check_robots(url):
        return PageResult(
            url=url,
            title=None,
            status_code=0,
            links=[],
            error="Blocked by robots.txt",
        )

    page = await browser.new_page()
    try:
        response = await page.goto(
            url, timeout=timeout, wait_until="domcontentloaded",
        )
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
