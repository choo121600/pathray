"""Table extractor for HTML pages."""

from playwright.async_api import ElementHandle, Page

from pathray.models.page_data import TableData


async def _cell_text(cell: ElementHandle) -> str:
    return (await cell.inner_text()).strip()


async def _parse_rows(
    rows: list[ElementHandle],
) -> list[list[str]]:
    """Parse table rows into lists of strings, handling colspan/rowspan."""
    result: list[list[str]] = []
    # rowspan_carry: col_index -> (value, remaining_rows)
    rowspan_carry: dict[int, tuple[str, int]] = {}

    for row in rows:
        cells = await row.query_selector_all("th,td")
        parsed: list[str] = []
        col = 0
        cell_idx = 0

        while cell_idx < len(cells) or any(
            c >= col for c in rowspan_carry if c >= col
        ):
            # Drain pending rowspan slots at this column position
            if col in rowspan_carry:
                value, remaining = rowspan_carry[col]
                parsed.append(value)
                if remaining - 1 > 0:
                    rowspan_carry[col] = (value, remaining - 1)
                else:
                    del rowspan_carry[col]
                col += 1
                continue

            if cell_idx >= len(cells):
                break

            cell = cells[cell_idx]
            text = await _cell_text(cell)

            colspan_attr = await cell.get_attribute("colspan")
            colspan = (
                int(colspan_attr)
                if colspan_attr and colspan_attr.isdigit()
                else 1
            )

            rowspan_attr = await cell.get_attribute("rowspan")
            rowspan = (
                int(rowspan_attr)
                if rowspan_attr and rowspan_attr.isdigit()
                else 1
            )

            for i in range(colspan):
                parsed.append(text)
                if rowspan > 1:
                    rowspan_carry[col + i] = (text, rowspan - 1)

            col += colspan
            cell_idx += 1

        result.append(parsed)

    return result


async def extract_tables(page: Page) -> list[TableData]:
    """Extract all tables from the page."""
    tables = await page.query_selector_all("table")
    if not tables:
        return []

    result: list[TableData] = []

    for table in tables:
        # Caption
        caption: str | None = None
        caption_el = await table.query_selector("caption")
        if caption_el:
            caption = (await caption_el.inner_text()).strip() or None

        # Collect all rows
        all_rows = await table.query_selector_all("tr")
        if not all_rows:
            result.append(TableData(headers=[], rows=[], caption=caption))
            continue

        # Detect headers: th elements in first row, or first row itself
        first_row = all_rows[0]
        th_els = await first_row.query_selector_all("th")

        if th_els:
            headers = [await _cell_text(th) for th in th_els]
            data_rows_els = all_rows[1:]
        else:
            # No th elements: use first row as headers
            td_els = await first_row.query_selector_all("td")
            headers = [await _cell_text(td) for td in td_els]
            data_rows_els = all_rows[1:]

        rows = await _parse_rows(data_rows_els)

        result.append(TableData(headers=headers, rows=rows, caption=caption))

    return result
