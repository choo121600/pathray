"""Tests for URL queue and visited tracking (Issue #6)."""

from pathray.crawler.queue import URLQueue, is_same_domain, normalize_url


class TestNormalizeUrl:
    def test_removes_fragment(self):
        assert normalize_url("https://example.com/page#section") == "https://example.com/page"

    def test_removes_trailing_slash(self):
        assert normalize_url("https://example.com/page/") == "https://example.com/page"

    def test_keeps_root_slash(self):
        assert normalize_url("https://example.com/") == "https://example.com/"

    def test_sorts_query_params(self):
        result = normalize_url("https://example.com/page?b=2&a=1")
        assert result == "https://example.com/page?a=1&b=2"

    def test_identical_urls_normalize_same(self):
        url1 = normalize_url("https://example.com/path/")
        url2 = normalize_url("https://example.com/path")
        assert url1 == url2

    def test_fragment_and_trailing_slash(self):
        result = normalize_url("https://example.com/path/#top")
        assert result == "https://example.com/path"


class TestIsSameDomain:
    def test_same_domain(self):
        assert is_same_domain("https://example.com/page", "https://example.com/")

    def test_different_domain(self):
        assert not is_same_domain("https://other.com/page", "https://example.com/")

    def test_subdomain_is_different(self):
        assert not is_same_domain("https://sub.example.com/", "https://example.com/")


class TestURLQueue:
    def test_enqueue_and_dequeue(self):
        q = URLQueue("https://example.com")
        q.enqueue("https://example.com/page1", 0)
        url, depth = q.dequeue()
        assert url == "https://example.com/page1"
        assert depth == 0

    def test_is_empty(self):
        q = URLQueue("https://example.com")
        assert q.is_empty()
        q.enqueue("https://example.com/page1", 0)
        assert not q.is_empty()

    def test_duplicate_ignored(self):
        q = URLQueue("https://example.com")
        assert q.enqueue("https://example.com/page1", 0) is True
        assert q.enqueue("https://example.com/page1", 1) is False

    def test_normalized_duplicate_ignored(self):
        q = URLQueue("https://example.com")
        q.enqueue("https://example.com/page/", 0)
        result = q.enqueue("https://example.com/page", 1)
        assert result is False

    def test_external_domain_filtered(self):
        q = URLQueue("https://example.com")
        result = q.enqueue("https://other.com/page", 0)
        assert result is False
        assert q.is_empty()

    def test_depth_tracking(self):
        q = URLQueue("https://example.com")
        q.enqueue("https://example.com/a", 0)
        q.enqueue("https://example.com/b", 2)
        _, d1 = q.dequeue()
        _, d2 = q.dequeue()
        assert d1 == 0
        assert d2 == 2

    def test_visited_count(self):
        q = URLQueue("https://example.com")
        q.enqueue("https://example.com/a", 0)
        q.enqueue("https://example.com/b", 0)
        q.enqueue("https://example.com/a", 1)  # duplicate
        assert q.visited_count == 2

    def test_fragment_dedup(self):
        q = URLQueue("https://example.com")
        q.enqueue("https://example.com/page#top", 0)
        result = q.enqueue("https://example.com/page#bottom", 1)
        assert result is False
