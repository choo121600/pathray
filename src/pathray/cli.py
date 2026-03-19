"""CLI entry point for pathray."""

import asyncio
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

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
    ),
    output: str = typer.Option(
        "output/data/",
        "--output",
        "-o",
        help="Output directory for extracted page JSON files.",
    ),
    concurrency: int = typer.Option(
        3, "--concurrency", "-c", help="Max concurrent pages.",
    ),
    silent: bool = typer.Option(
        False, "--silent", "-s", help="Disable progress output.",
    ),
) -> None:
    """Extract page structure data from crawled pages."""
    asyncio.run(_extract_async(sitemap, output, concurrency, silent))


async def _extract_async(
    sitemap: str,
    output: str,
    concurrency: int,
    silent: bool,
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
        help="Output format (json, mermaid, dot).",
    ),
) -> None:
    """Generate ERD from extracted page data."""
    rprint(f"[bold]Generating ERD[/bold] from {pages_dir}")


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
) -> None:
    """Run the full pipeline: crawl -> extract -> erd."""
    rprint(f"[bold]Running full pipeline[/bold] for {url}")
