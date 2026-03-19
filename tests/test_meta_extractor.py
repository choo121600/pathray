"""Tests for metadata extractor."""

from unittest.mock import AsyncMock

import pytest

from pathray.extractor.meta_extractor import extract_metadata


def _make_meta_el(property_or_name: str, content: str) -> AsyncMock:
    el = AsyncMock()

    async def get_attr(attr: str) -> str | None:
        if attr in ("property", "name"):
            return property_or_name
        if attr == "content":
            return content
        return None

    el.get_attribute = AsyncMock(side_effect=get_attr)
    return el


def _make_link_el(href: str) -> AsyncMock:
    el = AsyncMock()
    el.get_attribute = AsyncMock(return_value=href)
    return el


def _make_img_el(src: str) -> AsyncMock:
    el = AsyncMock()
    el.get_attribute = AsyncMock(return_value=src)
    return el


def _make_page(
    *,
    title: str = "",
    description: str | None = None,
    keywords: str | None = None,
    og_tags: dict[str, str] | None = None,
    canonical: str | None = None,
    images: list[str] | None = None,
) -> AsyncMock:
    page = AsyncMock()
    page.title = AsyncMock(return_value=title)

    # description element
    if description is not None:
        desc_el = AsyncMock()
        desc_el.get_attribute = AsyncMock(return_value=description)
        page.query_selector = AsyncMock(return_value=desc_el)
    else:
        page.query_selector = AsyncMock(return_value=None)

    async def query_selector_side(selector: str):
        if 'description' in selector:
            if description is not None:
                el = AsyncMock()
                el.get_attribute = AsyncMock(return_value=description)
                return el
        if 'keywords' in selector:
            if keywords is not None:
                el = AsyncMock()
                el.get_attribute = AsyncMock(return_value=keywords)
                return el
        if 'canonical' in selector:
            if canonical is not None:
                el = AsyncMock()
                el.get_attribute = AsyncMock(return_value=canonical)
                return el
        return None

    page.query_selector = AsyncMock(side_effect=query_selector_side)

    async def query_selector_all_side(selector: str):
        if 'og:' in selector:
            if og_tags:
                return [_make_meta_el(prop, content) for prop, content in og_tags.items()]
        if 'img' in selector:
            if images:
                return [_make_img_el(src) for src in images]
        return []

    page.query_selector_all = AsyncMock(side_effect=query_selector_all_side)
    return page


@pytest.mark.asyncio
async def test_extract_title():
    page = _make_page(title="My Page Title")
    meta = await extract_metadata(page)

    assert meta.title == "My Page Title"


@pytest.mark.asyncio
async def test_extract_description():
    page = _make_page(description="A great page about things.")
    meta = await extract_metadata(page)

    assert meta.description == "A great page about things."


@pytest.mark.asyncio
async def test_extract_keywords():
    page = _make_page(keywords="python, web, scraping")
    meta = await extract_metadata(page)

    assert meta.keywords == ["python", "web", "scraping"]


@pytest.mark.asyncio
async def test_extract_keywords_strips_whitespace():
    page = _make_page(keywords="  foo ,  bar  , baz")
    meta = await extract_metadata(page)

    assert meta.keywords == ["foo", "bar", "baz"]


@pytest.mark.asyncio
async def test_extract_og_tags():
    page = _make_page(og_tags={
        "og:title": "OG Title",
        "og:description": "OG Desc",
        "og:image": "https://example.com/img.png",
    })
    meta = await extract_metadata(page)

    assert meta.og_tags["og:title"] == "OG Title"
    assert meta.og_tags["og:description"] == "OG Desc"
    assert meta.og_tags["og:image"] == "https://example.com/img.png"


@pytest.mark.asyncio
async def test_extract_canonical_url():
    page = _make_page(canonical="https://example.com/canonical")
    meta = await extract_metadata(page)

    assert meta.canonical_url == "https://example.com/canonical"


@pytest.mark.asyncio
async def test_extract_images():
    page = _make_page(images=[
        "https://example.com/a.png",
        "https://example.com/b.jpg",
    ])
    meta = await extract_metadata(page)

    assert meta.images == [
        "https://example.com/a.png",
        "https://example.com/b.jpg",
    ]


@pytest.mark.asyncio
async def test_no_metadata_defaults():
    page = _make_page()
    meta = await extract_metadata(page)

    assert meta.title is None
    assert meta.description is None
    assert meta.keywords == []
    assert meta.og_tags == {}
    assert meta.canonical_url is None
    assert meta.images == []
