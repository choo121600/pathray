"""Sample tests for pathray project setup verification."""

import pytest

from pathray import __version__
from pathray.models import Entity, PageData, SitemapEntry
from pathray.models.erd import EntityField, Relationship
from pathray.models.page_data import FormField, MetaData, TableData, TextContent


def test_version():
    assert __version__ == "0.1.0"


def test_sitemap_entry_validation(sample_sitemap_entry: dict):
    entry = SitemapEntry.model_validate(sample_sitemap_entry)
    assert str(entry.url) == "https://example.com/"
    assert entry.depth == 0
    assert entry.status_code == 200


def test_sitemap_entry_links(sample_sitemap_entry: dict):
    entry = SitemapEntry.model_validate(sample_sitemap_entry)
    assert len(entry.links) == 1


def test_page_data_defaults():
    page = PageData(url="https://example.com")
    assert page.tables == []
    assert page.forms == []
    assert page.text_blocks == []


def test_table_data():
    table = TableData(headers=["Name", "Age"], rows=[["Alice", "30"]])
    assert len(table.headers) == 2
    assert len(table.rows) == 1


def test_form_field():
    field = FormField(name="email", field_type="email", required=True)
    assert field.required is True


def test_text_content():
    text = TextContent(tag="h1", text="Hello", level=1)
    assert text.level == 1


def test_metadata():
    meta = MetaData(title="Test", keywords=["a", "b"])
    assert len(meta.keywords) == 2


def test_entity(sample_entity: Entity):
    assert sample_entity.name == "User"
    assert len(sample_entity.fields) == 2
    assert sample_entity.fields[0].is_primary is True


def test_entity_field():
    field = EntityField(
        name="id", field_type="integer", is_primary=True, nullable=False,
    )
    assert field.nullable is False


def test_relationship():
    rel = Relationship(from_entity="User", to_entity="Order")
    assert rel.relation_type == "one-to-many"


def test_model_imports():
    """Verify all models are importable from pathray.models."""
    from pathray.models import (
        Entity,
        EntityField,
        FormField,
        MetaData,
        PageData,
        Relationship,
        SitemapEntry,
        TableData,
        TextContent,
    )
    assert all([
        Entity, EntityField, FormField, MetaData, PageData,
        Relationship, SitemapEntry, TableData, TextContent,
    ])


@pytest.mark.asyncio
async def test_async_support():
    """Verify pytest-asyncio works."""
    result = await _async_helper()
    assert result == 42


async def _async_helper() -> int:
    return 42
