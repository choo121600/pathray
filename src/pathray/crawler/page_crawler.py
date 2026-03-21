"""Playwright-based single page crawler."""

import asyncio
from collections import OrderedDict
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

from playwright.async_api import Browser, Page
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


_EXTRACT_JS = """() => {
    const urls = new Set();

    // 1. Standard <a href>
    for (const a of document.querySelectorAll('a[href]')) {
        const href = a.getAttribute('href');
        if (href) urls.add(href);
    }

    // 2. iframe/frame src
    for (const el of document.querySelectorAll('iframe[src], frame[src]')) {
        const src = el.getAttribute('src');
        if (src) urls.add(src);
    }

    // 3. onclick handlers — extract URL-like strings
    for (const el of document.querySelectorAll('[onclick]')) {
        const onclick = el.getAttribute('onclick');
        if (!onclick) continue;
        const matches = onclick.matchAll(/['"]([^'"]*\\.(?:aspx|html|htm|php|jsp|do|action|cgi)[^'"]*)['"]/gi);
        for (const m of matches) urls.add(m[1]);
        const locMatch = onclick.match(/(?:window\\.)?location(?:\\.href)?\\s*=\\s*['"]([^'"]+)['"]/);
        if (locMatch) urls.add(locMatch[1]);
        const openMatch = onclick.match(/window\\.open\\(\\s*['"]([^'"]+)['"]/);
        if (openMatch) urls.add(openMatch[1]);
    }

    // 4. javascript: href — extract embedded URLs
    for (const a of document.querySelectorAll('a[href^="javascript:"]')) {
        const href = a.getAttribute('href');
        if (!href) continue;
        const matches = href.matchAll(/['"]([^'"]*\\.(?:aspx|html|htm|php|jsp|do|action|cgi)[^'"]*)['"]/gi);
        for (const m of matches) urls.add(m[1]);
    }

    // 5. data-href, data-url, data-src attributes
    for (const el of document.querySelectorAll('[data-href], [data-url], [data-src]')) {
        for (const attr of ['data-href', 'data-url', 'data-src']) {
            const val = el.getAttribute(attr);
            if (val && val.trim()) urls.add(val.trim());
        }
    }

    // 6. meta refresh
    const meta = document.querySelector('meta[http-equiv="refresh"]');
    if (meta) {
        const content = meta.getAttribute('content') || '';
        const urlMatch = content.match(/url=([^;\\s]+)/i);
        if (urlMatch) urls.add(urlMatch[1]);
    }

    return [...urls];
}"""


async def _extract_links(page: Page, base_url: str) -> list[str]:
    """Extract links from the main page and all child frames.

    Sources: a[href], iframe/frame[src], onclick handlers, javascript: hrefs,
    data-href/data-url/data-src attributes, meta refresh.
    """
    # Run extraction on main frame
    raw_urls: list[str] = await page.evaluate(_EXTRACT_JS)

    # Also extract from all child frames (e.g. iframe content)
    for frame in page.frames:
        if frame == page.main_frame:
            continue
        try:
            frame_urls: list[str] = await frame.evaluate(_EXTRACT_JS)
            raw_urls.extend(frame_urls)
        except Exception:
            continue

    links: list[str] = []
    seen: set[str] = set()
    for raw in raw_urls:
        absolute = urljoin(base_url, raw)
        if absolute.startswith(("http://", "https://")) and absolute not in seen:
            seen.add(absolute)
            links.append(absolute)

    return links


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
        links = await _extract_links(page, url)

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
