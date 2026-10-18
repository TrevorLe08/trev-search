#!/usr/bin/env python3
"""
fetch_media.py - Secure Local Image Fetcher & Verification Tool
Part of the trev-search skill.

Implements Defense-in-Depth against malicious image URLs:
1. Anti-SSRF & DNS Rebinding Immunity: Socket-level IP pinning and re-validation on all HTTP 30x redirects.
2. Scheme Whitelist: Only http and https permitted.
3. Pre-flight Header Checks: Validates Content-Type and Content-Length.
4. Magic Bytes Inspection: Verifies genuine bitmap image signatures (JPEG, PNG, WebP, GIF);
   strictly rejects Windows PE (MZ), Linux ELF, shell scripts, HTML/JS, and SVG (XML XSS/XXE vector).
5. Decompression Bomb / Pixel Flood Defense: Extracts dimensions via struct.unpack directly from headers,
   strictly rejecting images exceeding max width/height/megapixels before buffering.
6. Streaming Size Guard: Hard limit at 10MB to prevent infinite streams and disk exhaustion.
7. Filename Sanitization: Generates deterministic SHA-256 filenames, discarding server-provided names.
"""

import argparse
import hashlib
import http.client
import ipaddress
import json
import os
import socket
import struct
import sys
import urllib.parse
import urllib.request
from typing import Optional, Tuple, Union

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB limit
CHUNK_SIZE = 64 * 1024  # 64 KB per chunk
REQUEST_TIMEOUT = 10  # 10 seconds

# Pixel flood & decompression bomb limits (Chromium Webview protection)
MAX_IMAGE_WIDTH = 8192
MAX_IMAGE_HEIGHT = 8192
MAX_IMAGE_PIXELS = 8192 * 8192  # ~67.1 Megapixels

# Bitmap formats only: strictly eliminates SVG to prevent XSS / XXE in webviews
ALLOWED_MIME_PREFIXES = (
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
)

DENIED_SIGNATURES = (
    b"MZ",  # Windows PE binary (.exe, .dll, .sys)
    b"\x7fELF",  # Linux ELF binary
    b"PK\x03\x04",  # Zip / JAR / APK
    b"Rar!\x1a\x07",  # RAR archive
    b"#!\x2f",  # Unix shell script shebang
)

BLOCKED_METADATA_IPS = {
    "169.254.169.254",  # AWS/GCP/Azure link-local metadata
    "169.254.170.2",  # AWS ECS container credentials
    "100.100.100.200",  # Alibaba Cloud metadata
}


def is_prohibited_ip(ip: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]) -> bool:
    """Check if an IP address is private, loopback, link-local, cloud metadata, or non-global."""
    # Unwrap IPv4-mapped IPv6 address (e.g. ::ffff:127.0.0.1 -> 127.0.0.1)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped

    if str(ip) in BLOCKED_METADATA_IPS:
        return True

    # Check 6to4 encapsulation (2002::/16)
    if isinstance(ip, ipaddress.IPv6Address) and getattr(ip, "sixtofour", None):
        if is_prohibited_ip(ip.sixtofour):
            return True

    # Check Teredo encapsulation (2001::/32)
    if isinstance(ip, ipaddress.IPv6Address) and getattr(ip, "teredo", None):
        if is_prohibited_ip(ip.teredo[1]):
            return True

    return (
        not ip.is_global
        or ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_unspecified
        or ip.is_reserved
    )


