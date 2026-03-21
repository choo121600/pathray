"""Tests for the ai_analyzer module."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from pathray.erd.ai_analyzer import _build_prompt, analyze_with_ai, prepare_pages_for_ai
from pathray.models.erd import Entity, Relationship
from pathray.models.page_data import (
    FormData,
    FormField,
    MetaData,
    PageData,
    TableData,
)


def _make_page(
    url: str = "https://example.com/users",
    title: str | None = "Users",
    tables: list[TableData] | None = None,
    forms: list[FormData] | None = None,
) -> PageData:
    return PageData(
        url=url,  # type: ignore[arg-type]
        meta=MetaData(
            title=title,
            og_tags={"og:title": "Users"},
            images=["https://example.com/logo.png"],
        ),
        tables=tables or [],
        forms=forms or [],
    )


# ---------------------------------------------------------------------------
# prepare_pages_for_ai
# ---------------------------------------------------------------------------


class TestPreparePagesForAi:
    def test_basic_structure(self):
        page = _make_page()
        result = prepare_pages_for_ai([page])
        assert len(result) == 1
        item = result[0]
        assert item["url"] == "https://example.com/users"
        assert item["title"] == "Users"
        assert "tables" in item
        assert "forms" in item

    def test_no_images_or_og_tags(self):
        """Condensed output must not contain images or og_tags."""
        page = _make_page()
        result = prepare_pages_for_ai([page])
        item = result[0]
        assert "images" not in item
        assert "og_tags" not in item

    def test_no_text_blocks(self):
        """text_blocks must be absent from condensed output."""
        page = _make_page()
        result = prepare_pages_for_ai([page])
        assert "text_blocks" not in result[0]

    def test_table_rows_limited_to_three(self):
        rows = [["a"], ["b"], ["c"], ["d"], ["e"]]
        table = TableData(headers=["col"], rows=rows)
        page = _make_page(tables=[table])
        result = prepare_pages_for_ai([page])
        assert len(result[0]["tables"][0]["sample_rows"]) == 3

    def test_table_with_no_headers_skipped(self):
        table = TableData(headers=[], rows=[["data"]])
        page = _make_page(tables=[table])
        result = prepare_pages_for_ai([page])
        assert result[0]["tables"] == []

    def test_table_fields_present(self):
        table = TableData(
            headers=["id", "name"],
            rows=[["1", "Alice"]],
            caption="Users",
            context_heading="User List",
        )
        page = _make_page(tables=[table])
        result = prepare_pages_for_ai([page])
        t = result[0]["tables"][0]
        assert t["caption"] == "Users"
        assert t["context_heading"] == "User List"
        assert t["headers"] == ["id", "name"]

    def test_empty_form_skipped(self):
        form = FormData(fields=[])
        page = _make_page(forms=[form])
        result = prepare_pages_for_ai([page])
        assert result[0]["forms"] == []

    def test_form_fields_condensed(self):
        form = FormData(
            action="/login",
            method="POST",
            fields=[
                FormField(
                    name="username",
                    field_type="text",
                    label="Username",
                    required=True,
                    placeholder="Enter username",
                    options=["opt1"],
                )
            ],
        )
        page = _make_page(forms=[form])
        result = prepare_pages_for_ai([page])
        f = result[0]["forms"][0]
        assert f["action"] == "/login"
        assert f["method"] == "POST"
        field = f["fields"][0]
        assert field["name"] == "username"
        assert field["field_type"] == "text"
        assert field["label"] == "Username"
        assert field["required"] is True
        # placeholder and options must not be present
        assert "placeholder" not in field
        assert "options" not in field

    def test_multiple_pages(self):
        p1 = _make_page(url="https://example.com/a", title="A")
        p2 = _make_page(url="https://example.com/b", title="B")
        result = prepare_pages_for_ai([p1, p2])
        assert len(result) == 2


# ---------------------------------------------------------------------------
# _build_prompt
# ---------------------------------------------------------------------------


class TestBuildPrompt:
    def test_returns_string(self):
        result = _build_prompt([])
        assert isinstance(result, str)

    def test_contains_json_format_instructions(self):
        result = _build_prompt([])
        assert '"entities"' in result
        assert '"relationships"' in result
        assert "field_type" in result

    def test_contains_page_data(self):
        condensed = [{"url": "https://example.com", "title": "Test", "tables": [], "forms": []}]
        result = _build_prompt(condensed)
        assert "https://example.com" in result

    def test_instructs_no_markdown(self):
        result = _build_prompt([])
        # The prompt must tell Claude not to wrap in markdown fences
        assert "```" not in result or "마크다운" in result


# ---------------------------------------------------------------------------
# analyze_with_ai
# ---------------------------------------------------------------------------

_VALID_AI_RESPONSE = {
    "entities": [
        {
            "name": "User",
            "fields": [
                {"name": "id", "field_type": "INTEGER", "nullable": False, "is_primary": True},
                {"name": "email", "field_type": "VARCHAR", "nullable": True, "is_primary": False},
            ],
            "source_url": "https://example.com/users",
            "source_title": "Users",
        }
    ],
    "relationships": [
        {"from_entity": "User", "to_entity": "Order", "relation_type": "one-to-many", "label": "places"}
    ],
}


def _mock_proc(stdout: str, returncode: int = 0) -> MagicMock:
    mock = MagicMock()
    mock.returncode = returncode
    mock.stdout = stdout
    mock.stderr = ""
    return mock


class TestAnalyzeWithAi:
    def _make_page_with_table(self) -> PageData:
        table = TableData(headers=["id", "email"], rows=[["1", "a@b.com"]])
        return _make_page(tables=[table])

    def test_parses_valid_response(self):
        outer = json.dumps({"result": json.dumps(_VALID_AI_RESPONSE)})
        with patch("subprocess.run", return_value=_mock_proc(outer)):
            entities, relationships = analyze_with_ai([self._make_page_with_table()])

        assert len(entities) == 1
        assert entities[0].name == "User"
        assert entities[0].fields[0].is_primary is True
        assert len(relationships) == 1
        assert relationships[0].from_entity == "User"

    def test_parses_markdown_wrapped_response(self):
        """Claude may wrap JSON in ```json ... ``` despite instructions."""
        inner = json.dumps(_VALID_AI_RESPONSE)
        wrapped = f"```json\n{inner}\n```"
        outer = json.dumps({"result": wrapped})
        with patch("subprocess.run", return_value=_mock_proc(outer)):
            entities, relationships = analyze_with_ai([self._make_page_with_table()])

        assert len(entities) == 1
        assert entities[0].name == "User"

    def test_fallback_on_nonzero_exit(self):
        with patch("subprocess.run", return_value=_mock_proc("", returncode=1)):
            entities, relationships = analyze_with_ai([self._make_page_with_table()])

        # Fallback to heuristic — should still return entity lists (may be non-empty)
        assert isinstance(entities, list)
        assert isinstance(relationships, list)

    def test_fallback_on_invalid_json(self):
        outer = json.dumps({"result": "not valid json {"})
        with patch("subprocess.run", return_value=_mock_proc(outer)):
            entities, relationships = analyze_with_ai([self._make_page_with_table()])

        assert isinstance(entities, list)
        assert isinstance(relationships, list)

    def test_fallback_when_claude_not_found(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            entities, relationships = analyze_with_ai([self._make_page_with_table()])

        assert isinstance(entities, list)
        assert isinstance(relationships, list)

    def test_fallback_on_timeout(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="claude", timeout=120)):
            entities, relationships = analyze_with_ai([self._make_page_with_table()])

        assert isinstance(entities, list)
        assert isinstance(relationships, list)

    def test_entity_fields_mapped_correctly(self):
        outer = json.dumps({"result": json.dumps(_VALID_AI_RESPONSE)})
        with patch("subprocess.run", return_value=_mock_proc(outer)):
            entities, _ = analyze_with_ai([self._make_page_with_table()])

        user = entities[0]
        assert isinstance(user, Entity)
        assert user.source_url == "https://example.com/users"
        assert user.source_title == "Users"

    def test_relationship_mapped_correctly(self):
        outer = json.dumps({"result": json.dumps(_VALID_AI_RESPONSE)})
        with patch("subprocess.run", return_value=_mock_proc(outer)):
            _, relationships = analyze_with_ai([self._make_page_with_table()])

        rel = relationships[0]
        assert isinstance(rel, Relationship)
        assert rel.relation_type == "one-to-many"
        assert rel.label == "places"

    def test_empty_entities_and_relationships(self):
        empty_response = {"entities": [], "relationships": []}
        outer = json.dumps({"result": json.dumps(empty_response)})
        with patch("subprocess.run", return_value=_mock_proc(outer)):
            entities, relationships = analyze_with_ai([self._make_page_with_table()])

        assert entities == []
        assert relationships == []
