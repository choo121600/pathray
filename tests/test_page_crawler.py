"""Tests for Playwright page crawler (Issue #7)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pathray.crawler.page_crawler import crawl_page


def _make_mock_browser(
    *,
    status: int = 200,
    title: str = "Test Page",
    evaluate_return: list[str] | None = None,
    raise_timeout: bool = False,
    raise_error: Exception | None = None,
) -> AsyncMock:
    if evaluate_return is None:
        evaluate_return = []

    browser = AsyncMock()
    page = AsyncMock()
    browser.new_page = AsyncMock(return_value=page)

    if raise_timeout:
        from playwright.async_api import (
            TimeoutError as PlaywrightTimeout,
        )

        page.goto = AsyncMock(
            side_effect=PlaywrightTimeout("timeout"),
        )
    elif raise_error:
        page.goto = AsyncMock(side_effect=raise_error)
    else:
        response = MagicMock()
        response.status = status
        page.goto = AsyncMock(return_value=response)

    page.title = AsyncMock(return_value=title)
    page.evaluate = AsyncMock(return_value=evaluate_return)
    page.close = AsyncMock()

    return browser


@pytest.mark.asyncio
async def test_crawl_page_extracts_links():
    browser = _make_mock_browser(
        evaluate_return=["https://example.com/about", "/contact"],
    )
    result = await crawl_page(
        browser, "https://example.com", respect_robots=False,
    )
    assert result.status_code == 200
    assert "https://example.com/about" in result.links
    assert "https://example.com/contact" in result.links


@pytest.mark.asyncio
async def test_crawl_page_extracts_title():
    browser = _make_mock_browser(title="My Site")
    result = await crawl_page(
        browser, "https://example.com", respect_robots=False,
    )
    assert result.title == "My Site"


@pytest.mark.asyncio
async def test_crawl_page_status_code():
    browser = _make_mock_browser(status=404)
    result = await crawl_page(
        browser, "https://example.com/missing",
        respect_robots=False,
    )
    assert result.status_code == 404
    assert result.error is None


@pytest.mark.asyncio
async def test_crawl_page_timeout():
    browser = _make_mock_browser(raise_timeout=True)
    result = await crawl_page(
        browser, "https://example.com/slow",
        respect_robots=False,
    )
    assert result.status_code == 0
    assert result.error == "Timeout"
    assert result.links == []


@pytest.mark.asyncio
async def test_crawl_page_network_error():
    browser = _make_mock_browser(
        raise_error=ConnectionError("Network down"),
    )
    result = await crawl_page(
        browser, "https://example.com/broken",
        respect_robots=False,
    )
    assert result.status_code == 0
    assert "Network down" in result.error


@pytest.mark.asyncio
async def test_crawl_page_filters_non_http():
    browser = _make_mock_browser(
        evaluate_return=[
            "mailto:test@example.com",
            "javascript:void(0)",
            "https://example.com/ok",
        ],
    )
    result = await crawl_page(
        browser, "https://example.com", respect_robots=False,
    )
    assert len(result.links) == 1
    assert result.links[0] == "https://example.com/ok"


@pytest.mark.asyncio
async def test_crawl_page_robots_blocked(monkeypatch):
    """Page blocked by robots.txt returns error."""
    async def mock_check_robots(url):
        return False

    monkeypatch.setattr(
        "pathray.crawler.page_crawler._check_robots",
        mock_check_robots,
    )
    browser = _make_mock_browser()
    result = await crawl_page(
        browser, "https://example.com/secret",
        respect_robots=True,
    )
    assert result.status_code == 0
    assert result.error == "Blocked by robots.txt"
    assert result.links == []


@pytest.mark.asyncio
async def test_crawl_page_robots_disabled():
    """With respect_robots=False, robots.txt is not checked."""
    browser = _make_mock_browser()
    result = await crawl_page(
        browser, "https://example.com",
        respect_robots=False,
    )
    assert result.status_code == 200


@pytest.mark.asyncio
async def test_crawl_page_deduplicates_links():
    """Duplicate URLs from evaluate should be deduplicated."""
    browser = _make_mock_browser(
        evaluate_return=[
            "https://example.com/page",
            "https://example.com/page",
            "/page",
        ],
    )
    result = await crawl_page(
        browser, "https://example.com", respect_robots=False,
    )
    assert result.links.count("https://example.com/page") == 1


@pytest.mark.asyncio
async def test_crawl_page_resolves_relative_urls():
    """Relative URLs from iframe/onclick are resolved to absolute."""
    browser = _make_mock_browser(
        evaluate_return=[
            "subdir/page.aspx",
            "../other.html",
        ],
    )
    result = await crawl_page(
        browser, "https://example.com/app/index.html",
        respect_robots=False,
    )
    assert "https://example.com/app/subdir/page.aspx" in result.links
    assert "https://example.com/other.html" in result.links
