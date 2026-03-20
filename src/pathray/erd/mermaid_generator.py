"""Mermaid ERD diagram generator for pathray."""

import re
from pathlib import Path

from pathray.models.erd import Entity, Relationship


def _sanitize_name(name: str) -> tuple[str, str | None]:
    """Sanitize a name for Mermaid ATTRIBUTE_WORD compatibility.

    Returns (sanitized_name, original_or_none).
    If the name is already ASCII-safe, original is None.
    """
    ascii_name = re.sub(r"[^\x00-\x7F]", "_", name)
    ascii_name = re.sub(r"_+", "_", ascii_name).strip("_")
    if not ascii_name or not re.match(r"[A-Za-z_]", ascii_name):
        ascii_name = "f_" + ascii_name
    changed = ascii_name != name
    return ascii_name, (name if changed else None)


def _sanitize_entity_name(name: str) -> str:
    """Sanitize entity name — quote if it contains non-ASCII."""
    if re.search(r"[^\x00-\x7F]", name):
        escaped = name.replace('"', '\\"')
        return f'"{escaped}"'
    return name

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
        safe_entity = _sanitize_entity_name(entity.name)
        lines.append(f"    {safe_entity} {{")
        for field in entity.fields:
            markers = ""
            if field.is_primary:
                markers += " PK"
            if field.name.endswith("_id") and not field.is_primary:
                markers += " FK"
            safe_name, original = _sanitize_name(field.name)
            comment = f' "{original}"' if original else ""
            line = f"        {field.field_type} {safe_name}{markers}{comment}"
            lines.append(line)
        lines.append("    }")

    for rel in relationships:
        left, right = _CARDINALITY_MAP.get(
            rel.relation_type, ("||", "o{")
        )
        label = rel.label if rel.label else rel.relation_type
        safe_from = _sanitize_entity_name(rel.from_entity)
        safe_to = _sanitize_entity_name(rel.to_entity)
        lines.append(
            f'    {safe_from} {left}--{right} {safe_to} : "{label}"'
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
