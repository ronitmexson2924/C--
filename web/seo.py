"""
Page rendering and search-engine metadata for the C-- web studio.

Every public page is rendered server-side from ``templates/layout.html`` plus a
content fragment in ``content/``, so crawlers receive complete, unique HTML for
each URL. This module also produces robots.txt, sitemap.xml, the web app
manifest, and schema.org JSON-LD. Standard library only.
"""

from __future__ import annotations

import base64
import datetime as _dt
import hashlib
import html
import json
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

WEB_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = WEB_DIR / "templates"
CONTENT_DIR = WEB_DIR / "content"

DEFAULT_SITE_URL = "https://web-production-c8ddc.up.railway.app"
SITE_URL = os.environ.get("SITE_URL", DEFAULT_SITE_URL).rstrip("/")

SITE_NAME = "C-- (C Minus Minus)"
REPO_URL = "https://github.com/ronitmexson2924/C--"
SPEC_PDF_PATH = "/document/C_Minus_Minus_Language_Specification_and_Compiler_Report.pdf"
OG_IMAGE_PATH = "/assets/og-image.png"
OG_IMAGE_SIZE = (1200, 630)
SOFTWARE_VERSION = "0.2.0"
DATE_PUBLISHED = "2026-09-21"  # first commit of the project

AUTHORS = ["Ronit Mexson", "Mit Kumar Raju Panchal", "Garv Gupta"]
ADVISOR = "Prof. Hariharan R L"


@dataclass(frozen=True)
class Page:
    path: str
    tab: str             # view id suffix used by the client (view-<tab>)
    content: str         # fragment file in content/
    title: str
    description: str
    crumb: str
    article: bool = False
    priority: str = "0.8"


PAGES: List[Page] = [
    Page(
        path="/", tab="overview", content="home.html", crumb="Home", priority="1.0",
        title="C-- (C Minus Minus) – Memory-Safe Systems Programming Language",
        description="C-- (C Minus Minus) is a memory-safe, statically typed systems language with no pointers or null. "
                    "Run it online, read the guide, or transpile to C99.",
    ),
    Page(
        path="/playground", tab="playground", content="playground.html", crumb="Playground", priority="0.9",
        title="C-- Online Playground & Compiler Explorer | C Minus Minus",
        description="Write and run C-- (C Minus Minus) code in your browser. Inspect tokens and the AST, see live "
                    "diagnostics, and transpile programs to ISO C99.",
    ),
    Page(
        path="/architecture", tab="features", content="architecture.html", crumb="Architecture", article=True,
        title="C-- Language Architecture & Safety Guarantees | C Minus Minus",
        description="The six invariants behind C--: memory safety, deep-copy value semantics, immutability by default, "
                    "precise diagnostics, and two execution backends.",
    ),
    Page(
        path="/pipeline", tab="pipeline", content="pipeline.html", crumb="Pipeline", article=True,
        title="C-- Compiler Pipeline: Lexer, Parser & Analyzer | C Minus Minus",
        description="How the C-- compiler works: a handwritten lexer, recursive descent Pratt parser, semantic "
                    "analyzer, reference interpreter and ISO C99 transpiler.",
    ),
    Page(
        path="/reference", tab="syntax", content="reference.html", crumb="Reference", article=True,
        title="C-- Language Reference & Syntax Guide | C Minus Minus",
        description="C-- syntax by example: bindings, functions, arrays, lists, stacks, queues, switch and loops. "
                    "Open any snippet in the online playground and run it.",
    ),
    Page(
        path="/about", tab="about", content="about.html", crumb="About", priority="0.6",
        title="About C-- (C Minus Minus) – Team, Advisor & FAQ",
        description="Meet the team behind C-- (C Minus Minus), a compiler design project at SCOPE, and get answers "
                    "to common questions about the memory-safe language.",
    ),
]

PAGES_BY_PATH: Dict[str, Page] = {p.path: p for p in PAGES}

NOT_FOUND = Page(
    path="/404", tab="notfound", content="404.html", crumb="Not found",
    title="Page not found | C-- (C Minus Minus)",
    description="The page you requested does not exist on the C-- (C Minus Minus) website.",
)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def absolute(path: str) -> str:
    return SITE_URL + path


def _attr(value: str) -> str:
    return html.escape(value, quote=True)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _mtime_date(path: Path) -> str:
    return _dt.datetime.fromtimestamp(path.stat().st_mtime, _dt.timezone.utc).date().isoformat()


def asset_version(name: str) -> str:
    """Short content hash used to cache-bust web/<name>."""
    return _file_hash(WEB_DIR / name, (WEB_DIR / name).stat().st_mtime_ns)


