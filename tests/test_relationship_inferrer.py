"""Tests for relationship_inferrer module."""

import pytest

from pathray.erd.relationship_inferrer import (
    _entity_name_from_fk,
    _find_entity,
    _is_junction_table,
    _is_one_to_one,
    infer_relationships,
)
from pathray.models.erd import Entity, EntityField, Relationship


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entity(name: str, fields: list[tuple[str, str, bool, bool]]) -> Entity:
    """Build an Entity from (name, field_type, nullable, is_primary) tuples."""
    return Entity(
        name=name,
        fields=[
            EntityField(name=n, field_type=ft, nullable=nl, is_primary=pk)
            for n, ft, nl, pk in fields
        ],
    )


def _simple(name: str, *field_names: str) -> Entity:
    """Build an Entity where all fields are TEXT, nullable, non-PK."""
    return Entity(
        name=name,
        fields=[EntityField(name=n, field_type="TEXT") for n in field_names],
    )


# ---------------------------------------------------------------------------
# _entity_name_from_fk
# ---------------------------------------------------------------------------


class TestEntityNameFromFk:
    def test_user_id(self):
        assert _entity_name_from_fk("user_id") == "User"

    def test_author_id(self):
        assert _entity_name_from_fk("author_id") == "Author"

    def test_compound_fk(self):
        assert _entity_name_from_fk("blog_post_id") == "BlogPost"

    def test_no_id_suffix_returns_none(self):
        assert _entity_name_from_fk("username") is None

    def test_bare_id_returns_none(self):
        # "id" alone doesn't end with "_id"
        assert _entity_name_from_fk("id") is None

    def test_parent_id(self):
        assert _entity_name_from_fk("parent_id") == "Parent"


# ---------------------------------------------------------------------------
# _find_entity
# ---------------------------------------------------------------------------


class TestFindEntity:
    def _entities(self) -> list[Entity]:
        return [_simple("User"), _simple("Post"), _simple("Comment")]

    def test_exact_match(self):
        assert _find_entity("User", self._entities()) == "User"

    def test_case_insensitive(self):
        assert _find_entity("user", self._entities()) == "User"
        assert _find_entity("USER", self._entities()) == "User"

    def test_no_match_returns_none(self):
        assert _find_entity("Product", self._entities()) is None

    def test_empty_list_returns_none(self):
        assert _find_entity("User", []) is None


# ---------------------------------------------------------------------------
# _is_junction_table
# ---------------------------------------------------------------------------


class TestIsJunctionTable:
    def test_two_fk_no_extra_fields(self):
        entity = _simple("UserPost", "id", "user_id", "post_id")
        # id is PK-ish but not marked here; let's use the helper with is_primary
        entity2 = Entity(
            name="UserPost",
            fields=[
                EntityField(name="id", field_type="INTEGER", is_primary=True),
                EntityField(name="user_id", field_type="INTEGER"),
                EntityField(name="post_id", field_type="INTEGER"),
            ],
        )
        assert _is_junction_table(entity2, ["user_id", "post_id"]) is True

    def test_two_fk_with_extra_fields_still_junction(self):
        entity = Entity(
            name="UserPost",
            fields=[
                EntityField(name="user_id", field_type="INTEGER"),
                EntityField(name="post_id", field_type="INTEGER"),
                EntityField(name="role", field_type="TEXT"),
            ],
        )
        # 1 non-FK non-PK field → still ≤ 2 → junction
        assert _is_junction_table(entity, ["user_id", "post_id"]) is True

    def test_two_fk_too_many_extra_fields(self):
        entity = Entity(
            name="Post",
            fields=[
                EntityField(name="user_id", field_type="INTEGER"),
                EntityField(name="category_id", field_type="INTEGER"),
                EntityField(name="title", field_type="TEXT"),
                EntityField(name="body", field_type="TEXT"),
                EntityField(name="published_at", field_type="DATE"),
            ],
        )
        # 3 non-FK non-PK fields → not a junction
        assert _is_junction_table(entity, ["user_id", "category_id"]) is False

    def test_one_fk_not_junction(self):
        entity = _simple("Post", "id", "user_id", "title")
        assert _is_junction_table(entity, ["user_id"]) is False


# ---------------------------------------------------------------------------
# _is_one_to_one
# ---------------------------------------------------------------------------


