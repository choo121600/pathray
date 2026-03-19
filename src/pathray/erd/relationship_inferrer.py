"""Relationship inference from entity field patterns."""

import re

from pathray.models.erd import Entity, Relationship


def _entity_name_from_fk(field_name: str) -> str | None:
    """Derive referenced entity name from a FK field (e.g. user_id → User)."""
    if not field_name.endswith("_id"):
        return None
    base = field_name[:-3]  # strip trailing _id
    return "".join(word.capitalize() for word in re.split(r"_", base) if word)


def _find_entity(name: str, entities: list[Entity]) -> str | None:
    """Return the canonical entity name matching *name* (case-insensitive)."""
    name_lower = name.lower()
    for entity in entities:
        if entity.name.lower() == name_lower:
            return entity.name
    return None


def _is_junction_table(entity: Entity, fk_field_names: list[str]) -> bool:
    """Return True when the entity looks like a junction/pivot table.

    Heuristic: has ≥ 2 FK fields and at most 2 non-PK, non-FK fields.
    """
    non_fk_fields = [
        f for f in entity.fields
        if f.name not in fk_field_names and not f.is_primary
    ]
    return len(fk_field_names) >= 2 and len(non_fk_fields) <= 1


def _is_one_to_one(entity: Entity, referenced_name: str, fk_count: int) -> bool:
    """Return True when a 1:1 relationship is likely.

    Heuristic: entity has only one FK, and the entity name contains or
    starts with the referenced entity name (e.g. UserProfile → User).
    """
    if fk_count != 1:
        return False
    e_lower = entity.name.lower()
    r_lower = referenced_name.lower()
    return e_lower.startswith(r_lower) or e_lower.endswith(r_lower)


def infer_relationships(entities: list[Entity]) -> list[Relationship]:
    """Infer relationships between entities based on FK field naming conventions.

    Detection rules:
    - Fields ending in ``_id`` (e.g. ``user_id``) are treated as foreign keys.
    - The derived entity name must match an existing entity (case-insensitive).
    - Self-referential FKs (e.g. ``parent_id`` on the same entity) produce a
      one-to-many relationship from the entity to itself.
    - If an entity has ≥ 2 FKs to distinct entities AND looks like a junction
      table (≤ 2 non-PK/non-FK fields), a many-to-many relationship is created
      between the two referenced entities.
    - A 1:1 relationship is inferred when the entity has exactly one FK and its
      name is a compound of the referenced entity name (e.g. UserProfile → User).
    - All other cases produce a one-to-many relationship where the referenced
      entity is the "one" side and the FK-holding entity is the "many" side.
    """
    relationships: list[Relationship] = []

    for entity in entities:
        # Map FK field name → resolved (canonical) entity name
        fk_map: dict[str, str] = {}
        for field in entity.fields:
            ref_name = _entity_name_from_fk(field.name)
            if ref_name is None:
                continue
            matched = _find_entity(ref_name, entities)
            if matched is None:
                continue
            fk_map[field.name] = matched

        if not fk_map:
            continue

        fk_field_names = list(fk_map.keys())
        # Unique referenced entities preserving insertion order
        referenced_entities = list(dict.fromkeys(fk_map.values()))

        # N:M junction table heuristic
        if _is_junction_table(entity, fk_field_names) and len(referenced_entities) >= 2:
            relationships.append(
                Relationship(
                    from_entity=referenced_entities[0],
                    to_entity=referenced_entities[1],
                    relation_type="many-to-many",
                    label=entity.name,
                )
            )
            continue

        # Individual FK → relationship
        for field_name, referenced in fk_map.items():
            # Self-referential
            if referenced == entity.name:
                relationships.append(
                    Relationship(
                        from_entity=entity.name,
                        to_entity=entity.name,
                        relation_type="one-to-many",
                        label=field_name,
                    )
                )
                continue

            # 1:1 heuristic
            if _is_one_to_one(entity, referenced, len(fk_map)):
                rel_type = "one-to-one"
            else:
                rel_type = "one-to-many"

            relationships.append(
                Relationship(
                    from_entity=referenced,
                    to_entity=entity.name,
                    relation_type=rel_type,
                    label=field_name,
                )
            )

    return relationships
