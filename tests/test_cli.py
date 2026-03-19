"""Tests for CLI URL validation."""

import pytest
import typer

from pathray.cli import _validate_url


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
