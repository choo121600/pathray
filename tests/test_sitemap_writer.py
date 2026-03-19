"""Tests for sitemap JSON output (Issue #9)."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from pathray.crawler.sitemap_writer import write_sitemap
from pathray.models.sitemap import SitemapEntry


@pytest.fixture
def sample_entries() -> list[SitemapEntry]:
    return [
        SitemapEntry(
            url="https://example.com/",
            title="Home",
            depth=0,
            status_code=200,
            links=["https://example.com/about"],
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        SitemapEntry(
            url="https://example.com/about",
            title="About",
            depth=1,
            status_code=200,
            links=[],
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
    ]


def test_write_sitemap_creates_file(
    tmp_path: Path, sample_entries: list[SitemapEntry],
):
    output = str(tmp_path / "output" / "sitemap.json")
    result = write_sitemap(sample_entries, output)
    assert result.exists()


def test_write_sitemap_valid_json(
    tmp_path: Path, sample_entries: list[SitemapEntry],
):
    output = str(tmp_path / "sitemap.json")
    write_sitemap(sample_entries, output)
    data = json.loads(Path(output).read_text())
    assert isinstance(data, list)
    assert len(data) == 2


def test_write_sitemap_entry_fields(
    tmp_path: Path, sample_entries: list[SitemapEntry],
):
    output = str(tmp_path / "sitemap.json")
    write_sitemap(sample_entries, output)
    data = json.loads(Path(output).read_text())
    entry = data[0]
    assert "url" in entry
    assert "title" in entry
    assert "depth" in entry
    assert "status_code" in entry


def test_write_sitemap_creates_directory(
    tmp_path: Path, sample_entries: list[SitemapEntry],
):
    output = str(tmp_path / "deep" / "nested" / "sitemap.json")
    result = write_sitemap(sample_entries, output)
    assert result.exists()
    assert result.parent.exists()
