"""Entity inference from page data."""

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

from pathray.models.erd import Entity, EntityField
from pathray.models.page_data import FormField, PageData, TableData

_SKIP_WEB_TERMS = frozenset(
    {"edit", "new", "create", "show", "index", "list", "view", "add", "update", "delete"}
)

_TYPE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"email", re.IGNORECASE), "VARCHAR"),
    (re.compile(r"date|time|created_at|updated_at", re.IGNORECASE), "DATE"),
    (re.compile(r"phone|tel", re.IGNORECASE), "VARCHAR"),
    (re.compile(r"url|link|href|website", re.IGNORECASE), "VARCHAR"),
    (re.compile(r"bool|active|enabled|is_", re.IGNORECASE), "BOOLEAN"),
    (re.compile(r"number|count|qty|quantity|amount|price|age|total|score", re.IGNORECASE), "INTEGER"),
]

_FORM_TYPE_MAP: dict[str, str] = {
    "email": "VARCHAR",
    "url": "VARCHAR",
    "tel": "VARCHAR",
    "number": "INTEGER",
    "range": "INTEGER",
    "checkbox": "BOOLEAN",
    "radio": "BOOLEAN",
    "date": "DATE",
    "datetime": "DATE",
    "datetime-local": "DATE",
    "time": "DATE",
    "month": "DATE",
    "week": "DATE",
}

_SKIP_FORM_TYPES = frozenset({"submit", "button", "reset", "image", "hidden", "file"})


def _infer_field_type(name: str, form_field_type: str | None = None) -> str:
    """Infer SQL field type from field name and optional HTML form input type."""
    for pattern, sql_type in _TYPE_PATTERNS:
        if pattern.search(name):
            return sql_type
    if form_field_type:
        if form_field_type in _FORM_TYPE_MAP:
            return _FORM_TYPE_MAP[form_field_type]
    return "TEXT"


def _infer_entity_name_from_url(url: str) -> str | None:
    """Extract a PascalCase entity name from a URL path segment."""
    try:
        path = url.split("?")[0].rstrip("/")
        # Drop scheme + host
        if "://" in path:
            path = path.split("://", 1)[1]
            if "/" in path:
                path = path[path.index("/"):]
            else:
                return None
        segments = [s for s in path.split("/") if s]
        for seg in reversed(segments):
            seg_clean = seg.split(".")[0].lower()
            if seg_clean.isdigit() or seg_clean in _SKIP_WEB_TERMS:
                continue
            words = re.split(r"[-_]", seg_clean)
            return "".join(w.capitalize() for w in words if w)
    except Exception:
        logger.debug("Failed to infer entity name from URL: %s", url)
    return None


def _fields_from_table(table: TableData) -> list[EntityField]:
    """Infer EntityFields from a TableData (headers → field names)."""
    fields: list[EntityField] = []
    for i, header in enumerate(table.headers):
        header = header.strip()
        if not header:
            continue
        name = re.sub(r"\s+", "_", header.lower())
        name = re.sub(r"[^\w]", "", name)
        if not name:
            continue
        is_primary = name in ("id", "pk", "key")
        field_type = _infer_field_type(name)
        fields.append(
            EntityField(
                name=name,
                field_type=field_type,
                nullable=not is_primary,
                is_primary=is_primary,
            )
        )
    return fields


def _fields_from_form(form_fields: list[FormField]) -> list[EntityField]:
    """Infer EntityFields from HTML form fields."""
    fields: list[EntityField] = []
    seen: set[str] = set()
    for ff in form_fields:
        if not ff.name or ff.name in seen:
            continue
        if ff.field_type in _SKIP_FORM_TYPES:
            continue
        seen.add(ff.name)
        is_primary = ff.name in ("id", "pk")
        field_type = _infer_field_type(ff.name, ff.field_type)
        fields.append(
            EntityField(
                name=ff.name,
                field_type=field_type,
                nullable=not ff.required,
                is_primary=is_primary,
            )
        )
    return fields


def _jaccard(set_a: set[str], set_b: set[str]) -> float:
    """Compute Jaccard similarity between two sets of strings."""
    if not set_a and not set_b:
        return 1.0
    union = len(set_a | set_b)
    return len(set_a & set_b) / union if union else 0.0


def _merge_entities(entities: list[Entity]) -> list[Entity]:
    """Merge entities with Jaccard field-name similarity >= 0.6."""
    if not entities:
        return []
    merged = list(entities)
    changed = True
    while changed:
        changed = False
        result: list[Entity] = []
        used: set[int] = set()
        for i, base in enumerate(merged):
            if i in used:
                continue
            current = base
            for j in range(i + 1, len(merged)):
                if j in used:
                    continue
                names_cur = {f.name for f in current.fields}
                names_other = {f.name for f in merged[j].fields}
                if _jaccard(names_cur, names_other) >= 0.6:
                    existing = {f.name for f in current.fields}
                    extra = [f for f in merged[j].fields if f.name not in existing]
                    current = Entity(
                        name=current.name,
                        fields=list(current.fields) + extra,
                        source_url=current.source_url,
                    )
                    used.add(j)
                    changed = True
            result.append(current)
        merged = result
    return merged


def _base_name_from_page(page: PageData) -> str:
    """Derive a PascalCase entity base name from page title or URL."""
    if page.meta.title:
        title = page.meta.title.strip()
        # Strip common suffixes like " | App Name"
        title = re.split(r"\s*[|\-—]\s*", title)[0].strip()
        words = re.split(r"[\s_\-]+", title)
        name = "".join(w.capitalize() for w in words if w.isalnum() or re.match(r"\w", w))
        if name:
            return name
    return _infer_entity_name_from_url(str(page.url)) or "Unknown"


def infer_entities_from_page(page: PageData) -> list[Entity]:
    """Infer entities from a single PageData instance."""
    url_str = str(page.url)
    base = _base_name_from_page(page)
    entities: list[Entity] = []

    for i, table in enumerate(page.tables):
        fields = _fields_from_table(table)
        if not fields:
            continue
        name = base if len(page.tables) == 1 else f"{base}Table{i + 1}"
        entities.append(Entity(name=name, fields=fields, source_url=url_str))

    for i, form in enumerate(page.forms):
        fields = _fields_from_form(form.fields)
        if not fields:
            continue
        name = base if len(page.forms) == 1 else f"{base}Form{i + 1}"
        entities.append(Entity(name=name, fields=fields, source_url=url_str))

    return entities


def infer_entities(pages: list[PageData]) -> list[Entity]:
    """Infer and merge entities across multiple pages."""
    all_entities: list[Entity] = []
    for page in pages:
        all_entities.extend(infer_entities_from_page(page))
    return _merge_entities(all_entities)


def load_pages_from_dir(directory: str | Path) -> list[PageData]:
    """Load page-*.json files from a directory into PageData objects."""
    dir_path = Path(directory)
    pages: list[PageData] = []
    for json_file in sorted(dir_path.glob("page-*.json")):
        with json_file.open(encoding="utf-8") as f:
            data = json.load(f)
        pages.append(PageData.model_validate(data))
    return pages
