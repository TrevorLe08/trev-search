#!/usr/bin/env python3
"""
test_fetch_e2e.py - End-to-end tests for fetch_media.py using a local HTTP server.

The test server listens on 127.0.0.1, which fetch_media blocks by design. These tests allow
only that loopback address by patching is_prohibited_ip; every other check (redirect
validation, cloud-metadata IPs, content type, file signatures, dimensions, size caps,
filename handling and CLI output) runs unmodified through urllib.

Run from this directory:  python -B -m unittest -v test_fetch_e2e
"""

import contextlib
import hashlib
import io
import json
import os
import shutil
import struct
import sys
import tempfile
import threading
import unittest
import urllib.error
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))  # scripts/ holds the modules under test

import fetch_media

_REAL_IS_PROHIBITED = fetch_media.is_prohibited_ip


def _allow_loopback_only(ip):
    if str(ip) == "127.0.0.1":
        return False
    return _REAL_IS_PROHIBITED(ip)


def _chunk(tag, data):
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def make_png(width=64, height=48, between=b"", trailer=b""):
    """Build a PNG. Pixel data is real only for small images; large declared sizes just lie in IHDR."""
    if width * height <= 64 * 64:
        raw = b"".join(b"\x00" + b"\x10\x20\x30" * width for _ in range(height))
    else:
        raw = b"\x00"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + between
        + _chunk(b"IDAT", zlib.compress(raw))
        + _chunk(b"IEND", b"")
        + trailer
    )


class _Handler(BaseHTTPRequestHandler):
    routes = {}

    def do_GET(self):
        route = self.routes.get(self.path)
        if route is None:
            self.send_error(404)
            return
        status, headers, body = route
        self.send_response(status)
        length = headers.get("Content-Length", "auto")
        if length == "auto":
            self.send_header("Content-Length", str(len(body)))
        elif length is not None:  # None means: send no Content-Length at all
            self.send_header("Content-Length", length)
        for key, value in headers.items():
            if key != "Content-Length":
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        # The client may abort on purpose (size caps); do not print server-side tracebacks.
        pass


