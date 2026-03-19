"""Tests for entity_inferrer module."""

import json
from pathlib import Path

import pytest

from pathray.erd.entity_inferrer import (
    _fields_from_form,
    _fields_from_table,
    _infer_field_type,
    _jaccard,
    _merge_entities,
    infer_entities,
    infer_entities_from_page,
    load_pages_from_dir,
)
from pathray.models.erd import Entity, EntityField
from pathray.models.page_data import (
    FormData,
    FormField,
    MetaData,
    PageData,
    TableData,
)


def _make_page(
    url: str = "https://example.com/users",
    title: str | None = None,
    tables: list[TableData] | None = None,
    forms: list[FormData] | None = None,
) -> PageData:
    return PageData(
        url=url,  # type: ignore[arg-type]
        meta=MetaData(title=title),
        tables=tables or [],
        forms=forms or [],
    )


# ---------------------------------------------------------------------------
# _infer_field_type
# ---------------------------------------------------------------------------


class TestInferFieldType:
    def test_email_name(self):
        assert _infer_field_type("email") == "VARCHAR"

    def test_email_address_name(self):
        assert _infer_field_type("email_address") == "VARCHAR"

    def test_date_name(self):
        assert _infer_field_type("birth_date") == "DATE"

    def test_created_at(self):
        assert _infer_field_type("created_at") == "DATE"

    def test_phone_name(self):
        assert _infer_field_type("phone") == "VARCHAR"

    def test_tel_name(self):
        assert _infer_field_type("tel") == "VARCHAR"

    def test_url_name(self):
        assert _infer_field_type("profile_url") == "VARCHAR"

    def test_boolean_active(self):
        assert _infer_field_type("active") == "BOOLEAN"

    def test_boolean_is_prefix(self):
        assert _infer_field_type("is_admin") == "BOOLEAN"

    def test_integer_count(self):
        assert _infer_field_type("count") == "INTEGER"

    def test_integer_price(self):
        assert _infer_field_type("price") == "INTEGER"

    def test_default_text(self):
        assert _infer_field_type("description") == "TEXT"

    def test_form_type_email(self):
        assert _infer_field_type("contact", "email") == "VARCHAR"

    def test_form_type_number(self):
        assert _infer_field_type("qty", "number") == "INTEGER"

    def test_form_type_checkbox(self):
        assert _infer_field_type("agree", "checkbox") == "BOOLEAN"

    def test_form_type_date(self):
        assert _infer_field_type("dob", "date") == "DATE"

    def test_form_type_url(self):
        assert _infer_field_type("website", "url") == "VARCHAR"

    def test_name_takes_priority_over_form_type(self):
        # field name "email" pattern wins before form_type lookup
        assert _infer_field_type("email", "text") == "VARCHAR"


# ---------------------------------------------------------------------------
# _fields_from_table
# ---------------------------------------------------------------------------


class TestFieldsFromTable:
    def test_basic_headers(self):
        table = TableData(headers=["id", "name", "email"], rows=[])
        fields = _fields_from_table(table)
        assert [f.name for f in fields] == ["id", "name", "email"]

    def test_id_is_primary(self):
        table = TableData(headers=["id", "name"], rows=[])
        fields = _fields_from_table(table)
        assert fields[0].is_primary is True
        assert fields[0].nullable is False

    def test_non_id_not_primary(self):
        table = TableData(headers=["name", "email"], rows=[])
        fields = _fields_from_table(table)
        assert all(not f.is_primary for f in fields)

    def test_header_whitespace_normalised(self):
        table = TableData(headers=["  First Name  "], rows=[])
        fields = _fields_from_table(table)
        assert fields[0].name == "first_name"

    def test_empty_headers_skipped(self):
        table = TableData(headers=["", "name", ""], rows=[])
        fields = _fields_from_table(table)
        assert len(fields) == 1
        assert fields[0].name == "name"

    def test_type_inference_applied(self):
        table = TableData(headers=["email", "created_at", "count"], rows=[])
        fields = _fields_from_table(table)
        types = {f.name: f.field_type for f in fields}
        assert types["email"] == "VARCHAR"
        assert types["created_at"] == "DATE"
        assert types["count"] == "INTEGER"


# ---------------------------------------------------------------------------
# _fields_from_form
# ---------------------------------------------------------------------------


