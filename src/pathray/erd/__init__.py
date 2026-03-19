"""ERD generation modules."""

from pathray.erd.entity_inferrer import (
    infer_entities,
    infer_entities_from_page,
    load_pages_from_dir,
)
from pathray.erd.relationship_inferrer import infer_relationships

__all__ = [
    "infer_entities",
    "infer_entities_from_page",
    "infer_relationships",
    "load_pages_from_dir",
]
