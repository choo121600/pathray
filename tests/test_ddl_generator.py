"""Tests for SQL DDL generator."""

import tempfile
from pathlib import Path

import pytest

from pathray.erd.ddl_generator import ddl_to_file, ddl_to_string, generate_ddl
from pathray.models.erd import Entity, EntityField, Relationship


@pytest.fixture()
def simple_entity() -> Entity:
    return Entity(
        name="User",
        fields=[
            EntityField(name="id", field_type="integer", nullable=False, is_primary=True),
            EntityField(name="name", field_type="string", nullable=False),
            EntityField(name="email", field_type="string", nullable=True),
        ],
    )


@pytest.fixture()
def post_entity() -> Entity:
    return Entity(
        name="Post",
        fields=[
            EntityField(name="id", field_type="integer", nullable=False, is_primary=True),
            EntityField(name="title", field_type="string", nullable=False),
            EntityField(name="body", field_type="text", nullable=True),
            EntityField(name="user_id", field_type="integer", nullable=False),
        ],
    )


def test_generate_ddl_creates_table(simple_entity: Entity) -> None:
    ddl = generate_ddl([simple_entity], [])
    assert 'CREATE TABLE "User"' in ddl


def test_primary_key_column(simple_entity: Entity) -> None:
    ddl = generate_ddl([simple_entity], [])
    assert '"id" INTEGER PRIMARY KEY' in ddl


def test_not_null_column(simple_entity: Entity) -> None:
    ddl = generate_ddl([simple_entity], [])
    assert '"name" VARCHAR(255) NOT NULL' in ddl


def test_nullable_column_no_constraint(simple_entity: Entity) -> None:
    ddl = generate_ddl([simple_entity], [])
    assert '"email" VARCHAR(255)' in ddl
    assert '"email" VARCHAR(255) NOT NULL' not in ddl


def test_type_mapping_text() -> None:
    entity = Entity(
        name="Article",
        fields=[EntityField(name="content", field_type="text", nullable=True)],
    )
    ddl = generate_ddl([entity], [])
    assert '"content" TEXT' in ddl


def test_type_mapping_boolean() -> None:
    entity = Entity(
        name="Flag",
        fields=[EntityField(name="active", field_type="boolean", nullable=False)],
    )
    ddl = generate_ddl([entity], [])
    assert '"active" BOOLEAN NOT NULL' in ddl


def test_type_mapping_date() -> None:
    entity = Entity(
        name="Event",
        fields=[EntityField(name="created_at", field_type="date", nullable=True)],
    )
    ddl = generate_ddl([entity], [])
    assert '"created_at" DATE' in ddl


def test_type_mapping_unknown_defaults_to_text() -> None:
    entity = Entity(
        name="Thing",
        fields=[EntityField(name="data", field_type="json", nullable=True)],
    )
    ddl = generate_ddl([entity], [])
    assert '"data" TEXT' in ddl


def test_multiple_entities(simple_entity: Entity, post_entity: Entity) -> None:
    ddl = generate_ddl([simple_entity, post_entity], [])
    assert 'CREATE TABLE "User"' in ddl
    assert 'CREATE TABLE "Post"' in ddl


def test_foreign_key_constraint(simple_entity: Entity, post_entity: Entity) -> None:
    rel = Relationship(from_entity="Post", to_entity="User", relation_type="one-to-many")
    ddl = generate_ddl([simple_entity, post_entity], [rel])
    assert 'FOREIGN KEY ("user_id") REFERENCES "User" ("id")' in ddl


def test_no_fk_when_column_missing(simple_entity: Entity) -> None:
    """FK constraint not added if the FK column doesn't exist in the entity."""
    entity_no_fk_col = Entity(
        name="Comment",
        fields=[
            EntityField(name="id", field_type="integer", nullable=False, is_primary=True),
            EntityField(name="body", field_type="text", nullable=True),
        ],
    )
    rel = Relationship(
        from_entity="Comment", to_entity="Post", relation_type="one-to-many"
    )
    ddl = generate_ddl([simple_entity, entity_no_fk_col], [rel])
    assert "FOREIGN KEY" not in ddl


def test_ddl_to_string(simple_entity: Entity) -> None:
    result = ddl_to_string([simple_entity], [])
    assert isinstance(result, str)
    assert 'CREATE TABLE "User"' in result


def test_ddl_to_file(simple_entity: Entity) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "schema.sql"
        path = ddl_to_file([simple_entity], [], out)
        assert path.exists()
        content = path.read_text()
        assert 'CREATE TABLE "User"' in content


def test_ddl_to_file_creates_parent_dirs(simple_entity: Entity) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "nested" / "dir" / "schema.sql"
        path = ddl_to_file([simple_entity], [], out)
        assert path.exists()


def test_empty_entities() -> None:
    ddl = generate_ddl([], [])
    assert ddl == ""
