"""ERD generation modules."""

from pathray.erd.ddl_generator import ddl_to_file, ddl_to_string, generate_ddl
from pathray.erd.entity_inferrer import (
    infer_entities,
    infer_entities_from_page,
    load_pages_from_dir,
)
from pathray.erd.image_renderer import render_images
from pathray.erd.mermaid_generator import generate_mermaid, save_mermaid
from pathray.erd.relationship_inferrer import infer_relationships

__all__ = [
    "ddl_to_file",
    "ddl_to_string",
    "generate_ddl",
    "generate_mermaid",
    "infer_entities",
    "infer_entities_from_page",
    "infer_relationships",
    "load_pages_from_dir",
    "render_images",
    "save_mermaid",
]
