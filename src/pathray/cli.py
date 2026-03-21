"""CLI entry point for pathray."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Optional
from urllib.parse import urlparse

if TYPE_CHECKING:
    from pathray.models.erd import Entity, Relationship

import typer
from rich import print as rprint

from pathray import __version__

app = typer.Typer(
    name="pathray",
    help="Web page structure analyzer and ERD generator.",
)


def version_callback(value: bool) -> None:
    if value:
        rprint(f"pathray {__version__}")
        raise typer.Exit()


def _validate_url(url: str) -> str:
    """Validate that URL has a valid scheme and netloc."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise typer.BadParameter(
            f"Invalid URL scheme: '{parsed.scheme}'. "
            "Use http:// or https://",
        )
    if not parsed.netloc:
        raise typer.BadParameter(
            f"Invalid URL: '{url}'. Missing domain.",
        )
    return url


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """pathray - Web page structure analyzer and ERD generator."""


@app.command()
def crawl(
    url: str = typer.Argument(help="Target URL to crawl."),
    depth: int = typer.Option(
        5, "--depth", "-d", help="Maximum crawl depth.",
    ),
    concurrency: int = typer.Option(
        3, "--concurrency", "-c", help="Max concurrent pages.",
    ),
    output: str = typer.Option(
        "output/sitemap.json",
        "--output",
        "-o",
        help="Output file path.",
    ),
    silent: bool = typer.Option(
        False, "--silent", "-s", help="Disable progress output.",
    ),
) -> None:
    """Crawl a website and generate a sitemap."""
    url = _validate_url(url)
    asyncio.run(
        _crawl_async(url, depth, concurrency, output, silent),
    )


async def _crawl_async(
    url: str,
    depth: int,
    concurrency: int,
    output: str,
    silent: bool,
) -> None:
    from pathray.crawler.browser import launch_browser
    from pathray.crawler.crawler_engine import CrawlerEngine
    from pathray.crawler.progress import RichCrawlProgress
    from pathray.crawler.sitemap_writer import write_sitemap

    progress = RichCrawlProgress(silent=silent)
    engine = CrawlerEngine(
        url,
        max_depth=depth,
        concurrency=concurrency,
        progress=progress,
    )

    if not silent:
        rprint(
            f"[bold]Crawling[/bold] {url} "
            f"(depth={depth}, concurrency={concurrency})",
        )

    async with launch_browser() as browser:
        entries = await engine.crawl(browser)

    path = write_sitemap(entries, output)
    if not silent:
        rprint(f"[bold]Sitemap written to[/bold] {path}")


@app.command()
def extract(
    sitemap: str = typer.Argument(
        help="Path to sitemap JSON file.",
        exists=True,
    ),
    output: str = typer.Option(
        "output/data/",
        "--output",
        "-o",
        help="Output directory for extracted page JSON files.",
    ),
    concurrency: int = typer.Option(
        3, "--concurrency", "-c", min=1, help="Max concurrent pages.",
    ),
    silent: bool = typer.Option(
        False, "--silent", "-s", help="Disable progress output.",
    ),
    dump_html: bool = typer.Option(
        False, "--dump-html", help="Save raw HTML of each page.",
    ),
) -> None:
    """Extract page structure data from crawled pages."""
    asyncio.run(_extract_async(sitemap, output, concurrency, silent, dump_html))


async def _extract_async(
    sitemap: str,
    output: str,
    concurrency: int,
    silent: bool,
    dump_html: bool = False,
) -> None:
    from rich.console import Console

    from pathray.extractor.extraction_engine import ExtractionEngine, ExtractionProgress

    console = Console()

    class _RichProgress(ExtractionProgress):
        def on_page_start(self, url: str, index: int, total: int) -> None:
            if not silent:
                console.print(f"  [dim]Extracting ({index}/{total}):[/dim] {url}")

        def on_page_done(
            self, url: str, index: int, total: int, error: str | None,
        ) -> None:
            if silent:
                return
            if error:
                console.print(f"  [yellow]Warning:[/yellow] {url} - {error}")

        def on_complete(self, total: int, errors: int, elapsed: float) -> None:
            if silent:
                return
            console.print()
            console.print("[bold green]Extraction complete![/bold green]")
            console.print(f"  Total pages: {total}")
            console.print(f"  Errors: {errors}")
            console.print(f"  Elapsed: {elapsed:.1f}s")

    if not silent:
        rprint(f"[bold]Extracting[/bold] from {sitemap} (concurrency={concurrency})")

    engine = ExtractionEngine(
        sitemap,
        output,
        concurrency=concurrency,
        progress=_RichProgress(),
        dump_html=dump_html,
    )
    pages = await engine.run()

    if not silent:
        rprint(f"[bold]Pages saved to[/bold] {output} ({len(pages)} files)")

    from pathray.extractor.summary_generator import generate_summary, print_summary

    summary_path = str(Path(output).parent / "summary.json")
    summary = generate_summary(pages, summary_path)

    if not silent:
        print_summary(summary)
        rprint(f"[bold]Summary written to[/bold] {summary_path}")


