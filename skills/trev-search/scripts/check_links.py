#!/usr/bin/env python3
"""
check_links.py - Verify that cited links exist and report what they are, for trev-search.

For each URL: HTTP status, final URL after redirects, page title, published/modified dates
and lead image (og:image) found in page metadata, and optional phrase matches. Uses fetch_media's SSRF-safe opener
(public http/https only, IP-pinned connections, every redirect re-validated).

Usage:
    python check_links.py URL [URL ...] [--file urls.txt] [--find "phrase" ...]

Prints a JSON list to stdout. A "found": false only means the phrase is not in the static
HTML; the page may render it with JavaScript, so open the page before calling a claim unsupported.
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser

from fetch_media import REQUEST_TIMEOUT, build_secure_opener, to_ascii_url, validate_url_and_check_ssrf

MAX_PAGE_BYTES = 2 * 1024 * 1024
MAX_WORKERS = 8
MIN_TEXT_CHARS = 1500

PUBLISHED_KEYS = ("article:published_time", "datepublished", "date", "pubdate", "publishdate",
                  "dc.date", "dc.date.issued", "citation_publication_date", "og:published_time")
MODIFIED_KEYS = ("article:modified_time", "datemodified", "og:updated_time", "last-modified", "dc.date.modified")
SOFT_404_PATH = re.compile(r"(^|[/_.-])(404|not-?found|error)([/_.-]|$)", re.IGNORECASE)
SOFT_404_TITLE = re.compile(
    r"\b404\b|not found|page not found|không tìm thấy|trang không tồn tại|error page|lỗi 404", re.IGNORECASE
)
JSONLD_DATE = re.compile(r'"(datePublished|dateModified)"\s*:\s*"([^"]+)"')
DEAD_CODES = {404, 410}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.meta = {}
        self.time_datetime = ""
        self.text = []
        self._in_title = False
        self._skip = 0
        self._jsonld = False
        self.jsonld = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            key = (a.get("property") or a.get("name") or a.get("itemprop") or a.get("http-equiv") or "").lower()
            if key and a.get("content") and key not in self.meta:
                self.meta[key] = a["content"].strip()
        elif tag == "time" and a.get("datetime") and not self.time_datetime:
            self.time_datetime = a["datetime"].strip()
        elif tag in ("script", "style", "noscript"):
            self._skip += 1
            self._jsonld = tag == "script" and "ld+json" in a.get("type", "")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in ("script", "style", "noscript") and self._skip:
            self._skip -= 1
            self._jsonld = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif self._jsonld:
            self.jsonld.append(data)
        elif not self._skip:
            self.text.append(data)


def normalize(s):
    return " ".join(s.split()).casefold()


def first_meta(meta, keys):
    return next((meta[k] for k in keys if meta.get(k)), "")


def analyze_html(html, phrases=()):
    """Extract title, dates, soft-404 hint and phrase matches from an HTML string."""
    p = PageParser()
    try:
        p.feed(html)
        p.close()
    except Exception:  # malformed HTML: keep whatever was parsed
        pass
    title = " ".join(p.title.split()) or p.meta.get("og:title", "")
    jsonld = dict((k.lower(), v) for k, v in JSONLD_DATE.findall(" ".join(p.jsonld)))
    published = first_meta(p.meta, PUBLISHED_KEYS) or jsonld.get("datepublished", "") or p.time_datetime
    modified = first_meta(p.meta, MODIFIED_KEYS) or jsonld.get("datemodified", "")
    body = normalize(" ".join(p.text))
    return {
        "title": title,
        "published": published,
        "modified": modified,
        "image": p.meta.get("og:image") or p.meta.get("og:image:url") or p.meta.get("twitter:image", ""),
        "soft_404": bool(title and SOFT_404_TITLE.search(title)),
        "found": {ph: normalize(ph) in body for ph in phrases},
        "text_chars": len(body),
    }


def decode_body(raw, encoding):
    """Undo gzip/deflate, capped at MAX_PAGE_BYTES of output (guards against compression bombs)."""
    encoding = encoding.lower().strip()
    if encoding in ("gzip", "x-gzip"):
        return zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(raw, MAX_PAGE_BYTES)
    if encoding == "deflate":
        try:
            return zlib.decompressobj().decompress(raw, MAX_PAGE_BYTES)
        except zlib.error:  # some servers send raw deflate without the zlib header
            return zlib.decompressobj(-zlib.MAX_WBITS).decompress(raw, MAX_PAGE_BYTES)
    return raw


def is_homepage_redirect(url, final_url):
    src, dst = urllib.parse.urlparse(url), urllib.parse.urlparse(final_url)
    return src.path.strip("/") != "" and dst.path.strip("/") == "" and not dst.query


def check_url(url, phrases=()):
    result = {"url": url, "verdict": "unreachable", "status": None, "final_url": None}
    try:
        target = to_ascii_url(url)
        validate_url_and_check_ssrf(target)
        req = urllib.request.Request(target, headers={
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 TrevSearchLinkCheck/1.0"),
            "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.5",
            "Accept-Language": "vi,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
        })
        with build_secure_opener().open(req, timeout=REQUEST_TIMEOUT) as resp:
            result["status"] = resp.status
            result["final_url"] = resp.geturl()
            ctype = resp.headers.get("Content-Type", "").lower()
            result["content_type"] = ctype.split(";")[0].strip()
            result["last_modified_header"] = resp.headers.get("Last-Modified", "")
            raw = decode_body(resp.read(MAX_PAGE_BYTES), resp.headers.get("Content-Encoding", ""))
    except urllib.error.HTTPError as e:
        e.close()
        result["status"] = e.code
        result["verdict"] = "dead" if e.code in DEAD_CODES else "unreachable" if e.code >= 500 else "blocked"
        if result["verdict"] == "blocked":
            result["note"] = "Site refused the script (bot block, login or paywall); open it with a page-reading tool before calling it dead."
        return result
    except ValueError as e:  # fetch_media raises ValueError for DNS failure and SSRF blocks
        # DNS failure: a made-up domain, or a real site down right now; the script cannot tell which
        result["verdict"] = "unreachable" if "DNS_RESOLUTION_FAILED" in str(e) else "refused"
        result["error"] = str(e)
        return result
    except urllib.error.URLError as e:
        reason = str(e.reason)
        result["error"] = reason
        return result
    except Exception as e:  # timeouts, TLS and connection errors
        result["error"] = f"{type(e).__name__}: {e}"
        return result

    result["verdict"] = "ok"
    if result["content_type"] in ("text/html", "application/xhtml+xml", ""):
        charset = re.search(r"charset=([\w-]+)", ctype)
        html = raw.decode(charset.group(1) if charset else "utf-8", errors="replace")
        result.update(analyze_html(html, phrases))
        if result["image"]:  # the page's own lead image, absolute, for fetch_media.py
            result["image"] = urllib.parse.urljoin(result["final_url"], result["image"])
        result["soft_404"] = result["soft_404"] or bool(SOFT_404_PATH.search(urllib.parse.urlparse(result["final_url"]).path))
        if result["soft_404"]:
            result["verdict"] = "soft_404"
        elif result["text_chars"] < MIN_TEXT_CHARS:
            result["note"] = "Little text in the HTML (likely rendered by JavaScript); read it with a browser before citing."
    elif phrases:
        result["note"] = "Not HTML (e.g. PDF); phrases not checked, open it with a document reader."
    if is_homepage_redirect(url, result["final_url"]):
        result["verdict"] = "homepage_redirect"
    return result


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Check that links exist and what they are (trev-search).")
    parser.add_argument("urls", nargs="*", help="URLs to check")
    parser.add_argument("--file", help="Text file with one URL per line")
    parser.add_argument("--find", action="append", default=[], help="Phrase to look for in each page (repeatable)")
    args = parser.parse_args()

    urls = list(args.urls)
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            urls += [line.strip() for line in f if line.strip() and not line.startswith("#")]
    urls = list(dict.fromkeys(urls))
    if not urls:
        parser.error("no URLs given")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        results = list(pool.map(lambda u: check_url(u, args.find), urls))
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
