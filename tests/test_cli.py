"""Tests for CLI URL validation and erd/run commands."""

import json
import tempfile
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from pathray.cli import _validate_url, app

runner = CliRunner()

# ── URL validation ────────────────────────────────────────────────────────────


def test_validate_url_valid_http():
    assert _validate_url("http://example.com") == "http://example.com"


def test_validate_url_valid_https():
    result = _validate_url("https://example.com/path")
    assert result == "https://example.com/path"


def test_validate_url_invalid_scheme():
    with pytest.raises(typer.BadParameter, match="Invalid URL scheme"):
        _validate_url("ftp://example.com")


def test_validate_url_no_scheme():
    with pytest.raises(typer.BadParameter, match="Invalid URL scheme"):
        _validate_url("example.com")


def test_validate_url_missing_domain():
    with pytest.raises(typer.BadParameter, match="Missing domain"):
        _validate_url("https://")


# ── Helpers ───────────────────────────────────────────────────────────────────

_PAGE_JSON = {
    "url": "http://example.com/users",
    "meta": {"title": "Users"},
    "tables": [
        {
            "headers": ["id", "name", "email"],
            "rows": [["1", "Alice", "alice@example.com"]],
        }
    ],
    "forms": [],
    "text_blocks": [],
}


def _write_page(directory: Path, filename: str = "page-001.json") -> None:
    (directory / filename).write_text(json.dumps(_PAGE_JSON), encoding="utf-8")


# ── erd command ───────────────────────────────────────────────────────────────


def test_erd_json_format():
    with tempfile.TemporaryDirectory() as tmp:
        pages_dir = Path(tmp) / "pages"
        pages_dir.mkdir()
        _write_page(pages_dir)

        out_file = Path(tmp) / "erd.json"
        result = runner.invoke(
            app,
            ["erd", str(pages_dir), "--output", str(out_file), "--format", "json"],
        )
        assert result.exit_code == 0, result.output
        assert out_file.exists()
        data = json.loads(out_file.read_text())
        assert "entities" in data
        assert "relationships" in data


def test_erd_mermaid_format():
    with tempfile.TemporaryDirectory() as tmp:
        pages_dir = Path(tmp) / "pages"
        pages_dir.mkdir()
        _write_page(pages_dir)

        out_file = Path(tmp) / "erd.mmd"
        result = runner.invoke(
            app,
            ["erd", str(pages_dir), "--output", str(out_file), "--format", "mermaid"],
        )
        assert result.exit_code == 0, result.output
        assert out_file.exists()
        assert "erDiagram" in out_file.read_text()


def test_erd_missing_directory():
    result = runner.invoke(
        app,
        ["erd", "/nonexistent/path/pages"],
    )
    assert result.exit_code != 0


def test_erd_empty_directory():
    with tempfile.TemporaryDirectory() as tmp:
        pages_dir = Path(tmp) / "pages"
        pages_dir.mkdir()
        out_file = Path(tmp) / "erd.json"

        result = runner.invoke(
            app,
            ["erd", str(pages_dir), "--output", str(out_file)],
        )
        assert result.exit_code == 0, result.output
        # Empty but valid output
        data = json.loads(out_file.read_text())
        assert data["entities"] == []


def test_erd_dot_format_not_implemented():
    with tempfile.TemporaryDirectory() as tmp:
        pages_dir = Path(tmp) / "pages"
        pages_dir.mkdir()
        _write_page(pages_dir)

        result = runner.invoke(
            app,
            ["erd", str(pages_dir), "--format", "dot"],
        )
        assert result.exit_code != 0


def test_erd_unknown_format():
    with tempfile.TemporaryDirectory() as tmp:
        pages_dir = Path(tmp) / "pages"
        pages_dir.mkdir()
        _write_page(pages_dir)

        result = runner.invoke(
            app,
            ["erd", str(pages_dir), "--format", "xml"],
        )
        assert result.exit_code != 0


def test_erd_creates_output_parent_dirs():
    with tempfile.TemporaryDirectory() as tmp:
        pages_dir = Path(tmp) / "pages"
        pages_dir.mkdir()
        _write_page(pages_dir)

        out_file = Path(tmp) / "nested" / "out" / "erd.json"
        result = runner.invoke(
            app,
            ["erd", str(pages_dir), "--output", str(out_file)],
        )
        assert result.exit_code == 0, result.output
        assert out_file.exists()
