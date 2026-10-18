#!/usr/bin/env python3
"""test_check_links.py - Tests for check_links.py against a local HTTP server (loopback allowed only here)."""

import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))  # scripts/ holds the modules under test

import check_links
import fetch_media

_REAL_IS_PROHIBITED = fetch_media.is_prohibited_ip

ARTICLE = """<html><head><title>  Tháp Eiffel – Lịch sử  </title>
<meta property="article:published_time" content="2026-03-01T08:00:00+07:00">
<meta property="og:image" content="/img/eiffel.jpg">
<script type="application/ld+json">{"dateModified": "2026-09-30"}</script>
<style>.x{content:"hidden phrase"}</style></head>
<body><p>Tháp cao   330 mét</p><script>var s = "hidden phrase";</script></body></html>"""


class _Handler(BaseHTTPRequestHandler):
    routes = {}

    def do_GET(self):
        status, headers, body = self.routes.get(self.path, (404, {}, b"missing"))
        self.send_response(status)
        for k, v in {"Content-Type": "text/html; charset=utf-8", **headers}.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class AnalyzeHtml(unittest.TestCase):
    def test_title_dates_and_phrases(self):
        r = check_links.analyze_html(ARTICLE, ["330 MÉT", "hidden phrase", "500 mét"])
        self.assertEqual(r["title"], "Tháp Eiffel – Lịch sử")
        self.assertEqual(r["published"], "2026-03-01T08:00:00+07:00")
        self.assertEqual(r["modified"], "2026-09-30")
        self.assertEqual(r["image"], "/img/eiffel.jpg")
        self.assertFalse(r["soft_404"])
        # whitespace/case normalized; script and style text ignored
        self.assertEqual(r["found"], {"330 MÉT": True, "hidden phrase": False, "500 mét": False})

    def test_soft_404_title(self):
        self.assertTrue(check_links.analyze_html("<title>Không tìm thấy trang</title>")["soft_404"])
        self.assertTrue(check_links.analyze_html("<title>404 - Page Not Found</title>")["soft_404"])

    def test_time_tag_fallback_and_malformed(self):
        r = check_links.analyze_html('<title>A</title><time datetime="2025-12-01">x</time><div><p>broken')
        self.assertEqual(r["published"], "2025-12-01")

    def test_to_ascii_url(self):
        self.assertEqual(check_links.to_ascii_url("https://a.vn/file/9.Trịnh Thế.pdf?q=bánh chưng#x"),
                         "https://a.vn/file/9.Tr%E1%BB%8Bnh%20Th%E1%BA%BF.pdf?q=b%C3%A1nh%20ch%C6%B0ng")
        self.assertEqual(check_links.to_ascii_url("https://vi.wikipedia.org/wiki/B%C3%A1nh"),
                         "https://vi.wikipedia.org/wiki/B%C3%A1nh")
        self.assertEqual(check_links.to_ascii_url("http://bánh.vn:8080/x"), "http://xn--bnh-ela.vn:8080/x")

    def test_homepage_redirect(self):
        self.assertTrue(check_links.is_homepage_redirect("https://a.vn/tin/123", "https://a.vn/"))
        self.assertFalse(check_links.is_homepage_redirect("https://a.vn/", "https://a.vn/"))
        self.assertFalse(check_links.is_homepage_redirect("https://a.vn/tin/1", "https://a.vn/tin/2"))


class CheckUrlEndToEnd(unittest.TestCase):
    def setUp(self):
        handler = type("Handler", (_Handler,), {"routes": {}})
        self.routes = handler.routes
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        server.daemon_threads = True
        self.base = f"http://127.0.0.1:{server.server_address[1]}"
        threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        allow = patch.object(fetch_media, "is_prohibited_ip",
                             side_effect=lambda ip: False if str(ip) == "127.0.0.1" else _REAL_IS_PROHIBITED(ip))
        allow.start()
        self.addCleanup(allow.stop)

    def serve(self, path, body=b"", status=200, **headers):
        self.routes[path] = (status, headers, body)
        return self.base + path

    def test_ok_page(self):
        r = check_links.check_url(self.serve("/a", ARTICLE.encode()), ["330 mét"])
        self.assertEqual((r["verdict"], r["status"]), ("ok", 200))
        self.assertTrue(r["found"]["330 mét"])
        self.assertEqual(r["image"], self.base + "/img/eiffel.jpg")

    def test_dead_and_blocked(self):
        self.assertEqual(check_links.check_url(self.base + "/nope")["verdict"], "dead")
        r = check_links.check_url(self.serve("/f", b"no", status=403))
        self.assertEqual(r["verdict"], "blocked")
        self.assertIn("note", r)

    def test_soft_404(self):
        r = check_links.check_url(self.serve("/s", b"<title>Page not found</title>"))
        self.assertEqual(r["verdict"], "soft_404")

    def test_redirect_to_404_path_with_200(self):
        self.serve("/404.html", b"<title>Trang chu</title>")
        r = check_links.check_url(self.serve("/bai-viet-1", status=302, Location="/404.html"))
        self.assertEqual(r["verdict"], "soft_404")

    def test_gzip_body(self):
        import gzip
        r = check_links.check_url(self.serve("/g", gzip.compress(ARTICLE.encode()), **{"Content-Encoding": "gzip"}), ["330 mét"])
        self.assertEqual(r["title"], "Tháp Eiffel – Lịch sử")
        self.assertTrue(r["found"]["330 mét"])

    def test_redirect_to_homepage(self):
        self.serve("/", b"<title>Home</title>")
        r = check_links.check_url(self.serve("/old-article", status=301, Location="/"))
        self.assertEqual(r["verdict"], "homepage_redirect")

    def test_non_html_skips_phrases(self):
        r = check_links.check_url(self.serve("/p.pdf", b"%PDF-1.7", **{"Content-Type": "application/pdf"}), ["x"])
        self.assertEqual(r["verdict"], "ok")
        self.assertIn("note", r)

    def test_private_ip_refused_and_unresolvable_dead(self):
        self.assertEqual(check_links.check_url("http://10.0.0.1/x")["verdict"], "refused")
        self.assertEqual(check_links.check_url("ftp://example.com/x")["verdict"], "refused")
        self.assertEqual(check_links.check_url("http://no-such-host.invalid/x")["verdict"], "unreachable")

    def test_server_error_unreachable_and_thin_page_noted(self):
        self.assertEqual(check_links.check_url(self.serve("/e", b"x", status=504))["verdict"], "unreachable")
        r = check_links.check_url(self.serve("/js", b"<title>App</title><div id=root></div>"))
        self.assertEqual(r["verdict"], "ok")
        self.assertIn("JavaScript", r["note"])


if __name__ == "__main__":
    unittest.main()