class FetchMediaEndToEnd(unittest.TestCase):
    def setUp(self):
        self.dest = tempfile.mkdtemp(prefix="test_fetch_e2e_")
        handler = type("Handler", (_Handler,), {"routes": {}})
        self.routes = handler.routes
        self.server = _Server(("127.0.0.1", 0), handler)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        patcher = patch.object(fetch_media, "is_prohibited_ip", side_effect=_allow_loopback_only)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(shutil.rmtree, self.dest, True)
        self.addCleanup(self._stop_server)

    def _stop_server(self):
        self.server.shutdown()
        self.server.server_close()

    def serve(self, path, body, content_type="image/png", status=200, **headers):
        self.routes[path] = (status, {"Content-Type": content_type, **headers}, body)
        return self.base + path

    def assert_blocked(self, url, reason):
        with self.assertRaises(ValueError) as ctx:
            fetch_media.fetch_image_securely(url, self.dest)
        self.assertTrue(str(ctx.exception).startswith(reason), str(ctx.exception))
        self.assertEqual(os.listdir(self.dest), [], "no file or temp file may remain after a rejection")

    # ---- success paths ----
    def test_valid_png_is_saved_with_hashed_name(self):
        png = make_png(64, 48)
        url = self.serve("/ok.png", png)
        result = fetch_media.fetch_image_securely(url, self.dest)
        expected_name = "media_" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:16] + ".png"
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["filename"], expected_name)
        self.assertEqual(result["dimensions"], "64x48")
        self.assertEqual(result["size_bytes"], len(png))
        self.assertEqual(os.listdir(self.dest), [expected_name])
        with open(os.path.join(self.dest, expected_name), "rb") as handle:
            self.assertEqual(handle.read(), png)

    def test_vietnamese_and_space_characters_in_url_are_encoded(self):
        self.serve("/%E1%BA%A3nh%20th%C3%A1p.png", make_png())  # what the server receives for "/ảnh tháp.png"
        result = fetch_media.fetch_image_securely(self.base + "/ảnh tháp.png", self.dest)
        self.assertEqual(result["status"], "success")

    def test_octet_stream_content_type_with_valid_png_is_accepted(self):
        url = self.serve("/blob", make_png(), content_type="application/octet-stream")
        self.assertEqual(fetch_media.fetch_image_securely(url, self.dest)["extension"], "png")

    def test_png_with_xmp_xml_metadata_is_accepted(self):
        xmp = b"XML:com.adobe.xmp\x00\x00\x00\x00\x00" + b'<?xml version="1.0"?><x:xmpmeta xmlns:x="adobe:ns:meta/"/>'
        url = self.serve("/xmp.png", make_png(between=_chunk(b"iTXt", xmp)))
        self.assertEqual(fetch_media.fetch_image_securely(url, self.dest)["status"], "success")

    def test_redirect_to_allowed_address_is_followed(self):
        self.serve("/final.png", make_png())
        self.routes["/start"] = (302, {"Location": "/final.png"}, b"")
        result = fetch_media.fetch_image_securely(self.base + "/start", self.dest)
        self.assertEqual(result["original_url"], self.base + "/start")
        self.assertEqual(result["status"], "success")

    def test_repeat_fetch_of_same_url_keeps_one_file(self):
        url = self.serve("/again.png", make_png())
        first = fetch_media.fetch_image_securely(url, self.dest)
        second = fetch_media.fetch_image_securely(url, self.dest)
        self.assertEqual(first["filename"], second["filename"])
        self.assertEqual(len(os.listdir(self.dest)), 1)

    # ---- content rejections ----
    def test_html_content_type_is_rejected(self):
        self.assert_blocked(self.serve("/page", b"<html>x</html>", content_type="text/html"), "INVALID_CONTENT_TYPE")

    def test_svg_content_type_is_rejected(self):
        self.assert_blocked(self.serve("/a.svg", b"<svg/>", content_type="image/svg+xml"), "INVALID_CONTENT_TYPE")

    def test_svg_body_served_as_png_is_rejected(self):
        body = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
        self.assert_blocked(self.serve("/fake.png", body), "INVALID_MAGIC_BYTES")

    def test_html_body_served_as_png_is_rejected(self):
        self.assert_blocked(self.serve("/x.png", b"<!DOCTYPE html><script>alert(1)</script>"), "INVALID_MAGIC_BYTES")

    def test_script_marker_inside_valid_png_is_still_rejected(self):
        poly = make_png(between=_chunk(b"tEXt", b"Comment\x00<script>alert(1)</script>"))
        self.assert_blocked(self.serve("/poly.png", poly), "INVALID_MAGIC_BYTES")

    def test_empty_body_is_rejected(self):
        self.assert_blocked(self.serve("/empty.png", b""), "EMPTY_RESPONSE")

    # ---- size and dimension limits ----
    def test_declared_dimensions_over_limit_are_rejected(self):
        self.assert_blocked(self.serve("/huge.png", make_png(9000, 9000)), "DECOMPRESSION_BOMB")

    def test_declared_content_length_over_cap_is_rejected(self):
        url = self.serve("/big.png", b"", **{"Content-Length": str(fetch_media.MAX_IMAGE_SIZE + 1)})
        self.assert_blocked(url, "OVERSIZED_PAYLOAD")

    def test_streamed_body_over_cap_is_rejected_without_content_length(self):
        body = make_png(64, 48, trailer=b"\x00" * 8000)
        url = self.serve("/stream.png", body, **{"Content-Length": None})
        with patch.object(fetch_media, "MAX_IMAGE_SIZE", 2048), patch.object(fetch_media, "CHUNK_SIZE", 512):
            self.assert_blocked(url, "OVERSIZED_PAYLOAD")

    # ---- redirects and errors ----
    def test_redirect_to_cloud_metadata_is_blocked(self):
        self.routes["/r"] = (302, {"Location": "http://169.254.169.254/latest/meta-data"}, b"")
        self.assert_blocked(self.base + "/r", "SSRF_BLOCKED")

    def test_redirect_to_non_http_scheme_is_refused(self):
        self.routes["/r"] = (302, {"Location": "file:///etc/passwd"}, b"")
        with self.assertRaises((ValueError, urllib.error.URLError)):
            fetch_media.fetch_image_securely(self.base + "/r", self.dest)
        self.assertEqual(os.listdir(self.dest), [])

    def test_redirect_loop_is_refused(self):
        self.routes["/loop"] = (302, {"Location": "/loop"}, b"")
        with self.assertRaises(urllib.error.HTTPError):
            fetch_media.fetch_image_securely(self.base + "/loop", self.dest)

    def test_http_404_is_an_error(self):
        with self.assertRaises(urllib.error.HTTPError):
            fetch_media.fetch_image_securely(self.base + "/missing.png", self.dest)

    def test_loopback_is_blocked_when_the_test_allowance_is_removed(self):
        url = self.serve("/ok.png", make_png())
        with patch.object(fetch_media, "is_prohibited_ip", _REAL_IS_PROHIBITED):
            with self.assertRaises(ValueError) as ctx:
                fetch_media.fetch_image_securely(url, self.dest)
        self.assertTrue(str(ctx.exception).startswith("SSRF_BLOCKED"))

    # ---- command line ----
    def run_cli(self, url):
        out = io.StringIO()
        with patch.object(sys, "argv", ["fetch_media.py", "--url", url, "--dest", self.dest]):
            with contextlib.redirect_stdout(out):
                code = fetch_media.main()
        return code, json.loads(out.getvalue())

    def test_cli_success_prints_json_and_returns_zero(self):
        code, payload = self.run_cli(self.serve("/cli.png", make_png()))
        self.assertEqual(code, 0)
        self.assertEqual(payload["status"], "success")
        self.assertTrue(os.path.exists(payload["local_path"]))

    def test_cli_error_prints_reason_and_returns_one(self):
        code, payload = self.run_cli(self.serve("/cli.html", b"<html></html>", content_type="text/html"))
        self.assertEqual(code, 1)
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["reason"], "INVALID_CONTENT_TYPE")


if __name__ == "__main__":
    unittest.main()
