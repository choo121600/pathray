"""Extraction orchestrator: visits pages and runs all extractors."""

import asyncio
import json
import time
from pathlib import Path

from playwright.async_api import Browser

from pathray.crawler.browser import launch_browser
from pathray.extractor.form_extractor import extract_forms
from pathray.extractor.meta_extractor import extract_metadata
from pathray.extractor.table_extractor import extract_tables
from pathray.extractor.text_extractor import extract_text
from pathray.models.page_data import PageData
from pathray.models.sitemap import SitemapEntry


class ExtractionProgress:
    """Callback interface for extraction progress reporting."""

    def on_page_start(self, url: str, index: int, total: int) -> None:
        pass

    def on_page_done(
        self, url: str, index: int, total: int, error: str | None,
    ) -> None:
        pass

    def on_complete(self, total: int, errors: int, elapsed: float) -> None:
        pass


class ExtractionEngine:
    """Visits each URL from a sitemap and runs all extractors."""

    def __init__(
        self,
        sitemap_path: str,
        output_dir: str = "output/data/",
        *,
        concurrency: int = 3,
        progress: ExtractionProgress | None = None,
    ) -> None:
        if concurrency < 1:
            msg = "concurrency must be at least 1"
            raise ValueError(msg)
        self._sitemap_path = Path(sitemap_path)
        self._output_dir = Path(output_dir)
        self._concurrency = concurrency
        self._progress = progress or ExtractionProgress()

    def _load_entries(self) -> list[SitemapEntry]:
        data = json.loads(self._sitemap_path.read_text())
        return [SitemapEntry.model_validate(entry) for entry in data]

    async def run(self) -> list[PageData]:
        """Run extraction on all URLs in the sitemap.

        Returns list of PageData for successfully extracted pages.
        Individual page failures are logged and skipped.
        """
        entries = self._load_entries()
        self._output_dir.mkdir(parents=True, exist_ok=True)

        semaphore = asyncio.Semaphore(self._concurrency)
        results: list[PageData | None] = [None] * len(entries)
        start_time = time.monotonic()

        async with launch_browser() as browser:
            tasks = [
                self._process_entry(
                    browser, entry, idx, len(entries), semaphore, results,
                )
                for idx, entry in enumerate(entries)
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

        error_count = sum(1 for r in results if r is None)
        elapsed = time.monotonic() - start_time
        self._progress.on_complete(len(entries), error_count, elapsed)

        return [r for r in results if r is not None]

    async def _process_entry(
        self,
        browser: Browser,
        entry: SitemapEntry,
        idx: int,
        total: int,
        semaphore: asyncio.Semaphore,
        results: list[PageData | None],
    ) -> None:
        url = str(entry.url)
        async with semaphore:
            self._progress.on_page_start(url, idx + 1, total)
            error: str | None = None
            try:
                page = await browser.new_page()
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    meta = await extract_metadata(page)
                    tables = await extract_tables(page)
                    forms = await extract_forms(page)
                    text_blocks = await extract_text(page)
                    page_data = PageData(
                        url=entry.url,
                        meta=meta,
                        tables=tables,
                        forms=forms,
                        text_blocks=text_blocks,
                    )
                    out_path = self._output_dir / f"page-{idx:03d}.json"
                    out_path.write_text(page_data.model_dump_json(indent=2))
                    results[idx] = page_data
                finally:
                    await page.close()
            except Exception as exc:
                error = str(exc)
            finally:
                self._progress.on_page_done(url, idx + 1, total, error)