class TestFieldsFromForm:
    def test_basic_fields(self):
        form_fields = [
            FormField(name="username", field_type="text"),
            FormField(name="email", field_type="email"),
        ]
        fields = _fields_from_form(form_fields)
        assert [f.name for f in fields] == ["username", "email"]

    def test_submit_button_skipped(self):
        form_fields = [
            FormField(name="name", field_type="text"),
            FormField(name="submit", field_type="submit"),
        ]
        fields = _fields_from_form(form_fields)
        assert len(fields) == 1
        assert fields[0].name == "name"

    def test_hidden_field_skipped(self):
        form_fields = [
            FormField(name="csrf", field_type="hidden"),
            FormField(name="username", field_type="text"),
        ]
        fields = _fields_from_form(form_fields)
        assert len(fields) == 1

    def test_required_field_not_nullable(self):
        form_fields = [FormField(name="username", field_type="text", required=True)]
        fields = _fields_from_form(form_fields)
        assert fields[0].nullable is False

    def test_optional_field_nullable(self):
        form_fields = [FormField(name="bio", field_type="text", required=False)]
        fields = _fields_from_form(form_fields)
        assert fields[0].nullable is True

    def test_duplicate_names_deduplicated(self):
        form_fields = [
            FormField(name="tag", field_type="text"),
            FormField(name="tag", field_type="text"),
        ]
        fields = _fields_from_form(form_fields)
        assert len(fields) == 1

    def test_type_inference_from_form_type(self):
        form_fields = [
            FormField(name="dob", field_type="date"),
            FormField(name="qty", field_type="number"),
        ]
        fields = _fields_from_form(form_fields)
        types = {f.name: f.field_type for f in fields}
        assert types["dob"] == "DATE"
        assert types["qty"] == "INTEGER"


# ---------------------------------------------------------------------------
# _jaccard
# ---------------------------------------------------------------------------


class TestJaccard:
    def test_identical_sets(self):
        assert _jaccard({"a", "b"}, {"a", "b"}) == 1.0

    def test_disjoint_sets(self):
        assert _jaccard({"a"}, {"b"}) == 0.0

    def test_partial_overlap(self):
        sim = _jaccard({"a", "b", "c"}, {"b", "c", "d"})
        # intersection=2, union=4 → 0.5
        assert abs(sim - 0.5) < 1e-9

    def test_both_empty(self):
        assert _jaccard(set(), set()) == 1.0

    def test_one_empty(self):
        assert _jaccard(set(), {"a"}) == 0.0


# ---------------------------------------------------------------------------
# _merge_entities
# ---------------------------------------------------------------------------


class TestMergeEntities:
    def _entity(self, name: str, field_names: list[str]) -> Entity:
        return Entity(
            name=name,
            fields=[EntityField(name=n, field_type="TEXT") for n in field_names],
        )

    def test_identical_entities_merged(self):
        e1 = self._entity("User", ["id", "name", "email"])
        e2 = self._entity("User", ["id", "name", "email"])
        result = _merge_entities([e1, e2])
        assert len(result) == 1

    def test_similar_entities_merged(self):
        # Jaccard = 3/5 = 0.6 ≥ 0.6 → merge
        # intersection={id,name,email}=3, union={id,name,email,phone,bio}=5
        e1 = self._entity("User", ["id", "name", "email", "phone"])
        e2 = self._entity("UserProfile", ["id", "name", "email", "bio"])
        result = _merge_entities([e1, e2])
        assert len(result) == 1
        names = {f.name for f in result[0].fields}
        assert "bio" in names

    def test_dissimilar_entities_not_merged(self):
        # Jaccard = 0/5 = 0 < 0.6 → keep separate
        e1 = self._entity("User", ["id", "name", "email"])
        e2 = self._entity("Product", ["sku", "price", "stock"])
        result = _merge_entities([e1, e2])
        assert len(result) == 2

    def test_empty_list(self):
        assert _merge_entities([]) == []

    def test_single_entity_unchanged(self):
        e = self._entity("User", ["id", "name"])
        result = _merge_entities([e])
        assert len(result) == 1


# ---------------------------------------------------------------------------
# infer_entities_from_page
# ---------------------------------------------------------------------------


