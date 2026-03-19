"""Tests for mermaid_generator module."""

from pathlib import Path

import pytest

from pathray.erd.mermaid_generator import generate_mermaid, save_mermaid
from pathray.models.erd import Entity, EntityField, Relationship


@pytest.fixture
def user_entity() -> Entity:
    return Entity(
        name="User",
        fields=[
            EntityField(name="id", field_type="integer", is_primary=True, nullable=False),
            EntityField(name="email", field_type="string"),
            EntityField(name="name", field_type="string"),
        ],
        source_url="https://example.com/users",
    )


@pytest.fixture
def order_entity() -> Entity:
    return Entity(
        name="Order",
        fields=[
            EntityField(name="id", field_type="integer", is_primary=True, nullable=False),
            EntityField(name="user_id", field_type="integer", nullable=False),
            EntityField(name="total", field_type="float"),
        ],
    )


@pytest.fixture
def one_to_many_rel() -> Relationship:
    return Relationship(
        from_entity="User",
        to_entity="Order",
        relation_type="one-to-many",
        label="places",
    )


def test_generate_starts_with_erdiagram(user_entity):
    result = generate_mermaid([user_entity], [])
    assert result.startswith("erDiagram")


def test_generate_entity_block(user_entity):
    result = generate_mermaid([user_entity], [])
    assert "User {" in result
    assert "integer id PK" in result
    assert "string email" in result


def test_generate_multiple_entities(user_entity, order_entity):
    result = generate_mermaid([user_entity, order_entity], [])
    assert "User {" in result
    assert "Order {" in result


def test_generate_one_to_many_relationship(user_entity, order_entity, one_to_many_rel):
    result = generate_mermaid([user_entity, order_entity], [one_to_many_rel])
    assert 'User ||--o{ Order : "places"' in result


def test_generate_one_to_one_relationship(user_entity, order_entity):
    rel = Relationship(
        from_entity="User",
        to_entity="Order",
        relation_type="one-to-one",
        label="has",
    )
    result = generate_mermaid([user_entity, order_entity], [rel])
    assert 'User ||--|| Order : "has"' in result


def test_generate_many_to_many_relationship(user_entity, order_entity):
    rel = Relationship(
        from_entity="User",
        to_entity="Order",
        relation_type="many-to-many",
    )
    result = generate_mermaid([user_entity, order_entity], [rel])
    assert "User }|--|{ Order" in result


def test_generate_many_to_one_relationship(user_entity, order_entity):
    rel = Relationship(
        from_entity="Order",
        to_entity="User",
        relation_type="many-to-one",
        label="belongs to",
    )
    result = generate_mermaid([user_entity, order_entity], [rel])
    assert 'Order }o--|| User : "belongs to"' in result


def test_relationship_label_defaults_to_relation_type(user_entity, order_entity):
    rel = Relationship(
        from_entity="User",
        to_entity="Order",
        relation_type="one-to-many",
    )
    result = generate_mermaid([user_entity, order_entity], [rel])
    assert '"one-to-many"' in result


def test_generate_empty_inputs():
    result = generate_mermaid([], [])
    assert result.strip() == "erDiagram"


def test_save_mermaid_creates_file(tmp_path, user_entity, order_entity, one_to_many_rel):
    output_file = tmp_path / "output" / "erd.mmd"
    result_path = save_mermaid([user_entity, order_entity], [one_to_many_rel], output_file)
    assert result_path == output_file
    assert output_file.exists()
    content = output_file.read_text(encoding="utf-8")
    assert "erDiagram" in content
    assert "User {" in content


def test_save_mermaid_returns_path(tmp_path, user_entity):
    output_file = tmp_path / "erd.mmd"
    result = save_mermaid([user_entity], [], output_file)
    assert isinstance(result, Path)
    assert result == output_file


def test_save_mermaid_creates_parent_dirs(tmp_path, user_entity):
    deep_path = tmp_path / "a" / "b" / "c" / "erd.mmd"
    save_mermaid([user_entity], [], deep_path)
    assert deep_path.exists()
