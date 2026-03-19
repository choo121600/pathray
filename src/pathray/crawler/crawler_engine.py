"""Main crawling orchestrator with concurrency control."""

import asyncio
import time
from datetime import datetime, timezone

from playwright.async_api import Browser

from pathray.crawler.page_crawler import crawl_page
from pathray.crawler.queue import URLQueue
from pathray.models.sitemap import SitemapEntry


class CrawlProgress:
    """Callback interface for progress reporting."""

    def on_page_start(self, url: str) -> None:
        pass

    def on_page_done(self, url: str, status_code: int, error: str | None) -> None:
        pass

    def on_complete(
        self, total: int, errors: int, elapsed: float,
    ) -> None:
        pass


class CrawlerEngine:
    """BFS web crawler with asyncio concurrency control."""

    def __init__(
        self,
        base_url: str,
        *,
        max_depth: int = 5,
        concurrency: int = 3,
        progress: CrawlProgress | None = None,
        respect_robots: bool = True,
    ) -> None:
        self._base_url = base_url
        self._max_depth = max_depth
        self._concurrency = concurrency
        self._progress = progress or CrawlProgress()
        self._respect_robots = respect_robots
        self._results: list[SitemapEntry] = []
        self._lock = asyncio.Lock()

    async def crawl(self, browser: Browser) -> list[SitemapEntry]:
        """Run BFS crawl starting from base_url.

        Returns list of SitemapEntry for all discovered pages.
        """
        queue = URLQueue(self._base_url)
        queue.enqueue(self._base_url, 0)

        semaphore = asyncio.Semaphore(self._concurrency)
        self._results = []
        start_time = time.monotonic()

        active_tasks: set[asyncio.Task[None]] = set()

        while not queue.is_empty() or active_tasks:
            while not queue.is_empty():
                url, depth = queue.dequeue()
                task = asyncio.create_task(
                    self._process_url(
                        browser, url, depth, queue, semaphore,
                    ),
                )
                active_tasks.add(task)
                task.add_done_callback(active_tasks.discard)

            if active_tasks:
                done, _ = await asyncio.wait(
                    active_tasks,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for t in done:
                    t.result()

        elapsed = time.monotonic() - start_time
        error_count = sum(
            1 for e in self._results if e.status_code == 0
        )
        self._progress.on_complete(
            len(self._results), error_count, elapsed,
        )

        return self._results

    async def _process_url(
        self,
        browser: Browser,
        url: str,
        depth: int,
        queue: URLQueue,
        semaphore: asyncio.Semaphore,
    ) -> None:
        async with semaphore:
            self._progress.on_page_start(url)
            result = await crawl_page(
                browser, url, respect_robots=self._respect_robots,
            )
            self._progress.on_page_done(
                url, result.status_code, result.error,
            )

            entry = SitemapEntry(
                url=result.url,
                title=result.title,
                depth=depth,
                status_code=result.status_code,
                links=[link for link in result.links],
                timestamp=datetime.now(timezone.utc),
            )
            async with self._lock:
                self._results.append(entry)

            if depth < self._max_depth:
                for link in result.links:
                    queue.enqueue(link, depth + 1)
