"""CLI entry point for pathray."""

from typing import Optional

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
    depth: int = typer.Option(2, "--depth", "-d", help="Maximum crawl depth."),
    output: str = typer.Option(
        "output/sitemap.json", "--output", "-o", help="Output file path.",
    ),
) -> None:
    """Crawl a website and generate a sitemap."""
    rprint(f"[bold]Crawling[/bold] {url} (depth={depth})")


@app.command()
def extract(
    sitemap: str = typer.Argument(help="Path to sitemap JSON file."),
    output: str = typer.Option(
        "output/pages/", "--output", "-o", help="Output directory.",
    ),
) -> None:
    """Extract page structure data from crawled pages."""
    rprint(f"[bold]Extracting[/bold] from {sitemap}")


@app.command()
def erd(
    pages_dir: str = typer.Argument(help="Path to extracted pages directory."),
    output: str = typer.Option(
        "output/erd.json", "--output", "-o", help="Output file path.",
    ),
    fmt: str = typer.Option(
        "json", "--format", "-f", help="Output format (json, mermaid, dot).",
    ),
) -> None:
    """Generate ERD from extracted page data."""
    rprint(f"[bold]Generating ERD[/bold] from {pages_dir}")


@app.command()
def run(
    url: str = typer.Argument(help="Target URL for full pipeline."),
    output: str = typer.Option("output/", "--output", "-o", help="Output directory."),
) -> None:
    """Run the full pipeline: crawl → extract → erd."""
    rprint(f"[bold]Running full pipeline[/bold] for {url}")
