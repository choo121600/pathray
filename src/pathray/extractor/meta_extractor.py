"""Metadata extractor for HTML pages."""

from playwright.async_api import Page

from pathray.models.page_data import MetaData


async def extract_metadata(page: Page) -> MetaData:
    """Extract page metadata (title, meta tags, OG tags, images)."""
    title = await page.title()

    description: str | None = None
    desc_el = await page.query_selector('meta[name="description"]')
    if desc_el:
        description = await desc_el.get_attribute("content")

    keywords: list[str] = []
    kw_el = await page.query_selector('meta[name="keywords"]')
    if kw_el:
        kw_content = await kw_el.get_attribute("content")
        if kw_content:
            keywords = [k.strip() for k in kw_content.split(",") if k.strip()]

    og_tags: dict[str, str] = {}
    og_els = await page.query_selector_all('meta[property^="og:"]')
    for el in og_els:
        prop = await el.get_attribute("property")
        content = await el.get_attribute("content")
        if prop and content is not None:
            og_tags[prop] = content

    canonical_url: str | None = None
    canon_el = await page.query_selector('link[rel="canonical"]')
    if canon_el:
        canonical_url = await canon_el.get_attribute("href")

    images: list[str] = []
    img_els = await page.query_selector_all("img[src]")
    for el in img_els:
        src = await el.get_attribute("src")
        if src:
            images.append(src)

    return MetaData(
        title=title or None,
        description=description,
        keywords=keywords,
        og_tags=og_tags,
        canonical_url=canonical_url,
        images=images,
    )
