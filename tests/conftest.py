"""Shared test fixtures for pathray."""

import pytest

from pathray.models.erd import Entity, EntityField


@pytest.fixture
def sample_sitemap_entry() -> dict:
    """Sample data for SitemapEntry validation."""
    return {
        "url": "https://example.com",
        "title": "Example",
        "depth": 0,
        "status_code": 200,
        "links": ["https://example.com/about"],
        "timestamp": "2026-03-19T00:00:00",
    }


@pytest.fixture
def sample_entity() -> Entity:
    """Sample Entity for testing."""
    return Entity(
        name="User",
        fields=[
            EntityField(
                name="id", field_type="integer",
                is_primary=True, nullable=False,
            ),
            EntityField(name="email", field_type="string"),
        ],
        source_url="https://example.com/users",
    )
