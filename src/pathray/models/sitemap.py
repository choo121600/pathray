"""Sitemap models for crawl results."""

from datetime import datetime

from pydantic import BaseModel, HttpUrl


class SitemapEntry(BaseModel):
    """A single entry in the crawled sitemap.

    Represents one page discovered during the crawl phase,
    including its URL, metadata, and outgoing links.
    """

    url: HttpUrl
    title: str | None = None
    depth: int
    status_code: int
    links: list[HttpUrl] = []
    timestamp: datetime
