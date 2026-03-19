"""Tests for extraction engine."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from pathray.extractor.extraction_engine import ExtractionEngine, ExtractionProgress
from pathray.models.page_data import (
    MetaData,
    PageData,
)


def _make_sitemap(tmp_path: Path, entries: list[dict]) -> Path:
    sitemap = tmp_path / "sitemap.json"
    sitemap.write_text(json.dumps(entries))
    return sitemap


def _sample_entry(url: str = "https://example.com/") -> dict:
    return {
        "url": url,
        "title": "Example",
        "depth": 0,
        "status_code": 200,
        "links": [],
        "timestamp": "2026-03-19T00:00:00+00:00",
    }


def _mock_page_data(url: str) -> PageData:
    return PageData(
        url=url,
        meta=MetaData(title="Test"),
        tables=[],
        forms=[],
        text_blocks=[],
    )


@pytest.mark.asyncio
async def test_run_produces_json_files(tmp_path):
    sitemap = _make_sitemap(tmp_path, [_sample_entry()])
    output_dir = tmp_path / "data"

    mock_browser = AsyncMock()
    mock_page = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)

    with (
        patch("pathray.extractor.extraction_engine.launch_browser") as mock_launch,
        patch(
            "pathray.extractor.extraction_engine.extract_metadata",
            return_value=MetaData(),
        ),
        patch("pathray.extractor.extraction_engine.extract_tables", return_value=[]),
        patch("pathray.extractor.extraction_engine.extract_forms", return_value=[]),
        patch("pathray.extractor.extraction_engine.extract_text", return_value=[]),
    ):
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_browser)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_launch.return_value = mock_cm

        engine = ExtractionEngine(str(sitemap), str(output_dir), concurrency=1)
        pages = await engine.run()

    assert len(pages) == 1
    assert (output_dir / "page-000.json").exists()


@pytest.mark.asyncio
async def test_run_multiple_entries(tmp_path):
    entries = [
        _sample_entry("https://example.com/"),
        _sample_entry("https://example.com/about"),
        _sample_entry("https://example.com/contact"),
    ]
    sitemap = _make_sitemap(tmp_path, entries)
    output_dir = tmp_path / "data"

    mock_browser = AsyncMock()
    mock_page = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)

    with (
        patch("pathray.extractor.extraction_engine.launch_browser") as mock_launch,
        patch(
            "pathray.extractor.extraction_engine.extract_metadata",
            return_value=MetaData(),
        ),
        patch("pathray.extractor.extraction_engine.extract_tables", return_value=[]),
        patch("pathray.extractor.extraction_engine.extract_forms", return_value=[]),
        patch("pathray.extractor.extraction_engine.extract_text", return_value=[]),
    ):
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_browser)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_launch.return_value = mock_cm

        engine = ExtractionEngine(str(sitemap), str(output_dir), concurrency=2)
        pages = await engine.run()

    assert len(pages) == 3
    assert (output_dir / "page-000.json").exists()
    assert (output_dir / "page-001.json").exists()
    assert (output_dir / "page-002.json").exists()


@pytest.mark.asyncio
async def test_output_dir_created_automatically(tmp_path):
    sitemap = _make_sitemap(tmp_path, [_sample_entry()])
    output_dir = tmp_path / "nested" / "data"

    mock_browser = AsyncMock()
    mock_page = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)

    with (
        patch("pathray.extractor.extraction_engine.launch_browser") as mock_launch,
        patch(
            "pathray.extractor.extraction_engine.extract_metadata",
            return_value=MetaData(),
        ),
        patch("pathray.extractor.extraction_engine.extract_tables", return_value=[]),
        patch("pathray.extractor.extraction_engine.extract_forms", return_value=[]),
        patch("pathray.extractor.extraction_engine.extract_text", return_value=[]),
    ):
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_browser)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_launch.return_value = mock_cm

        engine = ExtractionEngine(str(sitemap), str(output_dir), concurrency=1)
        await engine.run()

    assert output_dir.exists()


@pytest.mark.asyncio
async def test_progress_callbacks_invoked(tmp_path):
    sitemap = _make_sitemap(tmp_path, [_sample_entry()])
    output_dir = tmp_path / "data"

    calls: list[str] = []

    class TrackingProgress(ExtractionProgress):
        def on_page_start(self, url, index, total):
            calls.append(f"start:{index}/{total}")

        def on_page_done(self, url, index, total, error):
            calls.append(f"done:{index}/{total}:error={error}")

        def on_complete(self, total, errors, elapsed):
            calls.append(f"complete:{total}:{errors}")

    mock_browser = AsyncMock()
    mock_page = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)

    with (
        patch("pathray.extractor.extraction_engine.launch_browser") as mock_launch,
        patch(
            "pathray.extractor.extraction_engine.extract_metadata",
            return_value=MetaData(),
        ),
        patch("pathray.extractor.extraction_engine.extract_tables", return_value=[]),
        patch("pathray.extractor.extraction_engine.extract_forms", return_value=[]),
        patch("pathray.extractor.extraction_engine.extract_text", return_value=[]),
    ):
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_browser)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_launch.return_value = mock_cm

        engine = ExtractionEngine(
            str(sitemap), str(output_dir), concurrency=1, progress=TrackingProgress(),
        )
        await engine.run()

    assert "start:1/1" in calls
    assert "done:1/1:error=None" in calls
    assert "complete:1:0" in calls


@pytest.mark.asyncio
async def test_empty_sitemap(tmp_path):
    sitemap = _make_sitemap(tmp_path, [])
    output_dir = tmp_path / "data"

    mock_browser = AsyncMock()
    with (
        patch("pathray.extractor.extraction_engine.launch_browser") as mock_launch,
    ):
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_browser)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_launch.return_value = mock_cm

        engine = ExtractionEngine(str(sitemap), str(output_dir), concurrency=1)
        pages = await engine.run()

    assert pages == []


@pytest.mark.asyncio
async def test_page_failure_does_not_stop_pipeline(tmp_path):
    """Individual page extraction failure should not halt other pages."""
    entries = [
        _sample_entry("https://example.com/good"),
        _sample_entry("https://example.com/bad"),
        _sample_entry("https://example.com/also-good"),
    ]
    sitemap = _make_sitemap(tmp_path, entries)
    output_dir = tmp_path / "data"

    call_count = 0

    async def _failing_metadata(page):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("Simulated extraction failure")
        return MetaData()

    mock_browser = AsyncMock()
    mock_page = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)

    with (
        patch(
            "pathray.extractor.extraction_engine.launch_browser",
        ) as mock_launch,
        patch(
            "pathray.extractor.extraction_engine.extract_metadata",
            side_effect=_failing_metadata,
        ),
        patch(
            "pathray.extractor.extraction_engine.extract_tables",
            return_value=[],
        ),
        patch(
            "pathray.extractor.extraction_engine.extract_forms",
            return_value=[],
        ),
        patch(
            "pathray.extractor.extraction_engine.extract_text",
            return_value=[],
        ),
    ):
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_browser)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_launch.return_value = mock_cm

        engine = ExtractionEngine(
            str(sitemap), str(output_dir), concurrency=1,
        )
        pages = await engine.run()

    assert len(pages) == 2
    assert (output_dir / "page-000.json").exists()
    assert not (output_dir / "page-001.json").exists()
    assert (output_dir / "page-002.json").exists()


@pytest.mark.asyncio
async def test_progress_reports_error_on_failure(tmp_path):
    """Progress callback should report error string for failed pages."""
    sitemap = _make_sitemap(tmp_path, [_sample_entry()])
    output_dir = tmp_path / "data"

    reported_errors: list[str | None] = []
    complete_info: dict = {}

    class ErrorTracker(ExtractionProgress):
        def on_page_done(self, url, index, total, error):
            reported_errors.append(error)

        def on_complete(self, total, errors, elapsed):
            complete_info["total"] = total
            complete_info["errors"] = errors

    mock_browser = AsyncMock()
    mock_page = AsyncMock()
    mock_browser.new_page = AsyncMock(return_value=mock_page)

    with (
        patch(
            "pathray.extractor.extraction_engine.launch_browser",
        ) as mock_launch,
        patch(
            "pathray.extractor.extraction_engine.extract_metadata",
            side_effect=RuntimeError("broken"),
        ),
        patch(
            "pathray.extractor.extraction_engine.extract_tables",
            return_value=[],
        ),
        patch(
            "pathray.extractor.extraction_engine.extract_forms",
            return_value=[],
        ),
        patch(
            "pathray.extractor.extraction_engine.extract_text",
            return_value=[],
        ),
    ):
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_browser)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_launch.return_value = mock_cm

        engine = ExtractionEngine(
            str(sitemap), str(output_dir), concurrency=1,
            progress=ErrorTracker(),
        )
        pages = await engine.run()

    assert len(pages) == 0
    assert len(reported_errors) == 1
    assert "broken" in reported_errors[0]
    assert complete_info["total"] == 1
    assert complete_info["errors"] == 1
