"""Tests for crawler engine with concurrency control (Issue #8)."""

from unittest.mock import AsyncMock

import pytest

from pathray.crawler.crawler_engine import CrawlerEngine
from pathray.crawler.page_crawler import PageResult
from pathray.crawler.queue import normalize_url


def _make_page_results(
    pages: dict[str, list[str]],
) -> dict[str, PageResult]:
    """Create PageResult map with normalized keys."""
    results = {}
    for url, links in pages.items():
        key = normalize_url(url)
        results[key] = PageResult(
            url=key,
            title=f"Page {key}",
            status_code=200,
            links=links,
        )
    return results


def _fallback(url: str) -> PageResult:
    return PageResult(
        url=url, title=None, status_code=404, links=[],
    )


@pytest.mark.asyncio
async def test_crawl_single_page(monkeypatch):
    page_map = _make_page_results({
        "https://example.com": [],
    })

    async def mock_crawl_page(browser, url, timeout=30000):
        return page_map.get(url, _fallback(url))

    monkeypatch.setattr(
        "pathray.crawler.crawler_engine.crawl_page",
        mock_crawl_page,
    )

    engine = CrawlerEngine(
        "https://example.com", max_depth=2, concurrency=1,
    )
    browser = AsyncMock()
    entries = await engine.crawl(browser)
    assert len(entries) == 1
    assert str(entries[0].url) == "https://example.com/"


@pytest.mark.asyncio
async def test_crawl_follows_links(monkeypatch):
    page_map = _make_page_results({
        "https://example.com": [
            "https://example.com/about",
        ],
        "https://example.com/about": [],
    })

    async def mock_crawl_page(browser, url, timeout=30000):
        return page_map.get(url, _fallback(url))

    monkeypatch.setattr(
        "pathray.crawler.crawler_engine.crawl_page",
        mock_crawl_page,
    )

    engine = CrawlerEngine(
        "https://example.com", max_depth=5, concurrency=1,
    )
    browser = AsyncMock()
    entries = await engine.crawl(browser)
    assert len(entries) == 2


@pytest.mark.asyncio
async def test_crawl_respects_max_depth(monkeypatch):
    page_map = _make_page_results({
        "https://example.com": ["https://example.com/a"],
        "https://example.com/a": ["https://example.com/b"],
        "https://example.com/b": ["https://example.com/c"],
        "https://example.com/c": [],
    })

    async def mock_crawl_page(browser, url, timeout=30000):
        return page_map.get(url, _fallback(url))

    monkeypatch.setattr(
        "pathray.crawler.crawler_engine.crawl_page",
        mock_crawl_page,
    )

    engine = CrawlerEngine(
        "https://example.com", max_depth=1, concurrency=1,
    )
    browser = AsyncMock()
    entries = await engine.crawl(browser)
    # depth 0: example.com, depth 1: /a
    assert len(entries) == 2


@pytest.mark.asyncio
async def test_crawl_no_duplicate_visits(monkeypatch):
    page_map = _make_page_results({
        "https://example.com": [
            "https://example.com/a",
            "https://example.com/a",
        ],
        "https://example.com/a": ["https://example.com"],
    })

    async def mock_crawl_page(browser, url, timeout=30000):
        return page_map.get(url, _fallback(url))

    monkeypatch.setattr(
        "pathray.crawler.crawler_engine.crawl_page",
        mock_crawl_page,
    )

    engine = CrawlerEngine(
        "https://example.com", max_depth=5, concurrency=1,
    )
    browser = AsyncMock()
    entries = await engine.crawl(browser)
    assert len(entries) == 2


@pytest.mark.asyncio
async def test_crawl_filters_external_links(monkeypatch):
    page_map = _make_page_results({
        "https://example.com": [
            "https://external.com/page",
            "https://example.com/internal",
        ],
        "https://example.com/internal": [],
    })

    async def mock_crawl_page(browser, url, timeout=30000):
        return page_map.get(url, _fallback(url))

    monkeypatch.setattr(
        "pathray.crawler.crawler_engine.crawl_page",
        mock_crawl_page,
    )

    engine = CrawlerEngine(
        "https://example.com", max_depth=5, concurrency=1,
    )
    browser = AsyncMock()
    entries = await engine.crawl(browser)
    urls = [str(e.url) for e in entries]
    assert not any("external.com" in u for u in urls)
    assert len(entries) == 2
