"""Text content extractor for HTML pages."""

from playwright.async_api import Page

from pathray.models.page_data import TextContent


async def extract_text(page: Page) -> list[TextContent]:
    """Extract text content (headings, paragraphs, lists) from the page."""
    results: list[TextContent] = []

    elements = await page.query_selector_all("h1,h2,h3,h4,h5,h6,p,ul,ol")

    for el in elements:
        tag = await el.evaluate("el => el.tagName.toLowerCase()")

        if tag in ("ul", "ol"):
            items = await el.query_selector_all("li")
            texts = []
            for li in items:
                t = (await li.inner_text()).strip()
                if t:
                    texts.append(t)
            text = "\n".join(texts)
            level = None
        else:
            text = (await el.inner_text()).strip()
            level = int(tag[1]) if tag[0] == "h" else None

        if text:
            results.append(TextContent(tag=tag, text=text, level=level))

    return results