def parse_and_validate_ip_literal(hostname: str) -> Optional[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
    """Parse direct IP literals, including integer and hex formats, and check against SSRF."""
    try:
        ip = ipaddress.ip_address(hostname)
        if is_prohibited_ip(ip):
            raise ValueError(f"SSRF_BLOCKED: Prohibited IP address '{hostname}'.")
        return ip
    except ValueError as e:
        if "SSRF_BLOCKED" in str(e):
            raise

    # Check decimal dword integer IP (e.g. 2130706433 -> 127.0.0.1)
    if hostname.isdigit():
        try:
            val = int(hostname)
            if 0 <= val <= 0xFFFFFFFF:
                ip = ipaddress.ip_address(val)
                if is_prohibited_ip(ip):
                    raise ValueError(f"SSRF_BLOCKED: Prohibited integer IP address '{hostname}' ({ip}).")
                return ip
        except ValueError as e:
            if "SSRF_BLOCKED" in str(e):
                raise

    # Check hex IP (e.g. 0x7f000001)
    if hostname.lower().startswith("0x"):
        try:
            val = int(hostname, 16)
            if 0 <= val <= 0xFFFFFFFF:
                ip = ipaddress.ip_address(val)
                if is_prohibited_ip(ip):
                    raise ValueError(f"SSRF_BLOCKED: Prohibited hexadecimal IP address '{hostname}' ({ip}).")
                return ip
        except ValueError as e:
            if "SSRF_BLOCKED" in str(e):
                raise

    return None


def resolve_and_validate_host(hostname: str, port: int) -> str:
    """
    Resolve hostname and verify that ALL returned IP addresses are public and safe.
    Returns the first validated IP address string for socket pinning (DNS rebinding prevention).
    """
    literal_ip = parse_and_validate_ip_literal(hostname)
    if literal_ip is not None:
        return str(literal_ip)

    try:
        addr_info = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise ValueError(f"DNS_RESOLUTION_FAILED: Could not resolve hostname '{hostname}': {exc}")

    if not addr_info:
        raise ValueError(f"DNS_RESOLUTION_FAILED: No IP addresses returned for '{hostname}'.")

    validated_ips = []
    for family, socktype, proto, canonname, sockaddr in addr_info:
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            raise ValueError(f"SSRF_BLOCKED: Invalid IP address returned from DNS: '{ip_str}'.")

        if is_prohibited_ip(ip):
            raise ValueError(f"SSRF_BLOCKED: Hostname '{hostname}' resolved to prohibited address '{ip_str}'.")
        validated_ips.append(ip_str)

    return validated_ips[0]


def to_ascii_url(url):
    """Percent-encode non-ASCII characters and spaces (common in Vietnamese URLs); keep existing escapes."""
    parts = urllib.parse.urlsplit(url.strip())
    host = parts.hostname.encode("idna").decode("ascii") if parts.hostname else ""
    netloc = host + (f":{parts.port}" if parts.port else "")
    safe = "/%:@!$&'()*+,;=-._~"
    return urllib.parse.urlunsplit((parts.scheme, netloc, urllib.parse.quote(parts.path, safe=safe),
                                    urllib.parse.quote(parts.query, safe=safe + "?"), ""))


def validate_url_and_check_ssrf(url: str) -> None:
    """Ensure URL is http/https and does not resolve to internal/private/metadata IP space."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise ValueError(f"SSRF_BLOCKED: Protocol '{parsed.scheme}' not allowed. Only http/https supported.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("SSRF_BLOCKED: URL does not specify a valid hostname.")

    port = parsed.port or (443 if parsed.scheme.lower() == "https" else 80)
    resolve_and_validate_host(hostname, port)


def _parse_jpeg_dimensions(data: bytes) -> Optional[Tuple[int, int]]:
    """Parse JPEG SOF marker to extract (width, height) without external libraries."""
    offset = 2
    data_len = len(data)
    sof_markers = {
        0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
        0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
    }
    while offset < data_len:
        if data[offset] != 0xFF:
            offset += 1
            continue
        while offset < data_len and data[offset] == 0xFF:
            offset += 1
        if offset >= data_len:
            break
        marker = data[offset]
        offset += 1

        if marker in (0xD8, 0xD9, 0x01) or (0xD0 <= marker <= 0xD7):
            continue

        if offset + 2 > data_len:
            break
        seg_len = struct.unpack(">H", data[offset : offset + 2])[0]
        if seg_len < 2:
            break

        if marker in sof_markers:
            if offset + 7 <= data_len:
                precision, height, width = struct.unpack(">BHH", data[offset + 2 : offset + 7])
                return width, height
            break

        offset += seg_len
    return None


def _parse_webp_dimensions(data: bytes) -> Optional[Tuple[int, int]]:
    """Parse WebP (VP8, VP8L, VP8X) dimensions using struct.unpack."""
    if len(data) < 25 or not (data.startswith(b"RIFF") and data[8:12] == b"WEBP"):
        return None

    chunk_tag = data[12:16]
    if chunk_tag == b"VP8 " and len(data) >= 30:
        if data[23:26] == b"\x9d\x01\x2a":
            w = struct.unpack("<H", data[26:28])[0] & 0x3FFF
            h = struct.unpack("<H", data[28:30])[0] & 0x3FFF
            return w, h
    elif chunk_tag == b"VP8L" and len(data) >= 25:
        if data[20] == 0x2F:
            val = struct.unpack("<I", data[21:25])[0]
            w = (val & 0x3FFF) + 1
            h = ((val >> 14) & 0x3FFF) + 1
            return w, h
    elif chunk_tag == b"VP8X" and len(data) >= 30:
        w = struct.unpack("<I", data[24:27] + b"\x00")[0] + 1
        h = struct.unpack("<I", data[27:30] + b"\x00")[0] + 1
        return w, h

    return None


def parse_image_dimensions(header: bytes, ext: str) -> Optional[Tuple[int, int]]:
    """
    Extract (width, height) directly from image binary headers using struct.unpack.
    Supports PNG (IHDR), JPEG (SOF), GIF (screen descriptor), and WebP (VP8/L/X).
    """
    try:
        if ext == "png" and len(header) >= 24:
            if header[:8] == b"\x89PNG\r\n\x1a\n" and header[12:16] == b"IHDR":
                width, height = struct.unpack(">II", header[16:24])
                return width, height

        elif ext == "gif" and len(header) >= 10:
            if header[:6] in (b"GIF87a", b"GIF89a"):
                width, height = struct.unpack("<HH", header[6:10])
                return width, height

        elif ext == "jpg" and len(header) >= 2:
            return _parse_jpeg_dimensions(header)

        elif ext == "webp":
            return _parse_webp_dimensions(header)
    except Exception:
        return None

    return None


def detect_image_magic_bytes(header: bytes) -> Optional[str]:
    """
    Inspect the first bytes of data to guarantee true bitmap image format.
    Strictly permits JPEG, PNG, WebP, GIF.
    Strictly rejects executables, scripts, HTML, and SVG (XML XSS/XXE vector).
    """
    for bad_sig in DENIED_SIGNATURES:
        if header.startswith(bad_sig):
            return None

    # "<?xml" is deliberately not listed: SVG/XML cannot pass the bitmap signature allowlist below,
    # and "<?xml" appears in legitimate XMP metadata near the start of real PNG/JPEG files.
    lower_header = header[:256].lower()
    if (
        b"<script" in lower_header
        or b"<?php" in lower_header
        or b"eval(" in lower_header
        or b"<svg" in lower_header
        or b"<!doctype html" in lower_header
        or b"<html" in lower_header
    ):
        return None

    if header.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP":
        return "webp"
    if header.startswith((b"GIF87a", b"GIF89a")):
        return "gif"

    return None


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Intercept HTTP 30x redirects and re-validate destination URL against SSRF."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        resolved_url = urllib.parse.urljoin(req.full_url, newurl)
        validate_url_and_check_ssrf(resolved_url)
        return super().redirect_request(req, fp, code, msg, headers, resolved_url)


class SafeHTTPConnection(http.client.HTTPConnection):
    """HTTPConnection that binds directly to the pre-validated IP to eliminate DNS Rebinding/TOCTOU."""

    def connect(self):
        port = self.port or 80
        validated_ip = resolve_and_validate_host(self.host, port)
        self.sock = socket.create_connection((validated_ip, port), self.timeout, self.source_address)


class SafeHTTPSConnection(http.client.HTTPSConnection):
    """HTTPSConnection that binds directly to the pre-validated IP with SNI TLS verification."""

    def connect(self):
        port = self.port or 443
        validated_ip = resolve_and_validate_host(self.host, port)
        self.sock = socket.create_connection((validated_ip, port), self.timeout, self.source_address)
        if self._context is None:
            import ssl
            self._context = ssl._create_default_https_context()
        server_hostname = getattr(self, "server_hostname", None) or getattr(self, "_server_hostname", None) or self.host
        self.sock = self._context.wrap_socket(self.sock, server_hostname=server_hostname)


class SafeHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(SafeHTTPConnection, req)


class SafeHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(SafeHTTPSConnection, req, context=self._context)


def build_secure_opener() -> urllib.request.OpenerDirector:
    """Create a urllib Opener with redirect validation and IP-pinned connections."""
    opener = urllib.request.OpenerDirector()
    opener.add_handler(urllib.request.HTTPDefaultErrorHandler())
    opener.add_handler(urllib.request.HTTPErrorProcessor())
    opener.add_handler(SafeRedirectHandler())
    opener.add_handler(SafeHTTPHandler())
    opener.add_handler(SafeHTTPSHandler())
    return opener


def fetch_image_securely(url: str, dest_dir: str) -> dict:
    """Download image with multi-layer verification and save securely."""
    # 1. SSRF & URL validation (Vietnamese characters and spaces are percent-encoded first)
    url = to_ascii_url(url)
    validate_url_and_check_ssrf(url)

    # 2. Build secure request
    parsed = urllib.parse.urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}/"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36 "
                "AntigravityEvidenceFetcher/1.0"
            ),
            "Accept": "image/jpeg,image/png,image/webp,image/gif;q=0.9,*/*;q=0.5",
            "Referer": origin,
        },
    )

    os.makedirs(dest_dir, exist_ok=True)
    temp_file = os.path.join(dest_dir, f".tmp_{hashlib.md5(url.encode()).hexdigest()}")

    opener = build_secure_opener()

    try:
        with opener.open(req, timeout=REQUEST_TIMEOUT) as response:
            # 3. Check Content-Type & Content-Length headers
            content_type = response.headers.get("Content-Type", "").lower().split(";")[0].strip()
            if content_type and not any(content_type.startswith(p) for p in ALLOWED_MIME_PREFIXES):
                if content_type not in ("application/octet-stream", "binary/octet-stream"):
                    raise ValueError(f"INVALID_CONTENT_TYPE: Server returned non-image content type '{content_type}'.")

            content_length = response.headers.get("Content-Length")
            if content_length:
                try:
                    if int(content_length) > MAX_IMAGE_SIZE:
                        raise ValueError(f"OVERSIZED_PAYLOAD: Image exceeds limit ({content_length} bytes > {MAX_IMAGE_SIZE} bytes).")
                except ValueError as e:
                    if "OVERSIZED_PAYLOAD" in str(e):
                        raise

            # 4. Stream and verify Magic Bytes and Pixel Dimensions on initial chunks
            total_bytes = 0
            detected_ext = None
            buffer_bytes = bytearray()
            dimensions = None

            with open(temp_file, "wb") as f_out:
                first_chunk = response.read(CHUNK_SIZE)
                if not first_chunk:
                    raise ValueError("EMPTY_RESPONSE: Server returned zero bytes.")

                detected_ext = detect_image_magic_bytes(first_chunk)
                if not detected_ext:
                    raise ValueError("INVALID_MAGIC_BYTES: Payload is not a recognized bitmap image or is an executable/script/SVG file.")

                buffer_bytes.extend(first_chunk)
                dimensions = parse_image_dimensions(bytes(buffer_bytes), detected_ext)

                # For JPEG with large EXIF headers, buffer up to 256KB to locate SOF
                while dimensions is None and len(buffer_bytes) < 256 * 1024:
                    more_chunk = response.read(CHUNK_SIZE)
                    if not more_chunk:
                        break
                    buffer_bytes.extend(more_chunk)
                    dimensions = parse_image_dimensions(bytes(buffer_bytes), detected_ext)

                if dimensions is None:
                    raise ValueError("INVALID_IMAGE_DIMENSIONS: Could not extract valid image dimensions from header.")

                width, height = dimensions
                if width <= 0 or height <= 0:
                    raise ValueError(f"INVALID_IMAGE_DIMENSIONS: Non-positive dimensions {width}x{height}.")
                if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT or (width * height) > MAX_IMAGE_PIXELS:
                    raise ValueError(
                        f"DECOMPRESSION_BOMB: Image dimensions {width}x{height} exceed limit ({MAX_IMAGE_WIDTH}x{MAX_IMAGE_HEIGHT})."
                    )

                f_out.write(buffer_bytes)
                total_bytes += len(buffer_bytes)

                # 5. Read remaining chunks with size guard
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > MAX_IMAGE_SIZE:
                        raise ValueError(f"OVERSIZED_PAYLOAD: Stream exceeded {MAX_IMAGE_SIZE} bytes limit.")
                    f_out.write(chunk)

            # 6. Sanitize filename using deterministic SHA-256
            url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
            final_filename = f"media_{url_hash}.{detected_ext}"
            final_path = os.path.join(dest_dir, final_filename)

            if os.path.exists(final_path):
                os.remove(final_path)
            os.rename(temp_file, final_path)

            return {
                "status": "success",
                "local_path": os.path.abspath(final_path).replace("\\", "/"),
                "filename": final_filename,
                "extension": detected_ext,
                "dimensions": f"{width}x{height}",
                "width": width,
                "height": height,
                "size_bytes": total_bytes,
                "content_type": content_type or f"image/{detected_ext}",
                "original_url": url,
            }

    except Exception as exc:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass
        raise exc


def main():
    parser = argparse.ArgumentParser(description="Fetch and verify image securely for /search mode.")
    parser.add_argument("--url", required=True, help="URL of the image to fetch")
    parser.add_argument("--dest", required=True, help="Destination directory to save verified image")
    args = parser.parse_args()

    try:
        result = fetch_image_securely(args.url, args.dest)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        err_msg = str(exc)
        reason = "UNKNOWN_ERROR"
        if ":" in err_msg:
            parts = err_msg.split(":", 1)
            reason = parts[0].strip()
            err_msg = parts[1].strip()

        err_result = {
            "status": "error",
            "reason": reason,
            "message": err_msg,
            "original_url": args.url,
        }
        print(json.dumps(err_result, indent=2))
        return 1


if __name__ == "__main__":
    sys.exit(main())