class TestIsOneToOne:
    def test_entity_starts_with_referenced(self):
        entity = _simple("UserProfile", "id", "user_id")
        assert _is_one_to_one(entity, "User", 1) is True

    def test_entity_ends_with_referenced(self):
        entity = _simple("AdminUser", "id", "user_id")
        assert _is_one_to_one(entity, "User", 1) is True

    def test_entity_contains_referenced(self):
        entity = _simple("UserSettings", "id", "user_id")
        assert _is_one_to_one(entity, "User", 1) is True

    def test_unrelated_name_not_one_to_one(self):
        entity = _simple("Post", "id", "user_id")
        assert _is_one_to_one(entity, "User", 1) is False

    def test_multiple_fks_not_one_to_one(self):
        entity = _simple("UserProfile", "id", "user_id", "role_id")
        assert _is_one_to_one(entity, "User", 2) is False


# ---------------------------------------------------------------------------
# infer_relationships
# ---------------------------------------------------------------------------


class TestInferRelationships:
    def test_basic_one_to_many(self):
        user = _simple("User", "id", "name")
        post = _simple("Post", "id", "title", "user_id")
        rels = infer_relationships([user, post])
        assert len(rels) == 1
        rel = rels[0]
        assert rel.from_entity == "User"
        assert rel.to_entity == "Post"
        assert rel.relation_type == "one-to-many"
        assert rel.label == "user_id"

    def test_no_fk_fields_no_relationships(self):
        user = _simple("User", "id", "name")
        product = _simple("Product", "id", "sku", "price")
        rels = infer_relationships([user, product])
        assert rels == []

    def test_fk_to_nonexistent_entity_ignored(self):
        post = _simple("Post", "id", "title", "author_id")
        # No Author entity present
        rels = infer_relationships([post])
        assert rels == []

    def test_self_referential(self):
        # category_id → "Category" matches the entity itself → self-referential
        category = _simple("Category", "id", "name", "category_id")
        rels = infer_relationships([category])
        assert len(rels) == 1
        rel = rels[0]
        assert rel.from_entity == "Category"
        assert rel.to_entity == "Category"
        assert rel.relation_type == "one-to-many"
        assert rel.label == "category_id"

    def test_many_to_many_junction(self):
        user = _simple("User", "id", "name")
        post = _simple("Post", "id", "title")
        junction = Entity(
            name="UserPost",
            fields=[
                EntityField(name="id", field_type="INTEGER", is_primary=True),
                EntityField(name="user_id", field_type="INTEGER"),
                EntityField(name="post_id", field_type="INTEGER"),
            ],
        )
        rels = infer_relationships([user, post, junction])
        assert len(rels) == 1
        rel = rels[0]
        assert rel.relation_type == "many-to-many"
        assert {rel.from_entity, rel.to_entity} == {"User", "Post"}
        assert rel.label == "UserPost"

    def test_one_to_one(self):
        user = _simple("User", "id", "name")
        profile = _simple("UserProfile", "id", "user_id", "bio")
        rels = infer_relationships([user, profile])
        assert len(rels) == 1
        assert rels[0].relation_type == "one-to-one"
        assert rels[0].from_entity == "User"
        assert rels[0].to_entity == "UserProfile"

    def test_multiple_fk_fields(self):
        user = _simple("User", "id", "name")
        category = _simple("Category", "id", "name")
        post = Entity(
            name="Post",
            fields=[
                EntityField(name="id", field_type="INTEGER", is_primary=True),
                EntityField(name="title", field_type="TEXT"),
                EntityField(name="body", field_type="TEXT"),
                EntityField(name="user_id", field_type="INTEGER"),
                EntityField(name="category_id", field_type="INTEGER"),
            ],
        )
        rels = infer_relationships([user, category, post])
        # Post has 2 FKs and 2 non-PK non-FK fields (title, body) → not junction
        assert len(rels) == 2
        rel_map = {r.label: r for r in rels}
        assert rel_map["user_id"].from_entity == "User"
        assert rel_map["category_id"].from_entity == "Category"

    def test_empty_entities(self):
        assert infer_relationships([]) == []

    def test_independent_entity_handled_gracefully(self):
        user = _simple("User", "id", "name", "email")
        # No FKs anywhere
        rels = infer_relationships([user])
        assert rels == []

    def test_compound_fk_name(self):
        blog_post = _simple("BlogPost", "id", "title")
        comment = _simple("Comment", "id", "body", "blog_post_id")
        rels = infer_relationships([blog_post, comment])
        assert len(rels) == 1
        assert rels[0].from_entity == "BlogPost"
        assert rels[0].to_entity == "Comment"