def _write_erd_outputs(
    entities: list[Entity],
    relationships: list[Relationship],
    out_path: Path,
    fmt: str,
) -> None:
    """Write ERD, DDL, Mermaid, and image outputs (shared by erd + run)."""
    import json as _json

    from pathray.erd.ddl_generator import ddl_to_file
    from pathray.erd.image_renderer import render_images
    from pathray.erd.mermaid_generator import save_mermaid

    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Primary ERD output
    if fmt == "json":
        from collections import defaultdict

        groups: defaultdict[str, list[Entity]] = defaultdict(list)
        for e in entities:
            key = e.source_title or e.source_url or ""
            groups[key].append(e)

        pages_out = []
        for label, group_entities in groups.items():
            url = group_entities[0].source_url
            pages_out.append({
                "title": label or None,
                "url": url,
                "entities": [e.model_dump() for e in group_entities],
            })

        data = {
            "pages": pages_out,
            "relationships": [r.model_dump() for r in relationships],
        }
        out_path.write_text(
            _json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8",
        )
        rprint(f"[bold]ERD written to[/bold] {out_path}")
    elif fmt == "mermaid":
        mmd_path = (
            out_path.with_suffix(".mmd") if out_path.suffix != ".mmd" else out_path
        )
        save_mermaid(entities, relationships, mmd_path)
        rprint(f"[bold]Mermaid ERD written to[/bold] {mmd_path}")
    elif fmt == "dot":
        rprint("[yellow]DOT format is not yet implemented.[/yellow]")
        raise typer.Exit(code=1)
    else:
        rprint(f"[red]Error:[/red] Unknown format: {fmt!r}. Use json, mermaid, or dot.")
        raise typer.Exit(code=1)

    # DDL
    sql_path = out_path.parent / "schema.sql"
    ddl_to_file(entities, relationships, sql_path)
    rprint(f"[bold]SQL DDL written to[/bold] {sql_path}")

    # Mermaid + images
    mmd_for_image = out_path.parent / "erd.mmd"
    if fmt != "mermaid":
        save_mermaid(entities, relationships, mmd_for_image)
    else:
        mmd_for_image = (
            out_path.with_suffix(".mmd") if out_path.suffix != ".mmd" else out_path
        )

    results = render_images(mmd_for_image, out_path.parent)
    if results.get("png"):
        rprint(f"[bold]ERD image written to[/bold] {results['png']}")
    if results.get("svg"):
        rprint(f"[bold]ERD SVG written to[/bold] {results['svg']}")


@app.command()
def erd(
    pages_dir: str = typer.Argument(
        help="Path to extracted pages directory.",
    ),
    output: str = typer.Option(
        "output/erd.json",
        "--output",
        "-o",
        help="Output file path.",
    ),
    fmt: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format (json, mermaid).",
    ),
    threshold: float = typer.Option(
        0.6,
        "--threshold",
        "-t",
        help="Jaccard similarity threshold for entity merging.",
        min=0.0,
        max=1.0,
    ),
    ai: bool = typer.Option(False, "--ai", help="Use AI analysis for entity inference."),
) -> None:
    """Generate ERD from extracted page data."""
    from pathlib import Path as _Path

    from rich.console import Console

    from pathray.erd.entity_inferrer import infer_entities, load_pages_from_dir
    from pathray.erd.relationship_inferrer import infer_relationships

    console = Console()

    pages_path = _Path(pages_dir)
    if not pages_path.exists():
        rprint(f"[red]Error:[/red] Directory not found: {pages_dir}")
        raise typer.Exit(code=1)

    rprint(f"[bold]Generating ERD[/bold] from {pages_dir}")

    pages = load_pages_from_dir(pages_path)
    if not pages:
        rprint(f"[yellow]Warning:[/yellow] No page-*.json files found in {pages_dir}")

    if ai:
        rprint("AI 분석 중...")
        from pathray.erd.ai_analyzer import analyze_with_ai
        entities, relationships = analyze_with_ai(pages)
    else:
        entities = infer_entities(pages, threshold=threshold)
        relationships = infer_relationships(entities)

    console.print(
        f"  Entities: [bold]{len(entities)}[/bold]  "
        f"Relationships: [bold]{len(relationships)}[/bold]"
    )

    _write_erd_outputs(entities, relationships, _Path(output), fmt)