@lru_cache(maxsize=64)
def _file_hash(path: Path, _mtime: int) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:10]


def _json_ld(data: Any) -> str:
    text = json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")
    return f'    <script type="application/ld+json">\n{text}\n    </script>'


def _strip_tags(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


# ---------------------------------------------------------------------------
# Structured data
# ---------------------------------------------------------------------------

def _persons() -> List[Dict[str, str]]:
    return [{"@type": "Person", "name": name} for name in AUTHORS]


def _site_graph() -> List[Dict[str, Any]]:
    return [
        {
            "@type": "WebSite",
            "@id": absolute("/#website"),
            "url": absolute("/"),
            "name": SITE_NAME,
            "alternateName": ["C Minus Minus", "Cmm", "C-- programming language"],
            "inLanguage": "en",
            "publisher": {"@id": absolute("/#organization")},
        },
        {
            "@type": "Organization",
            "@id": absolute("/#organization"),
            "name": "C-- (C Minus Minus) Project",
            "url": absolute("/"),
            "logo": absolute("/assets/cmm-icon-512.png"),
            "sameAs": [REPO_URL],
            "member": _persons(),
        },
    ]


def faq_entries() -> List[Dict[str, str]]:
    """Questions and answers exactly as they appear on the About page."""
    text = _read(CONTENT_DIR / "about.html")
    items = re.findall(r'<h3 class="faq-q">(.*?)</h3>.*?<p class="faq-a">(.*?)</p>', text, re.S)
    return [{"question": _strip_tags(q), "answer": _strip_tags(a)} for q, a in items]


def structured_data(page: Page) -> str:
    graph = _site_graph()
    if page.path == "/":
        graph.append({
            "@type": "SoftwareApplication",
            "@id": absolute("/#software"),
            "name": SITE_NAME,
            "alternateName": "C Minus Minus",
            "description": page.description,
            "url": absolute("/"),
            "applicationCategory": "DeveloperApplication",
            "applicationSubCategory": "Programming language",
            "operatingSystem": "Windows, macOS, Linux",
            "softwareVersion": SOFTWARE_VERSION,
            "license": "https://opensource.org/licenses/MIT",
            "downloadUrl": REPO_URL,
            "codeRepository": REPO_URL,
            "programmingLanguage": "Python",
            "image": absolute(OG_IMAGE_PATH),
            "author": _persons(),
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
        })
    if page.article:
        graph.append({
            "@type": "TechArticle",
            "headline": page.title.split(" | ")[0],
            "description": page.description,
            "url": absolute(page.path),
            "mainEntityOfPage": absolute(page.path),
            "image": absolute(OG_IMAGE_PATH),
            "author": _persons(),
            "publisher": {"@id": absolute("/#organization")},
            "datePublished": DATE_PUBLISHED,
            "dateModified": _mtime_date(CONTENT_DIR / page.content),
            "inLanguage": "en",
        })
    if page.path == "/about":
        graph.append({
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": e["question"],
                 "acceptedAnswer": {"@type": "Answer", "text": e["answer"]}}
                for e in faq_entries()
            ],
        })
    if page.path != "/" and page.path in PAGES_BY_PATH:
        graph.append({
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": absolute("/")},
                {"@type": "ListItem", "position": 2, "name": page.crumb, "item": absolute(page.path)},
            ],
        })
    return _json_ld({"@context": "https://schema.org", "@graph": graph})


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------

def _head(page: Page, indexable: bool) -> str:
    title = _attr(page.title)
    desc = _attr(page.description)
    url = _attr(absolute(page.path))
    image = _attr(absolute(OG_IMAGE_PATH))
    robots = "index, follow, max-image-preview:large, max-snippet:-1" if indexable else "noindex, follow"
    lines = [
        f"    <title>{title}</title>",
        f'    <meta name="description" content="{desc}">',
        f'    <meta name="robots" content="{robots}">',
    ]
    if indexable:
        lines.append(f'    <link rel="canonical" href="{url}">')
    lines += [
        '    <meta property="og:type" content="website">',
        f'    <meta property="og:site_name" content="{_attr(SITE_NAME)}">',
        f'    <meta property="og:title" content="{title}">',
        f'    <meta property="og:description" content="{desc}">',
        f'    <meta property="og:url" content="{url}">',
        f'    <meta property="og:image" content="{image}">',
        f'    <meta property="og:image:width" content="{OG_IMAGE_SIZE[0]}">',
        f'    <meta property="og:image:height" content="{OG_IMAGE_SIZE[1]}">',
        '    <meta property="og:image:alt" content="C-- (C Minus Minus): memory safety by removal, not by runtime.">',
        '    <meta property="og:locale" content="en_US">',
        '    <meta name="twitter:card" content="summary_large_image">',
        f'    <meta name="twitter:title" content="{title}">',
        f'    <meta name="twitter:description" content="{desc}">',
        f'    <meta name="twitter:image" content="{image}">',
    ]
    google = os.environ.get("GOOGLE_SITE_VERIFICATION", "").strip()
    bing = os.environ.get("BING_SITE_VERIFICATION", "").strip()
    if google:
        lines.append(f'    <meta name="google-site-verification" content="{_attr(google)}">')
    if bing:
        lines.append(f'    <meta name="msvalidate.01" content="{_attr(bing)}">')
    return "\n".join(lines)


