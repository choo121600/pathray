"""Sitemap JSON output writer."""

import json
from pathlib import Path

from pathray.models.sitemap import SitemapEntry


def write_sitemap(entries: list[SitemapEntry], output_path: str) -> Path:
    """Write sitemap entries to a JSON file.

    Args:
        entries: List of SitemapEntry from crawling.
        output_path: File path for JSON output.

    Returns:
        Path to the written file.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = [entry.model_dump(mode="json") for entry in entries]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    return path
