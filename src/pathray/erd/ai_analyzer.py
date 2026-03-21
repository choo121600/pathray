"""AI-powered ERD analysis using the claude CLI subprocess."""

from __future__ import annotations

import json
import logging
import subprocess

from pathray.models.erd import Entity, EntityField, Relationship
from pathray.models.page_data import PageData

logger = logging.getLogger(__name__)

_SAMPLE_ROWS = 3


def prepare_pages_for_ai(pages: list[PageData]) -> list[dict]:
    """Condense a list of PageData objects into minimal dicts for AI analysis.

    Strips images, og_tags, text_blocks, and limits table rows to the first 3.
    Tables with no headers and forms with no fields are excluded.
    """
    result: list[dict] = []
    for page in pages:
        tables = []
        for table in page.tables:
            if not table.headers:
                continue
            tables.append({
                "caption": table.caption,
                "context_heading": table.context_heading,
                "headers": table.headers,
                "sample_rows": table.rows[:_SAMPLE_ROWS],
            })

        forms = []
        for form in page.forms:
            fields = [
                {
                    "name": ff.name,
                    "field_type": ff.field_type,
                    "label": ff.label,
                    "required": ff.required,
                }
                for ff in form.fields
            ]
            if not fields:
                continue
            forms.append({
                "action": form.action,
                "method": form.method,
                "fields": fields,
            })

        result.append({
            "url": str(page.url),
            "title": page.meta.title,
            "tables": tables,
            "forms": forms,
        })

    return result


def _build_prompt(condensed_pages: list[dict]) -> str:
    """Build a Korean-language prompt asking Claude to analyse page data and return JSON.

    The prompt instructs Claude to output ONLY valid JSON with no markdown fences.
    """
    pages_json = json.dumps(condensed_pages, ensure_ascii=False, indent=2)

    return f"""다음은 웹사이트에서 추출한 페이지 데이터입니다. 각 페이지의 테이블과 폼을 분석하여 데이터베이스 엔티티를 추론해 주세요.

페이지 데이터:
{pages_json}

분석 규칙:
1. 의미 있는 엔티티 이름을 PascalCase로 작성하세요.
2. 네비게이션, 푸터, 레이아웃용 테이블은 제외하세요.
3. 각 필드의 타입은 TEXT, INTEGER, BOOLEAN, DATE, TIMESTAMP, VARCHAR 중 하나로 지정하세요.
4. 엔티티 간 관계(외래키, 연관 관계)가 추론 가능하면 relationships에 포함하세요.
5. source_url과 source_title은 해당 엔티티가 발견된 페이지 정보를 사용하세요.

반드시 아래 JSON 형식으로만 응답하세요. 마크다운 코드 블록(```), 설명 텍스트 없이 순수 JSON만 출력하세요:

{{
  "entities": [
    {{
      "name": "EntityName",
      "fields": [
        {{"name": "field_name", "field_type": "TEXT", "nullable": true, "is_primary": false}}
      ],
      "source_url": "https://...",
      "source_title": "Page Title"
    }}
  ],
  "relationships": [
    {{"from_entity": "A", "to_entity": "B", "relation_type": "one-to-many", "label": "has"}}
  ]
}}"""


def analyze_with_ai(pages: list[PageData]) -> tuple[list[Entity], list[Relationship]]:
    """Analyze page data using the claude CLI and return entities and relationships.

    Falls back to heuristic inference if the claude CLI is unavailable or returns
    unparseable output.

    Args:
        pages: List of PageData objects to analyze.

    Returns:
        A tuple of (entities, relationships).
    """
    from pathray.erd.entity_inferrer import infer_entities
    from pathray.erd.relationship_inferrer import infer_relationships

    condensed_pages = prepare_pages_for_ai(pages)
    prompt = _build_prompt(condensed_pages)

    try:
        proc = subprocess.run(
            ["claude", "-p", prompt, "--output-format", "json"],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        logger.warning("claude CLI not found; falling back to heuristic inference.")
        return infer_entities(pages), infer_relationships(infer_entities(pages))
    except subprocess.TimeoutExpired:
        logger.warning("claude CLI timed out; falling back to heuristic inference.")
        return infer_entities(pages), infer_relationships(infer_entities(pages))
    except Exception as exc:  # noqa: BLE001
        logger.warning("claude CLI error (%s); falling back to heuristic inference.", exc)
        return infer_entities(pages), infer_relationships(infer_entities(pages))

    if proc.returncode != 0:
        logger.warning(
            "claude CLI exited with code %d; falling back to heuristic inference.\nstderr: %s",
            proc.returncode,
            proc.stderr,
        )
        return infer_entities(pages), infer_relationships(infer_entities(pages))

    # claude --output-format json wraps the response in {"result": "..."}
    raw_text = proc.stdout.strip()
    try:
        outer = json.loads(raw_text)
        result_text: str = outer.get("result", raw_text)
    except json.JSONDecodeError:
        result_text = raw_text

    # Strip optional markdown fences that Claude may add despite instructions
    result_text = result_text.strip()
    if result_text.startswith("```"):
        lines = result_text.splitlines()
        # Drop the opening fence line and the closing fence line
        inner_lines = []
        in_fence = False
        for line in lines:
            if line.startswith("```") and not in_fence:
                in_fence = True
                continue
            if line.startswith("```") and in_fence:
                break
            inner_lines.append(line)
        result_text = "\n".join(inner_lines)

    try:
        data = json.loads(result_text)
    except json.JSONDecodeError as exc:
        logger.warning(
            "Failed to parse claude output as JSON (%s); falling back to heuristic inference.",
            exc,
        )
        return infer_entities(pages), infer_relationships(infer_entities(pages))

    # Convert raw dicts to model objects
    entities: list[Entity] = []
    for e in data.get("entities", []):
        fields = [
            EntityField(
                name=f["name"],
                field_type=f.get("field_type", "TEXT"),
                nullable=f.get("nullable", True),
                is_primary=f.get("is_primary", False),
            )
            for f in e.get("fields", [])
        ]
        entities.append(Entity(
            name=e["name"],
            fields=fields,
            source_url=e.get("source_url"),
            source_title=e.get("source_title"),
        ))

    relationships: list[Relationship] = []
    for r in data.get("relationships", []):
        relationships.append(Relationship(
            from_entity=r["from_entity"],
            to_entity=r["to_entity"],
            relation_type=r.get("relation_type", "one-to-many"),
            label=r.get("label"),
        ))

    return entities, relationships
