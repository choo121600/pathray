"""Tests for summary report generator."""

import json
from pathlib import Path

import pytest

from pathray.extractor.summary_generator import generate_summary, print_summary
from pathray.models.page_data import (
    FormData,
    FormField,
    MetaData,
    PageData,
    TableData,
)


def _make_page(
    url: str = "https://example.com",
    tables: list[TableData] | None = None,
    forms: list[FormData] | None = None,
    images: list[str] | None = None,
) -> PageData:
    meta = MetaData(images=images or [])
    return PageData(
        url=url,
        meta=meta,
        tables=tables or [],
        forms=forms or [],
    )


def test_empty_pages(tmp_path: Path) -> None:
    output = str(tmp_path / "summary.json")
    result = generate_summary([], output)
    assert result["total_pages"] == 0
    assert result["total_tables"] == 0
    assert result["total_forms"] == 0
    assert result["total_images"] == 0
    assert result["unique_form_fields"] == []
    assert result["unique_table_headers"] == []


def test_counts_single_page(tmp_path: Path) -> None:
    page = _make_page(
        tables=[TableData(headers=["id", "name"], rows=[])],
        forms=[FormData(action="/submit", method="POST", fields=[])],
        images=["img1.png", "img2.png"],
    )
    output = str(tmp_path / "summary.json")
    result = generate_summary([page], output)
    assert result["total_pages"] == 1
    assert result["total_tables"] == 1
    assert result["total_forms"] == 1
    assert result["total_images"] == 2


def test_counts_multiple_pages(tmp_path: Path) -> None:
    page1 = _make_page(
        url="https://example.com/a",
        tables=[TableData(), TableData()],
        forms=[FormData()],
        images=["a.png"],
    )
    page2 = _make_page(
        url="https://example.com/b",
        tables=[TableData()],
        forms=[FormData(), FormData()],
        images=["b.png", "c.png"],
    )
    output = str(tmp_path / "summary.json")
    result = generate_summary([page1, page2], output)
    assert result["total_pages"] == 2
    assert result["total_tables"] == 3
    assert result["total_forms"] == 3
    assert result["total_images"] == 3


def test_unique_form_fields(tmp_path: Path) -> None:
    page1 = _make_page(
        url="https://example.com/a",
        forms=[
            FormData(
                fields=[
                    FormField(name="email", field_type="email"),
                    FormField(name="password", field_type="password"),
                ]
            )
        ],
    )
    page2 = _make_page(
        url="https://example.com/b",
        forms=[
            FormData(
                fields=[
                    FormField(name="email", field_type="email"),  # duplicate
                    FormField(name="username", field_type="text"),
                ]
            )
        ],
    )
    output = str(tmp_path / "summary.json")
    result = generate_summary([page1, page2], output)
    assert sorted(result["unique_form_fields"]) == ["email", "password", "username"]


def test_unique_table_headers(tmp_path: Path) -> None:
    page1 = _make_page(
        url="https://example.com/a",
        tables=[TableData(headers=["id", "name", "email"])],
    )
    page2 = _make_page(
        url="https://example.com/b",
        tables=[
            TableData(headers=["id", "price"]),  # "id" is duplicate
        ],
    )
    output = str(tmp_path / "summary.json")
    result = generate_summary([page1, page2], output)
    assert sorted(result["unique_table_headers"]) == ["email", "id", "name", "price"]


def test_empty_field_names_excluded(tmp_path: Path) -> None:
    page = _make_page(
        forms=[
            FormData(
                fields=[
                    FormField(name="", field_type="submit"),  # empty name
                    FormField(name="search", field_type="text"),
                ]
            )
        ],
    )
    output = str(tmp_path / "summary.json")
    result = generate_summary([page], output)
    assert result["unique_form_fields"] == ["search"]


def test_saves_to_json_file(tmp_path: Path) -> None:
    page = _make_page(
        tables=[TableData(headers=["col1"])],
        forms=[FormData(fields=[FormField(name="field1", field_type="text")])],
    )
    output = str(tmp_path / "subdir" / "summary.json")
    generate_summary([page], output)

    saved = json.loads(Path(output).read_text())
    assert saved["total_pages"] == 1
    assert saved["total_tables"] == 1
    assert saved["unique_form_fields"] == ["field1"]
    assert saved["unique_table_headers"] == ["col1"]


def test_creates_output_directory(tmp_path: Path) -> None:
    output = str(tmp_path / "deep" / "nested" / "summary.json")
    generate_summary([], output)
    assert Path(output).exists()


def test_returns_sorted_fields(tmp_path: Path) -> None:
    page = _make_page(
        forms=[
            FormData(
                fields=[
                    FormField(name="zebra", field_type="text"),
                    FormField(name="apple", field_type="text"),
                    FormField(name="mango", field_type="text"),
                ]
            )
        ],
    )
    output = str(tmp_path / "summary.json")
    result = generate_summary([page], output)
    assert result["unique_form_fields"] == ["apple", "mango", "zebra"]


def test_print_summary_runs_without_error() -> None:
    summary = {
        "total_pages": 5,
        "total_tables": 10,
        "total_forms": 3,
        "total_images": 20,
        "unique_form_fields": ["email", "name"],
        "unique_table_headers": ["id", "title"],
    }
    # Should not raise
    print_summary(summary)


def test_print_summary_empty() -> None:
    summary = {
        "total_pages": 0,
        "total_tables": 0,
        "total_forms": 0,
        "total_images": 0,
        "unique_form_fields": [],
        "unique_table_headers": [],
    }
    print_summary(summary)
