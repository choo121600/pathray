"""Tests for text content extractor."""

from unittest.mock import AsyncMock

import pytest

from pathray.extractor.text_extractor import extract_text


def _make_el(tag: str, inner_text: str, li_texts: list[str] | None = None) -> AsyncMock:
    el = AsyncMock()
    el.evaluate = AsyncMock(return_value=tag)
    el.inner_text = AsyncMock(return_value=inner_text)
    if li_texts is not None:
        li_els = []
        for t in li_texts:
            li = AsyncMock()
            li.inner_text = AsyncMock(return_value=t)
            li_els.append(li)
        el.query_selector_all = AsyncMock(return_value=li_els)
    return el


def _make_page(elements: list[AsyncMock]) -> AsyncMock:
    page = AsyncMock()
    page.query_selector_all = AsyncMock(return_value=elements)
    return page


@pytest.mark.asyncio
async def test_extract_headings_levels():
    elements = [
        _make_el("h1", "Title"),
        _make_el("h2", "Subtitle"),
        _make_el("h3", "Section"),
        _make_el("h4", "Subsection"),
        _make_el("h5", "Minor"),
        _make_el("h6", "Tiny"),
    ]
    page = _make_page(elements)
    results = await extract_text(page)

    assert len(results) == 6
    assert results[0].tag == "h1" and results[0].level == 1
    assert results[1].tag == "h2" and results[1].level == 2
    assert results[2].tag == "h3" and results[2].level == 3
    assert results[3].tag == "h4" and results[3].level == 4
    assert results[4].tag == "h5" and results[4].level == 5
    assert results[5].tag == "h6" and results[5].level == 6


@pytest.mark.asyncio
async def test_extract_headings_text():
    elements = [_make_el("h1", "  Hello World  ")]
    page = _make_page(elements)
    results = await extract_text(page)

    assert results[0].text == "Hello World"


@pytest.mark.asyncio
async def test_extract_paragraph():
    elements = [_make_el("p", "Some paragraph text.")]
    page = _make_page(elements)
    results = await extract_text(page)

    assert len(results) == 1
    assert results[0].tag == "p"
    assert results[0].text == "Some paragraph text."
    assert results[0].level is None


@pytest.mark.asyncio
async def test_extract_ul_list():
    el = _make_el("ul", "", li_texts=["Item 1", "Item 2", "Item 3"])
    page = _make_page([el])
    results = await extract_text(page)

    assert len(results) == 1
    assert results[0].tag == "ul"
    assert results[0].text == "Item 1\nItem 2\nItem 3"
    assert results[0].level is None


@pytest.mark.asyncio
async def test_extract_ol_list():
    el = _make_el("ol", "", li_texts=["First", "Second"])
    page = _make_page([el])
    results = await extract_text(page)

    assert results[0].tag == "ol"
    assert results[0].text == "First\nSecond"


@pytest.mark.asyncio
async def test_document_order_preserved():
    elements = [
        _make_el("h1", "Title"),
        _make_el("p", "Intro"),
        _make_el("h2", "Section"),
        _make_el("p", "Body"),
    ]
    page = _make_page(elements)
    results = await extract_text(page)

    assert [r.tag for r in results] == ["h1", "p", "h2", "p"]


@pytest.mark.asyncio
async def test_empty_elements_skipped():
    elements = [
        _make_el("h1", "  "),  # whitespace only
        _make_el("p", ""),     # empty
        _make_el("p", "Real content"),
    ]
    page = _make_page(elements)
    results = await extract_text(page)

    assert len(results) == 1
    assert results[0].text == "Real content"


@pytest.mark.asyncio
async def test_empty_list_items_skipped():
    el = _make_el("ul", "", li_texts=["Item 1", "  ", "Item 3"])
    page = _make_page([el])
    results = await extract_text(page)

    assert results[0].text == "Item 1\nItem 3"


@pytest.mark.asyncio
async def test_no_elements_returns_empty():
    page = _make_page([])
    results = await extract_text(page)

    assert results == []