@app.command()
def run(
    url: str = typer.Argument(
        help="Target URL for full pipeline.",
    ),
    output: str = typer.Option(
        "output/",
        "--output",
        "-o",
        help="Output directory.",
    ),
    fmt: str = typer.Option(
        "json",
        "--format",
        "-f",
        help="ERD output format (json, mermaid).",
    ),
    ai: bool = typer.Option(False, "--ai", help="Use AI analysis for entity inference."),
    dump_html: bool = typer.Option(False, "--dump-html", help="Save raw HTML of each page."),
) -> None:
    """Run the full pipeline: crawl -> extract -> erd."""
    url = _validate_url(url)
    asyncio.run(_run_async(url, output, fmt, ai, dump_html))


async def _run_async(url: str, output: str, fmt: str, ai: bool = False, dump_html: bool = False) -> None:
    from pathlib import Path as _Path

    from rich.console import Console

    console = Console()
    out = _Path(output)

    sitemap_path = str(out / "sitemap.json")
    pages_dir = str(out / "data")
    erd_ext = ".mmd" if fmt == "mermaid" else ".json"
    erd_path = str(out / f"erd{erd_ext}")

    # ── Step 1: Crawl ────────────────────────────────────────────────────────
    console.rule("[bold]Step 1/3: Crawl[/bold]")
    try:
        from pathray.crawler.browser import launch_browser
        from pathray.crawler.crawler_engine import CrawlerEngine
        from pathray.crawler.progress import RichCrawlProgress
        from pathray.crawler.sitemap_writer import write_sitemap

        progress = RichCrawlProgress(silent=False)
        engine = CrawlerEngine(url, progress=progress)
        async with launch_browser() as browser:
            entries = await engine.crawl(browser)
        write_sitemap(entries, sitemap_path)
        console.print(f"[green]✓[/green] Sitemap saved to {sitemap_path}")
    except Exception as exc:
        console.print(f"[red]✗ Crawl failed:[/red] {exc}")
        raise typer.Exit(code=1)

    # ── Step 2: Extract ──────────────────────────────────────────────────────
    console.rule("[bold]Step 2/3: Extract[/bold]")
    try:
        from pathray.extractor.extraction_engine import (
            ExtractionEngine,
            ExtractionProgress,
        )

        class _Silent(ExtractionProgress):
            pass

        engine2 = ExtractionEngine(sitemap_path, pages_dir, progress=_Silent(), dump_html=dump_html)
        pages = await engine2.run()
        console.print(f"[green]✓[/green] Extracted {len(pages)} pages to {pages_dir}")

        from pathray.extractor.summary_generator import generate_summary

        summary_path = str(out / "summary.json")
        generate_summary(pages, summary_path)
        console.print(f"[green]✓[/green] Summary saved to {summary_path}")
    except Exception as exc:
        console.print(f"[red]✗ Extract failed:[/red] {exc}")
        raise typer.Exit(code=1)

    # ── Step 3: ERD + DDL + Images ──────────────────────────────────────────
    console.rule("[bold]Step 3/3: ERD[/bold]")
    try:
        from pathray.erd.entity_inferrer import infer_entities, load_pages_from_dir
        from pathray.erd.relationship_inferrer import infer_relationships

        page_data = load_pages_from_dir(pages_dir)
        if ai:
            console.print("AI 분석 중...")
            from pathray.erd.ai_analyzer import analyze_with_ai
            entities, relationships = analyze_with_ai(page_data)
        else:
            entities = infer_entities(page_data)
            relationships = infer_relationships(entities)

        console.print(
            f"  Entities: [bold]{len(entities)}[/bold]  "
            f"Relationships: [bold]{len(relationships)}[/bold]"
        )

        _write_erd_outputs(entities, relationships, _Path(erd_path), fmt)
    except typer.Exit:
        raise
    except Exception as exc:
        console.print(f"[red]✗ ERD generation failed:[/red] {exc}")
        raise typer.Exit(code=1)

    console.rule("[bold green]Pipeline complete![/bold green]")
