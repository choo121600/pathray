"""Integration tests with local test server (Issue #11)."""

import json
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import pytest

from pathray.crawler.crawler_engine import CrawlerEngine
from pathray.crawler.sitemap_writer import write_sitemap

FIXTURES_DIR = Path(__file__).parent / "fixtures"

PATH_MAP = {
    "/": "index.html",
    "/about": "about.html",
    "/products": "products.html",
    "/products/widget": "widget.html",
    "/products/gadget": "gadget.html",
    "/blog": "blog.html",
    "/blog/post1": "post1.html",
    "/blog/post2": "post2.html",
    "/contact": "contact.html",
    "/team": "team.html",
    "/history": "history.html",
}


class FixtureHandler(SimpleHTTPRequestHandler):
    """Serves fixture HTML files based on path mapping."""

    def do_GET(self):
        path = self.path.split("?")[0].split("#")[0]
        path = path.rstrip("/") or "/"
        filename = PATH_MAP.get(path)
        if filename:
            filepath = FIXTURES_DIR / filename
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(filepath.read_bytes())
        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><head><title>Not Found</title>"
                b"</head><body>404</body></html>",
            )

    def log_message(self, format, *args):
        pass


@pytest.fixture(scope="module")
def test_server():
    """Start a local HTTP server serving fixture pages."""
    server = HTTPServer(("127.0.0.1", 0), FixtureHandler)
    port = server.server_address[1]
    thread = threading.Thread(
        target=server.serve_forever, daemon=True,
    )
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()


@pytest.mark.asyncio
async def test_crawl_discovers_all_pages(test_server):
    """Crawler discovers all 11 pages on the test server."""
    from pathray.crawler.browser import launch_browser

    engine = CrawlerEngine(
        test_server, max_depth=5, concurrency=2,
        respect_robots=False,
    )
    async with launch_browser() as browser:
        entries = await engine.crawl(browser)

    assert len(entries) == 11, (
        f"Expected 11 pages, got {len(entries)}"
    )


@pytest.mark.asyncio
async def test_crawl_no_infinite_loop(test_server):
    """Circular refs don't cause infinite loop."""
    from pathray.crawler.browser import launch_browser

    engine = CrawlerEngine(
        test_server, max_depth=10, concurrency=2,
        respect_robots=False,
    )
    async with launch_browser() as browser:
        entries = await engine.crawl(browser)

    assert len(entries) == 11


@pytest.mark.asyncio
async def test_crawl_excludes_external_links(test_server):
    """External links are not crawled."""
    from pathray.crawler.browser import launch_browser

    engine = CrawlerEngine(
        test_server, max_depth=5, concurrency=2,
        respect_robots=False,
    )
    async with launch_browser() as browser:
        entries = await engine.crawl(browser)

    urls = [str(e.url) for e in entries]
    for url in urls:
        assert "external" not in url, (
            f"External URL found: {url}"
        )


@pytest.mark.asyncio
async def test_crawl_generates_valid_sitemap(
    test_server, tmp_path,
):
    """Full pipeline: crawl -> write sitemap -> verify JSON."""
    from pathray.crawler.browser import launch_browser

    engine = CrawlerEngine(
        test_server, max_depth=5, concurrency=2,
        respect_robots=False,
    )
    async with launch_browser() as browser:
        entries = await engine.crawl(browser)

    output = str(tmp_path / "sitemap.json")
    write_sitemap(entries, output)

    data = json.loads(Path(output).read_text())
    assert len(data) == 11

    for entry in data:
        assert "url" in entry
        assert "title" in entry
        assert "depth" in entry
        assert "status_code" in entry
        assert entry["status_code"] == 200


@pytest.mark.asyncio
async def test_crawl_respects_depth_limit(test_server):
    """With depth=1, only root + direct children."""
    from pathray.crawler.browser import launch_browser

    engine = CrawlerEngine(
        test_server, max_depth=1, concurrency=2,
        respect_robots=False,
    )
    async with launch_browser() as browser:
        entries = await engine.crawl(browser)

    # depth 0: /, depth 1: /about, /products, /blog, /contact
    assert len(entries) == 5, (
        f"Expected 5 pages at depth<=1, got {len(entries)}"
    )
