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


def _esc(identifier: str) -> str:
    """Escape double quotes in SQL identifiers."""
    return identifier.replace('"', '""')


def _field_ddl(field: EntityField) -> str:
    col_type = _map_type(field.field_type)
    parts = [f'    "{_esc(field.name)}" {col_type}']
    if field.is_primary:
        parts.append("PRIMARY KEY")
    elif not field.nullable:
        parts.append("NOT NULL")
    return " ".join(parts)


def _fk_constraint(fk_col: str, referenced_entity: str) -> str:
    return (
        f'    FOREIGN KEY ("{_esc(fk_col)}") '
        f'REFERENCES "{_esc(referenced_entity)}" ("id")'
    )


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
        entity_field_names = {f.name for f in entity.fields}
        for rel in relationships:
            if rel.relation_type == "many-to-many":
                continue
            # Determine FK column and referenced entity.
            # The entity holding the FK column could be either side
            # depending on how the Relationship was constructed.
            if rel.from_entity == entity.name and rel.to_entity == entity.name:
                # Self-referential
                fk_col = rel.label if rel.label else f"{entity.name.lower()}_id"
                referenced = entity.name
            elif rel.to_entity == entity.name and rel.from_entity != entity.name:
                # Inferrer convention: from=referenced, to=FK holder
                fk_col = (
                    rel.label if rel.label
                    else f"{rel.from_entity.lower()}_id"
                )
                referenced = rel.from_entity
            elif rel.from_entity == entity.name and rel.to_entity != entity.name:
                # Alternate convention: from=FK holder, to=referenced
                fk_col = (
                    rel.label if rel.label
                    else f"{rel.to_entity.lower()}_id"
                )
                referenced = rel.to_entity
            else:
                continue
            if fk_col not in entity_field_names:
                continue
            if referenced in entity_names:
                fk_lines.append(_fk_constraint(fk_col, referenced))

        all_lines = col_lines + fk_lines
        body = ",\n".join(all_lines)
        stmt = f'CREATE TABLE "{_esc(entity.name)}" (\n{body}\n);'
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
