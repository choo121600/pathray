"""Page data models for extracted page structures."""

from pydantic import BaseModel, HttpUrl


class TableData(BaseModel):
    """Represents an HTML table found on a page.

    Captures headers and row data for structure analysis.
    """

    headers: list[str] = []
    rows: list[list[str]] = []
    caption: str | None = None


class FormField(BaseModel):
    """Represents a form input field.

    Captures field attributes for entity/relationship extraction.
    """

    name: str
    field_type: str
    label: str | None = None
    required: bool = False
    placeholder: str | None = None
    options: list[str] = []


class TextContent(BaseModel):
    """Represents a text block on a page.

    Captures headings, paragraphs, and list items.
    """

    tag: str
    text: str
    level: int | None = None


class MetaData(BaseModel):
    """Page-level metadata.

    Captures meta tags, title, and other page attributes.
    """

    title: str | None = None
    description: str | None = None
    keywords: list[str] = []
    og_tags: dict[str, str] = {}
    canonical_url: str | None = None
    images: list[str] = []


class FormData(BaseModel):
    """Represents a complete HTML form with its fields."""

    action: str | None = None
    method: str = "GET"
    fields: list[FormField] = []


class PageData(BaseModel):
    """Complete extracted data for a single page.

    Aggregates all structural elements found on the page.
    """

    url: HttpUrl
    meta: MetaData = MetaData()
    tables: list[TableData] = []
    forms: list[FormData] = []
    text_blocks: list[TextContent] = []
