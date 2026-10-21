"""Tests for the web studio server: page rendering, SEO metadata, crawl files, and API routes."""

from __future__ import annotations

import gzip
import importlib.util
import json
import threading
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

import pytest

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def _load_server():
    spec = importlib.util.spec_from_file_location("cmm_web_server", WEB_DIR / "server.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


server_module = _load_server()
seo = server_module.seo
PAGE_PATHS = [p.path for p in seo.PAGES]


@pytest.fixture(scope="module")
def base_url():
    httpd = server_module.StudioServer(("127.0.0.1", 0), server_module.CmmRequestHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def fetch(url, data=None, headers=None):
    """Return (status, headers, body_bytes) without following redirects or raising on 4xx."""
    request = urllib.request.Request(url, data=data, headers=headers or {})
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=10) as res:
            return res.status, res.headers, res.read()
    except urllib.error.HTTPError as err:
        return err.code, err.headers, err.read()


class HeadParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.h1 = 0
        self.title = ""
        self._in_title = False
        self.meta = {}
        self.links = {}
        self.jsonld = []
        self._in_jsonld = False
        self._buf = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "h1":
            self.h1 += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = a.get("name") or a.get("property")
            if key:
                self.meta.setdefault(key, a.get("content"))
        elif tag == "link" and a.get("rel"):
            self.links[a["rel"]] = a.get("href")
        elif tag == "script" and a.get("type") == "application/ld+json":
            self._in_jsonld = True
            self._buf = ""

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_jsonld:
            self._in_jsonld = False
            self.jsonld.append(self._buf)

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_jsonld:
            self._buf += data


def parse_page(body: bytes) -> HeadParser:
    parser = HeadParser()
    parser.feed(body.decode("utf-8"))
    return parser


@pytest.mark.parametrize("path", PAGE_PATHS)
def test_page_has_complete_metadata(base_url, path):
    status, headers, body = fetch(base_url + path)
    assert status == 200
    assert headers["Content-Type"].startswith("text/html")
    page = parse_page(body)

    assert page.h1 == 1, f"{path} must have exactly one <h1>"
    assert 30 <= len(page.title) <= 65, page.title
    description = page.meta.get("description") or ""
    assert 110 <= len(description) <= 165, description
    assert page.links.get("canonical") == seo.absolute(path)
    for key in ("og:title", "og:description", "og:url", "og:image", "og:type", "twitter:card", "twitter:image"):
        assert page.meta.get(key), f"{path} missing {key}"
    assert page.meta["og:url"] == seo.absolute(path)
    assert "index" in page.meta.get("robots", "")

    assert page.jsonld, f"{path} has no JSON-LD"
    for block in page.jsonld:
        data = json.loads(block)
        assert data["@context"] == "https://schema.org"
        types = {node["@type"] for node in data["@graph"]}
        assert {"WebSite", "Organization"} <= types
        if path != "/":
            assert "BreadcrumbList" in types


def test_titles_and_descriptions_are_unique(base_url):
    titles, descriptions = set(), set()
    for path in PAGE_PATHS:
        page = parse_page(fetch(base_url + path)[2])
        titles.add(page.title)
        descriptions.add(page.meta["description"])
    assert len(titles) == len(PAGE_PATHS)
    assert len(descriptions) == len(PAGE_PATHS)


def test_page_specific_structured_data(base_url):
    def types_for(path):
        page = parse_page(fetch(base_url + path)[2])
        return {node["@type"]: node for node in json.loads(page.jsonld[0])["@graph"]}

    home = types_for("/")
    assert home["SoftwareApplication"]["softwareVersion"] == seo.SOFTWARE_VERSION
    assert home["SoftwareApplication"]["offers"]["price"] == "0"
    assert "TechArticle" in types_for("/reference")
    assert "TechArticle" in types_for("/architecture")

    faq = types_for("/about")["FAQPage"]["mainEntity"]
    about_html = fetch(base_url + "/about")[2].decode("utf-8")
    assert len(faq) >= 4
    for entry in faq:
        # Every FAQ question in the markup is visible on the page
        assert entry["name"] in about_html
        assert entry["acceptedAnswer"]["text"]


def test_active_view_is_server_rendered(base_url):
    body = fetch(base_url + "/reference")[2].decode("utf-8")
    assert 'class="tab-view active" id="view-syntax"' in body
    assert 'class="nav-tab active" href="/reference"' in body
    # Other content pages are not duplicated into this URL
    assert 'id="view-pipeline"' not in body
    # The playground shell is present but hidden, with an h2 heading
    assert 'class="tab-view" id="view-playground"' in body
    assert '<h2 class="sr-only" id="playground-title">' in body

    playground = fetch(base_url + "/playground")[2].decode("utf-8")
    assert '<h1 class="sr-only" id="playground-title">' in playground


def test_team_details(base_url):
    body = fetch(base_url + "/about")[2].decode("utf-8")
    for text in ("Mit Kumar Raju Panchal", "24BAI0279", "Garv Gupta", "24BDS0169", "Ronit Mexson", "24BAI0036"):
        assert text in body


def test_robots_txt(base_url):
    status, headers, body = fetch(base_url + "/robots.txt")
    text = body.decode("utf-8")
    assert status == 200 and headers["Content-Type"].startswith("text/plain")
    assert "Disallow: /api/" in text
    assert f"Sitemap: {seo.absolute('/sitemap.xml')}" in text


def test_sitemap_xml(base_url):
    status, headers, body = fetch(base_url + "/sitemap.xml")
    assert status == 200 and "xml" in headers["Content-Type"]
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    root = ET.fromstring(body)
    locs = [el.text for el in root.findall("sm:url/sm:loc", ns)]
    for path in PAGE_PATHS:
        assert seo.absolute(path) in locs
    assert all(el.text for el in root.findall("sm:url/sm:lastmod", ns))


def test_manifest_and_icons(base_url):
    status, headers, body = fetch(base_url + "/site.webmanifest")
    assert status == 200 and headers["Content-Type"].startswith("application/manifest+json")
    manifest = json.loads(body)
    for icon in manifest["icons"]:
        assert fetch(base_url + icon["src"])[0] == 200
    assert fetch(base_url + "/favicon.ico")[1]["Content-Type"] == "image/x-icon"
    assert fetch(base_url + "/assets/og-image.png")[0] == 200
    assert fetch(base_url + "/assets/apple-touch-icon.png")[0] == 200


def test_unknown_path_is_a_real_404(base_url):
    status, headers, body = fetch(base_url + "/no-such-page")
    assert status == 404
    page = parse_page(body)
    assert "noindex" in page.meta["robots"]
    assert "canonical" not in page.links
    assert page.h1 == 1


@pytest.mark.parametrize("path,target", [("/reference/", "/reference"), ("/about/", "/about"), ("/index.html", "/")])
def test_canonical_redirects(base_url, path, target):
    status, headers, _ = fetch(base_url + path)
    assert status == 301
    assert headers["Location"] == target


@pytest.mark.parametrize("path", ["/server.py", "/seo.py", "/templates/layout.html", "/content/home.html",
                                  "/assets/../web/server.py", "/assets/%2e%2e/web/server.py"])
def test_private_files_are_not_served(base_url, path):
    assert fetch(base_url + path)[0] == 404


def test_compression_caching_and_security_headers(base_url):
    status, headers, body = fetch(base_url + "/", headers={"Accept-Encoding": "gzip"})
    assert headers["Content-Encoding"] == "gzip"
    assert b"<!DOCTYPE html>" in gzip.decompress(body)
    assert "max-age=60" in headers["Cache-Control"]
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    csp = headers["Content-Security-Policy"]
    assert "default-src 'self'" in csp and "'sha256-" in csp

    etag = headers["ETag"]
    assert fetch(base_url + "/", headers={"If-None-Match": etag})[0] == 304

    css = fetch(base_url + f"/style.css?v={seo.asset_version('style.css')}")[1]
    assert "immutable" in css["Cache-Control"]
    assert css["Content-Type"].startswith("text/css")


def test_pdf_is_indexable(base_url):
    status, headers, _ = fetch(base_url + seo.SPEC_PDF_PATH)
    assert status == 200
    assert headers["Content-Type"] == "application/pdf"
    assert headers["X-Robots-Tag"] == "index, follow"


def test_verification_meta_from_environment(monkeypatch, base_url):
    monkeypatch.setenv("GOOGLE_SITE_VERIFICATION", "abc123token")
    monkeypatch.setenv("BING_SITE_VERIFICATION", "bing456")
    page = parse_page(fetch(base_url + "/")[2])
    assert page.meta["google-site-verification"] == "abc123token"
    assert page.meta["msvalidate.01"] == "bing456"

    monkeypatch.setenv("GOOGLE_SITE_VERIFICATION_FILE", "google0123abcd.html")
    status, _, body = fetch(base_url + "/google0123abcd.html")
    assert status == 200 and body == b"google-site-verification: google0123abcd.html"


def _post(base_url, endpoint, code):
    body = json.dumps({"code": code}).encode("utf-8")
    status, headers, data = fetch(base_url + endpoint, data=body, headers={"Content-Type": "application/json"})
    assert headers["Cache-Control"] == "no-store"
    return status, json.loads(data)


GOOD = "module main;\nfn main() {\n    print(6 * 7);\n}\n"
BAD = "module main;\nfn main() {\n    print(y);\n}\n"


def test_api_routes_unchanged(base_url):
    assert _post(base_url, "/api/run", GOOD) == (200, {"success": True, "stage": "interpreter", "output": "42\n", "exit_code": 0})
    status, data = _post(base_url, "/api/run", BAD)
    assert data["success"] is False and data["stage"] == "analyzer"
    assert _post(base_url, "/api/check", GOOD)[1]["success"] is True
    transpiled = _post(base_url, "/api/transpile", GOOD)[1]
    assert transpiled["success"] is True and "int main" in transpiled["c_code"]
    assert _post(base_url, "/api/ast", GOOD)[1]["success"] is True
    assert _post(base_url, "/api/tokens", GOOD)[1]["success"] is True
    presets = json.loads(fetch(base_url + "/api/presets")[2])
    assert "factorial" in presets
    assert fetch(base_url + "/api/unknown")[0] == 404


def test_input_does_not_block_the_server(base_url):
    code = "module main;\nfn main() {\n    let s = input();\n    print(s);\n}\n"
    status, data = _post(base_url, "/api/run", code)
    assert status == 200
    assert data["success"] is False and data["stage"] == "runtime"
