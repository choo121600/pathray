"""URL queue and visited tracking for BFS crawling."""

from collections import deque
from urllib.parse import ParseResult, parse_qsl, urlencode, urlparse


def normalize_url(url: str) -> str:
    """Normalize a URL for deduplication.

    - Remove fragment (#section)
    - Remove trailing slash from path
    - Sort query parameters
    """
    parsed: ParseResult = urlparse(url)
    path = parsed.path.rstrip("/") if parsed.path not in ("", "/") else "/"
    sorted_query = urlencode(sorted(parse_qsl(parsed.query)))
    normalized = ParseResult(
        scheme=parsed.scheme,
        netloc=parsed.netloc,
        path=path,
        params=parsed.params,
        query=sorted_query,
        fragment="",
    )
    return normalized.geturl()


def is_same_domain(url: str, base_url: str) -> bool:
    """Check if url belongs to the same domain as base_url."""
    return urlparse(url).netloc == urlparse(base_url).netloc


class URLQueue:
    """BFS URL queue with visited tracking and domain filtering."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url
        self._queue: deque[tuple[str, int]] = deque()
        self._visited: set[str] = set()

    @property
    def base_url(self) -> str:
        return self._base_url

    def enqueue(self, url: str, depth: int) -> bool:
        """Add a URL to the queue if not visited and same domain.

        Returns True if the URL was added, False if skipped.
        """
        normalized = normalize_url(url)
        if normalized in self._visited:
            return False
        if not is_same_domain(normalized, self._base_url):
            return False
        self._visited.add(normalized)
        self._queue.append((normalized, depth))
        return True

    def dequeue(self) -> tuple[str, int]:
        """Remove and return the next (url, depth) pair."""
        return self._queue.popleft()

    def is_empty(self) -> bool:
        """Check if the queue has no more URLs to process."""
        return len(self._queue) == 0

    @property
    def visited_count(self) -> int:
        """Number of unique URLs seen."""
        return len(self._visited)
