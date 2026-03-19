"""Rich-based crawling progress display."""

import time

from rich.console import Console

from pathray.crawler.crawler_engine import CrawlProgress


class RichCrawlProgress(CrawlProgress):
    """Progress display using Rich library."""

    def __init__(self, *, silent: bool = False) -> None:
        self._silent = silent
        self._console = Console()
        self._completed = 0
        self._start_time = time.monotonic()

    def on_page_start(self, url: str) -> None:
        if self._silent:
            return
        self._console.print(
            f"  [dim]Crawling:[/dim] {url}",
        )

    def on_page_done(self, url: str, status_code: int, error: str | None) -> None:
        self._completed += 1
        if self._silent:
            return
        elapsed = time.monotonic() - self._start_time
        if error:
            self._console.print(
                f"  [yellow]Warning:[/yellow] {url} - {error} "
                f"({self._completed} pages, {elapsed:.1f}s)",
            )
        elif status_code >= 400:
            self._console.print(
                f"  [yellow]Warning:[/yellow] {url} "
                f"- HTTP {status_code} "
                f"({self._completed} pages, {elapsed:.1f}s)",
            )
        else:
            self._console.print(
                f"  [dim]Done:[/dim] {self._completed} pages, "
                f"{elapsed:.1f}s elapsed",
            )

    def on_complete(
        self, total: int, errors: int, elapsed: float,
    ) -> None:
        if self._silent:
            return
        self._console.print()
        self._console.print("[bold green]Crawling complete![/bold green]")
        self._console.print(f"  Total pages: {total}")
        self._console.print(f"  Errors: {errors}")
        self._console.print(f"  Elapsed: {elapsed:.1f}s")
