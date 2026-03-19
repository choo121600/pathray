"""Tests for Playwright page crawler (Issue #7)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pathray.crawler.page_crawler import crawl_page


def _make_mock_element(href: str) -> AsyncMock:
    el = AsyncMock()
    el.get_attribute = AsyncMock(return_value=href)
    return el


def _make_mock_browser(
    *,
    status: int = 200,
    title: str = "Test Page",
    hrefs: list[str] | None = None,
    raise_timeout: bool = False,
    raise_error: Exception | None = None,
) -> AsyncMock:
    if hrefs is None:
        hrefs = []

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
    elements = [_make_mock_element(h) for h in hrefs]
    page.query_selector_all = AsyncMock(return_value=elements)
    page.close = AsyncMock()

    return browser


@pytest.mark.asyncio
async def test_crawl_page_extracts_links():
    browser = _make_mock_browser(
        hrefs=["https://example.com/about", "/contact"],
    )
    result = await crawl_page(browser, "https://example.com")
    assert result.status_code == 200
    assert "https://example.com/about" in result.links
    assert "https://example.com/contact" in result.links


@pytest.mark.asyncio
async def test_crawl_page_extracts_title():
    browser = _make_mock_browser(title="My Site")
    result = await crawl_page(browser, "https://example.com")
    assert result.title == "My Site"


@pytest.mark.asyncio
async def test_crawl_page_status_code():
    browser = _make_mock_browser(status=404)
    result = await crawl_page(
        browser, "https://example.com/missing",
    )
    assert result.status_code == 404
    assert result.error is None


@pytest.mark.asyncio
async def test_crawl_page_timeout():
    browser = _make_mock_browser(raise_timeout=True)
    result = await crawl_page(
        browser, "https://example.com/slow",
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
    )
    assert result.status_code == 0
    assert "Network down" in result.error


@pytest.mark.asyncio
async def test_crawl_page_filters_non_http():
    browser = _make_mock_browser(
        hrefs=[
            "mailto:test@example.com",
            "javascript:void(0)",
            "https://example.com/ok",
        ],
    )
    result = await crawl_page(browser, "https://example.com")
    assert len(result.links) == 1
    assert result.links[0] == "https://example.com/ok"