def _mark_active_nav(document: str, tab: str) -> str:
    path = _path_for_tab(tab)
    old = f'<a class="nav-tab" href="{path}" data-tab="{tab}" id="tab-btn-{tab}">'
    new = f'<a class="nav-tab active" href="{path}" data-tab="{tab}" id="tab-btn-{tab}" aria-current="page">'
    return document.replace(old, new, 1)


def _path_for_tab(tab: str) -> str:
    for p in PAGES:
        if p.tab == tab:
            return p.path
    return ""


def _activate(section_html: str) -> str:
    return section_html.replace('class="tab-view"', 'class="tab-view active"', 1)


def render_page(page: Page, indexable: bool = True) -> str:
    layout = _read(TEMPLATE_DIR / "layout.html")
    playground = _read(CONTENT_DIR / "playground.html")
    is_playground = page.tab == "playground"
    playground = playground.replace("{{@PLAYGROUND_HEADING}}", "h1" if is_playground else "h2")

    sections = [_activate(playground) if is_playground else playground]
    if not is_playground:
        sections.append(_activate(_read(CONTENT_DIR / page.content)))

    out = layout.replace("{{@HEAD}}", _head(page, indexable))
    out = out.replace("{{@JSONLD}}", structured_data(page) if indexable else "")
    out = out.replace("{{@SECTIONS}}", "\n".join(s.rstrip("\n") for s in sections))
    for name in ("style.css", "app.js"):
        out = out.replace(f"{{{{@ASSET:{name}}}}}", f"/{name}?v={asset_version(name)}")
    return _mark_active_nav(out, page.tab)


def inline_script_hashes(document: str) -> List[str]:
    """CSP hashes for executable inline <script> blocks in a rendered page."""
    hashes = []
    for attrs, body in re.findall(r"<script([^>]*)>(.*?)</script>", document, re.S):
        if "src=" in attrs or "application/ld+json" in attrs:
            continue
        digest = hashlib.sha256(body.encode("utf-8")).digest()
        hashes.append("'sha256-" + base64.b64encode(digest).decode("ascii") + "'")
    return hashes


# ---------------------------------------------------------------------------
# Crawl infrastructure
# ---------------------------------------------------------------------------

def robots_txt() -> str:
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "\n"
        f"Sitemap: {absolute('/sitemap.xml')}\n"
    )


def sitemap_xml(repo_root: Path) -> str:
    entries = []
    for page in PAGES:
        entries.append((absolute(page.path), _mtime_date(CONTENT_DIR / page.content), page.priority))
    pdf = repo_root / SPEC_PDF_PATH.lstrip("/")
    if pdf.is_file():
        entries.append((absolute(SPEC_PDF_PATH), _mtime_date(pdf), "0.5"))
    urls = "".join(
        f"  <url>\n    <loc>{html.escape(loc)}</loc>\n    <lastmod>{lastmod}</lastmod>\n"
        f"    <priority>{priority}</priority>\n  </url>\n"
        for loc, lastmod, priority in entries
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}</urlset>\n"
    )


def web_manifest() -> str:
    return json.dumps({
        "name": SITE_NAME,
        "short_name": "C--",
        "description": PAGES_BY_PATH["/"].description,
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#09090b",
        "theme_color": "#09090b",
        "icons": [
            {"src": "/assets/cmm-icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/assets/cmm-icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/assets/cmm-icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }, indent=2)


def google_verification_file(path: str) -> Optional[str]:
    """Body for an HTML-file Search Console verification, if configured."""
    name = os.environ.get("GOOGLE_SITE_VERIFICATION_FILE", "").strip().lstrip("/")
    if name and re.fullmatch(r"google[0-9a-f]+\.html", name) and path == "/" + name:
        return f"google-site-verification: {name}"
    return None
