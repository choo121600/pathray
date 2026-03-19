"""Tests for table extractor."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pathray.extractor.table_extractor import extract_tables


def _make_cell(text: str, tag: str = "td", colspan: str | None = None, rowspan: str | None = None) -> AsyncMock:
    cell = AsyncMock()
    cell.inner_text = AsyncMock(return_value=text)
    cell.tag_name = tag

    async def get_attribute(name: str) -> str | None:
        if name == "colspan":
            return colspan
        if name == "rowspan":
            return rowspan
        return None

    cell.get_attribute = get_attribute
    return cell


def _make_row(cells: list[AsyncMock]) -> AsyncMock:
    row = AsyncMock()
    row.query_selector_all = AsyncMock(return_value=cells)
    return row


def _make_table(
    rows: list[AsyncMock],
    caption_text: str | None = None,
) -> AsyncMock:
    table = AsyncMock()
    table.query_selector_all = AsyncMock(return_value=rows)

    if caption_text is not None:
        caption_el = AsyncMock()
        caption_el.inner_text = AsyncMock(return_value=caption_text)
        table.query_selector = AsyncMock(return_value=caption_el)
    else:
        table.query_selector = AsyncMock(return_value=None)

    return table


def _make_page(tables: list[AsyncMock]) -> AsyncMock:
    page = AsyncMock()
    page.query_selector_all = AsyncMock(return_value=tables)
    return page


# --- Tests ---


@pytest.mark.asyncio
async def test_table_with_th_headers():
    header_row = _make_row([
        _make_cell("Name", tag="th"),
        _make_cell("Age", tag="th"),
    ])
    data_row = _make_row([
        _make_cell("Alice"),
        _make_cell("30"),
    ])
    table = _make_table([header_row, data_row])
    page = _make_page([table])

    result = await extract_tables(page)

    assert len(result) == 1
    assert result[0].headers == ["Name", "Age"]
    assert result[0].rows == [["Alice", "30"]]
    assert result[0].caption is None


@pytest.mark.asyncio
async def test_table_without_th_uses_first_row_as_headers():
    first_row = _make_row([
        _make_cell("Col1"),
        _make_cell("Col2"),
    ])
    data_row = _make_row([
        _make_cell("val1"),
        _make_cell("val2"),
    ])

    # first_row returns no th elements (empty list when queried for th)
    async def first_row_selector(selector: str) -> list:
        if selector == "th":
            return []
        return [_make_cell("Col1"), _make_cell("Col2")]

    first_row.query_selector_all = first_row_selector

    table = _make_table([first_row, data_row])
    page = _make_page([table])

    result = await extract_tables(page)

    assert result[0].headers == ["Col1", "Col2"]
    assert result[0].rows == [["val1", "val2"]]


@pytest.mark.asyncio
async def test_empty_table():
    table = _make_table([])
    page = _make_page([table])

    result = await extract_tables(page)

    assert len(result) == 1
    assert result[0].headers == []
    assert result[0].rows == []


@pytest.mark.asyncio
async def test_no_tables():
    page = _make_page([])

    result = await extract_tables(page)

    assert result == []


@pytest.mark.asyncio
async def test_table_with_caption():
    header_row = _make_row([_make_cell("Item", tag="th")])
    table = _make_table([header_row], caption_text="Sales Report")
    page = _make_page([table])

    result = await extract_tables(page)

    assert result[0].caption == "Sales Report"


@pytest.mark.asyncio
async def test_empty_cells_become_empty_string():
    header_row = _make_row([
        _make_cell("A", tag="th"),
        _make_cell("B", tag="th"),
    ])
    data_row = _make_row([
        _make_cell(""),
        _make_cell("  "),
    ])
    table = _make_table([header_row, data_row])
    page = _make_page([table])

    result = await extract_tables(page)

    assert result[0].rows == [["", ""]]


@pytest.mark.asyncio
async def test_multiple_tables():
    table1 = _make_table([
        _make_row([_make_cell("H1", tag="th")]),
        _make_row([_make_cell("v1")]),
    ])
    table2 = _make_table([
        _make_row([_make_cell("H2", tag="th")]),
        _make_row([_make_cell("v2")]),
    ])
    page = _make_page([table1, table2])

    result = await extract_tables(page)

    assert len(result) == 2
    assert result[0].headers == ["H1"]
    assert result[1].headers == ["H2"]


@pytest.mark.asyncio
async def test_colspan_repeats_value():
    header_row = _make_row([
        _make_cell("A", tag="th"),
        _make_cell("B", tag="th"),
        _make_cell("C", tag="th"),
    ])
    # Cell with colspan=2 should fill 2 columns
    data_row = _make_row([
        _make_cell("merged", colspan="2"),
        _make_cell("single"),
    ])
    table = _make_table([header_row, data_row])
    page = _make_page([table])

    result = await extract_tables(page)

    assert result[0].rows == [["merged", "merged", "single"]]