class TestInferEntitiesFromPage:
    def test_from_table(self):
        table = TableData(headers=["id", "name", "email"], rows=[])
        page = _make_page(title="User", tables=[table])
        entities = infer_entities_from_page(page)
        assert len(entities) == 1
        assert entities[0].name == "User"
        assert len(entities[0].fields) == 3

    def test_from_form(self):
        form = FormData(
            fields=[
                FormField(name="username", field_type="text"),
                FormField(name="password", field_type="password"),
            ]
        )
        page = _make_page(title="Login", forms=[form])
        entities = infer_entities_from_page(page)
        assert len(entities) == 1
        assert entities[0].name == "Login"

    def test_name_from_title(self):
        table = TableData(headers=["id", "title"], rows=[])
        page = _make_page(url="https://example.com/posts", title="Post List | MySite", tables=[table])
        entities = infer_entities_from_page(page)
        assert entities[0].name == "PostList"

    def test_name_from_url_when_no_title(self):
        table = TableData(headers=["id", "name"], rows=[])
        page = _make_page(url="https://example.com/products", title=None, tables=[table])
        entities = infer_entities_from_page(page)
        assert entities[0].name == "Products"

    def test_empty_table_skipped(self):
        table = TableData(headers=[], rows=[])
        page = _make_page(title="Empty", tables=[table])
        entities = infer_entities_from_page(page)
        assert entities == []

    def test_empty_form_skipped(self):
        form = FormData(fields=[FormField(name="submit", field_type="submit")])
        page = _make_page(title="Empty", forms=[form])
        entities = infer_entities_from_page(page)
        assert entities == []

    def test_multiple_tables_get_distinct_names(self):
        t1 = TableData(headers=["id", "name"], rows=[])
        t2 = TableData(headers=["sku", "price"], rows=[])
        page = _make_page(title="Report", tables=[t1, t2])
        entities = infer_entities_from_page(page)
        assert len(entities) == 2
        names = {e.name for e in entities}
        assert "ReportTable1" in names
        assert "ReportTable2" in names

    def test_source_url_set(self):
        table = TableData(headers=["id"], rows=[])
        page = _make_page(url="https://example.com/users", title="User", tables=[table])
        entities = infer_entities_from_page(page)
        assert "example.com/users" in entities[0].source_url


# ---------------------------------------------------------------------------
# infer_entities (multi-page + merge)
# ---------------------------------------------------------------------------


class TestInferEntities:
    def test_merges_similar_across_pages(self):
        # Jaccard = 3/5 = 0.6 ≥ 0.6 → merge
        # intersection={id,name,email}=3, union={id,name,email,phone,bio}=5
        t1 = TableData(headers=["id", "name", "email", "phone"], rows=[])
        t2 = TableData(headers=["id", "name", "email", "bio"], rows=[])
        p1 = _make_page(url="https://example.com/users", title="User", tables=[t1])
        p2 = _make_page(url="https://example.com/users/new", title="User", tables=[t2])
        result = infer_entities([p1, p2])
        assert len(result) == 1
        field_names = {f.name for f in result[0].fields}
        assert "bio" in field_names

    def test_keeps_distinct_entities(self):
        t1 = TableData(headers=["id", "name", "email"], rows=[])
        t2 = TableData(headers=["sku", "price", "stock"], rows=[])
        p1 = _make_page(url="https://example.com/users", title="User", tables=[t1])
        p2 = _make_page(url="https://example.com/products", title="Product", tables=[t2])
        result = infer_entities([p1, p2])
        assert len(result) == 2

    def test_empty_pages(self):
        result = infer_entities([])
        assert result == []


# ---------------------------------------------------------------------------
# load_pages_from_dir
# ---------------------------------------------------------------------------


class TestLoadPagesFromDir:
    def _write_page(self, tmp_path: Path, filename: str, url: str) -> None:
        data = {
            "url": url,
            "meta": {"title": "Test"},
            "tables": [],
            "forms": [],
            "text_blocks": [],
        }
        (tmp_path / filename).write_text(json.dumps(data), encoding="utf-8")

    def test_loads_page_json_files(self, tmp_path: Path):
        self._write_page(tmp_path, "page-001.json", "https://example.com/a")
        self._write_page(tmp_path, "page-002.json", "https://example.com/b")
        pages = load_pages_from_dir(tmp_path)
        assert len(pages) == 2

    def test_ignores_non_page_files(self, tmp_path: Path):
        self._write_page(tmp_path, "page-001.json", "https://example.com/a")
        (tmp_path / "summary.json").write_text("{}", encoding="utf-8")
        pages = load_pages_from_dir(tmp_path)
        assert len(pages) == 1

    def test_returns_page_data_instances(self, tmp_path: Path):
        self._write_page(tmp_path, "page-001.json", "https://example.com/")
        pages = load_pages_from_dir(tmp_path)
        assert isinstance(pages[0], PageData)

    def test_empty_directory(self, tmp_path: Path):
        pages = load_pages_from_dir(tmp_path)
        assert pages == []

    def test_files_loaded_in_sorted_order(self, tmp_path: Path):
        self._write_page(tmp_path, "page-003.json", "https://example.com/c")
        self._write_page(tmp_path, "page-001.json", "https://example.com/a")
        self._write_page(tmp_path, "page-002.json", "https://example.com/b")
        pages = load_pages_from_dir(tmp_path)
        urls = [str(p.url) for p in pages]
        assert urls == [
            "https://example.com/a",
            "https://example.com/b",
            "https://example.com/c",
        ]
