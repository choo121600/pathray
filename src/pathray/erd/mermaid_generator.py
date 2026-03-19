"""Mermaid ERD diagram generator for pathray."""

from pathlib import Path

from pathray.models.erd import Entity, Relationship

_CARDINALITY_MAP = {
    "one-to-many": ("||", "o{"),
    "many-to-one": ("}o", "||"),
    "one-to-one": ("||", "||"),
    "many-to-many": ("}o", "o{"),
}


def generate_mermaid(
    entities: list[Entity],
    relationships: list[Relationship],
) -> str:
    """Generate Mermaid erDiagram syntax from entities and relationships.

    Args:
        entities: List of Entity objects to render.
        relationships: List of Relationship objects to render.

    Returns:
        Mermaid erDiagram string.
    """
    lines: list[str] = ["erDiagram"]

    for entity in entities:
        lines.append(f"    {entity.name} {{")
        for field in entity.fields:
            markers = ""
            if field.is_primary:
                markers += " PK"
            if field.name.endswith("_id") and not field.is_primary:
                markers += " FK"
            line = f"        {field.field_type} {field.name}{markers}"
            lines.append(line)
        lines.append("    }")

    for rel in relationships:
        left, right = _CARDINALITY_MAP.get(
            rel.relation_type, ("||", "o{")
        )
        label = rel.label if rel.label else rel.relation_type
        lines.append(
            f'    {rel.from_entity} {left}--{right} {rel.to_entity} : "{label}"'
        )

    return "\n".join(lines) + "\n"


def save_mermaid(
    entities: list[Entity],
    relationships: list[Relationship],
    output_path: str | Path,
) -> Path:
    """Generate Mermaid ERD and write to a .mmd file.

    Args:
        entities: List of Entity objects.
        relationships: List of Relationship objects.
        output_path: Destination file path (e.g. output/erd.mmd).

    Returns:
        Path of the written file.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = generate_mermaid(entities, relationships)
    path.write_text(content, encoding="utf-8")
    return path
