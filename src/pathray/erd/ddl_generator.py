"""SQL DDL generator for ERD entities and relationships."""

from pathlib import Path

from pathray.models.erd import Entity, EntityField, Relationship

_TYPE_MAP: dict[str, str] = {
    "string": "VARCHAR(255)",
    "str": "VARCHAR(255)",
    "text": "TEXT",
    "int": "INTEGER",
    "integer": "INTEGER",
    "float": "NUMERIC",
    "number": "NUMERIC",
    "bool": "BOOLEAN",
    "boolean": "BOOLEAN",
    "date": "DATE",
    "datetime": "TIMESTAMP",
    "timestamp": "TIMESTAMP",
}


def _map_type(field_type: str) -> str:
    return _TYPE_MAP.get(field_type.lower(), "TEXT")


def _field_ddl(field: EntityField) -> str:
    col_type = _map_type(field.field_type)
    parts = [f'    "{field.name}" {col_type}']
    if field.is_primary:
        parts.append("PRIMARY KEY")
    elif not field.nullable:
        parts.append("NOT NULL")
    return " ".join(parts)


def _fk_constraint(rel: Relationship, from_table: str) -> str:
    ref_col = f"{rel.to_entity.lower()}_id"
    return (
        f'    FOREIGN KEY ("{ref_col}") '
        f'REFERENCES "{rel.to_entity}" ("id")'
    )


def _has_fk_col(entity: Entity, to_entity: str) -> bool:
    ref_col = f"{to_entity.lower()}_id"
    return any(f.name == ref_col for f in entity.fields)


def generate_ddl(entities: list[Entity], relationships: list[Relationship]) -> str:
    """Generate PostgreSQL-compatible CREATE TABLE DDL statements.

    Args:
        entities: List of Entity objects to generate tables for.
        relationships: List of Relationship objects for FOREIGN KEY constraints.

    Returns:
        SQL DDL string with CREATE TABLE statements.
    """
    statements: list[str] = []

    entity_names = {e.name for e in entities}

    for entity in entities:
        col_lines = [_field_ddl(f) for f in entity.fields]

        fk_lines: list[str] = []
        for rel in relationships:
            if rel.from_entity == entity.name and rel.to_entity in entity_names:
                if rel.relation_type in ("one-to-many", "many-to-one", "one-to-one"):
                    if _has_fk_col(entity, rel.to_entity):
                        fk_lines.append(_fk_constraint(rel, entity.name))

        all_lines = col_lines + fk_lines
        body = ",\n".join(all_lines)
        stmt = f'CREATE TABLE "{entity.name}" (\n{body}\n);'
        statements.append(stmt)

    return "\n\n".join(statements)


def ddl_to_string(entities: list[Entity], relationships: list[Relationship]) -> str:
    """Return DDL as a string."""
    return generate_ddl(entities, relationships)


def ddl_to_file(
    entities: list[Entity],
    relationships: list[Relationship],
    output_path: str | Path,
) -> Path:
    """Write DDL to a .sql file and return the path.

    Args:
        entities: List of Entity objects.
        relationships: List of Relationship objects.
        output_path: Destination file path (created if not exists).

    Returns:
        Path to the written file.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ddl = generate_ddl(entities, relationships)
    path.write_text(ddl, encoding="utf-8")
    return path
