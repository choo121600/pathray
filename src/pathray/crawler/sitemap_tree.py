"""Sitemap tree visualizer — generates Mermaid flowchart from crawled sitemap."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

from pathray.models.sitemap import SitemapEntry


def _sanitize_label(text: str) -> str:
    """Escape characters that break Mermaid syntax."""
    text = text.replace('"', "'")
    text = text.replace("(", "&#40;")
    text = text.replace(")", "&#41;")
    return text


def _build_tree(entries: list[SitemapEntry]) -> dict:
    """Build a nested dict tree from URL paths.

    Returns a dict where keys are path segments and values are dicts with
    '_entries' holding SitemapEntry objects for that node.
    """
    tree: dict = {}
    for entry in entries:
        parsed = urlparse(str(entry.url))
        # Split path into segments, filter empty
        segments = [s for s in parsed.path.split("/") if s]
        node = tree
        for seg in segments:
            if seg not in node:
                node[seg] = {}
            node = node[seg]
        # Store entry info at leaf
        if "_entries" not in node:
            node["_entries"] = []
        node["_entries"].append(entry)

    return tree


def _node_id(prefix: str, segment: str) -> str:
    """Generate a safe Mermaid node ID."""
    raw = f"{prefix}_{segment}" if prefix else segment
    return re.sub(r"[^a-zA-Z0-9_]", "_", raw)


def _generate_lines(
    tree: dict,
    parent_id: str | None,
    prefix: str,
    lines: list[str],
    *,
    max_depth: int = 0,
    current_depth: int = 0,
) -> None:
    """Recursively generate Mermaid flowchart lines from the tree."""
    if max_depth and current_depth >= max_depth:
        return

    for key, subtree in sorted(tree.items()):
        if key == "_entries":
            continue

        node_id = _node_id(prefix, key)

        # Build label: segment name + title if available
        entries = subtree.get("_entries", [])
        if entries:
            title = entries[0].title
            status = entries[0].status_code
            if title and title != key:
                label = f"{_sanitize_label(key)}\\n{_sanitize_label(title)}"
            else:
                label = _sanitize_label(key)
            # Color nodes by status
            if status == 200:
                lines.append(f"    {node_id}[\"{label}\"]")
            elif status == 0:
                lines.append(f"    {node_id}[\"{label}\"]:::error")
            else:
                lines.append(f"    {node_id}[\"{label}\"]:::warn")
        else:
            # Directory node (no page directly)
            lines.append(f"    {node_id}{{\"{_sanitize_label(key)}\"}}")

        if parent_id:
            lines.append(f"    {parent_id} --> {node_id}")

        _generate_lines(
            subtree,
            node_id,
            f"{prefix}_{key}" if prefix else key,
            lines,
            max_depth=max_depth,
            current_depth=current_depth + 1,
        )


def generate_sitemap_mermaid(
    entries: list[SitemapEntry],
    *,
    max_depth: int = 0,
) -> str:
    """Generate a Mermaid flowchart from sitemap entries.

    Args:
        entries: Crawled sitemap entries.
        max_depth: Max tree depth to render (0 = unlimited).

    Returns:
        Mermaid diagram string.
    """
    if not entries:
        return "flowchart LR\n    empty[\"No pages found\"]"

    # Determine root domain
    first_url = str(entries[0].url)
    parsed = urlparse(first_url)
    domain = parsed.netloc

    tree = _build_tree(entries)
    lines: list[str] = [
        "flowchart LR",
        f"    root([\"{_sanitize_label(domain)}\"])",
    ]

    _generate_lines(
        tree,
        "root",
        "",
        lines,
        max_depth=max_depth,
    )

    # Style classes
    lines.append("")
    lines.append("    classDef error fill:#ff6b6b,color:#fff")
    lines.append("    classDef warn fill:#ffd93d,color:#333")

    return "\n".join(lines)


def save_sitemap_tree(
    entries: list[SitemapEntry],
    output_path: Path | str,
    *,
    max_depth: int = 0,
    render: bool = True,
) -> dict[str, Path | None]:
    """Generate and save a Mermaid sitemap tree diagram with optional images.

    Args:
        entries: Crawled sitemap entries.
        output_path: Output .mmd file path.
        max_depth: Max tree depth to render (0 = unlimited).
        render: Also render PNG/SVG images (requires Node.js).

    Returns:
        Dict with keys "mmd", "png", "svg" pointing to generated file paths.
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    mermaid = generate_sitemap_mermaid(entries, max_depth=max_depth)
    path.write_text(mermaid, encoding="utf-8")

    results: dict[str, Path | None] = {"mmd": path, "png": None, "svg": None}

    if render:
        from pathray.erd.image_renderer import render_images

        img_results = render_images(path, path.parent)
        results["png"] = img_results.get("png")
        results["svg"] = img_results.get("svg")

    return results


def load_and_generate(
    sitemap_path: str | Path,
    output_path: str | Path,
    *,
    max_depth: int = 0,
    render: bool = True,
) -> dict[str, Path | None]:
    """Load a sitemap.json and generate the tree diagram.

    Args:
        sitemap_path: Path to sitemap.json.
        output_path: Output .mmd file path.
        max_depth: Max tree depth (0 = unlimited).
        render: Also render PNG/SVG images (requires Node.js).

    Returns:
        Dict with keys "mmd", "png", "svg" pointing to generated file paths.
    """
    data = json.loads(Path(sitemap_path).read_text())
    entries = [SitemapEntry(**e) for e in data]
    return save_sitemap_tree(entries, output_path, max_depth=max_depth, render=render)
