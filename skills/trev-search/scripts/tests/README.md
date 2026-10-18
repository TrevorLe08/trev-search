# Script tests

Automated tests for the two helpers in `scripts/`. Any AI or person changing a helper, or hunting for bugs in it, runs these first and adds a test for every bug found.

## Run

From the skill folder (the one holding `SKILL.md`), with Python 3.10+ and no extra packages:

```powershell
python -m unittest discover -s scripts/tests -v
```

All tests run offline: HTTP cases use a local server on 127.0.0.1, which the tests allow by patching `fetch_media.is_prohibited_ip`. The helpers themselves still block private addresses. Expected result on 2026-10-18: `Ran 52 tests ... OK`.

## Files

| File | Covers |
| --- | --- |
| `test_check_links.py` | `check_links.py`: title, dates (meta, JSON-LD, `<time>`), lead image, phrase search (case/whitespace, ignores script/style), soft 404 by title or by `/404` path, homepage redirect, gzip bodies, Vietnamese/space URLs (`to_ascii_url`), verdicts `ok` / `dead` / `blocked` / `unreachable` / `refused`, note on pages with little text |
| `test_fetch_security.py` | `fetch_media.py` units: blocked loopback/LAN/metadata/IPv4-mapped/obfuscated IPs, redirect SSRF, SVG removed, magic bytes, dimension bombs (PNG, JPEG, GIF; WebP size parsing), DNS-rebinding IP pinning, deterministic file names |
| `test_fetch_e2e.py` | `fetch_media.py` end to end against a local server with PNG files: saving, content-type and body checks (HTML/SVG/script rejected), size caps, redirects (allowed, metadata, non-http, loops), 404, CLI output |

## Adding a test for a bug

1. Reproduce the bug with the smallest input: an HTML string for `check_links.analyze_html`, or a route on the local server (`self.serve(path, body, status=..., **headers)`) for `check_url` / `fetch_image_securely`.
2. Add the test to the matching file, see it fail, fix the helper, see all tests pass.
3. Note the bug and the fix in `../../CHANGELOG.md`.

Do not add tests that need the internet: live sites change. Use the live checks below by hand instead.

## Live checks (by hand)

Real pages that exposed bugs or rule gaps. Run `python scripts/check_links.py <url>` and compare. Results drift as sites change; a different result is a lead to investigate, not automatically a bug.

| URL | Verdict seen on 2026-10-16 | What it tests |
| --- | --- | --- |
| https://vnexpress.net/bai-viet-khong-ton-tai-123456789.html | `soft_404` (200, redirected to `/404.html`) | Soft 404 by path; sometimes times out → `unreachable` |
| https://www.python.org/about/ | `ok`, title found | gzip body sent without being asked |
| https://www.reuters.com/world/ | `blocked` (403) | Bot block is not `dead` |
| https://khong-ton-tai-abcxyz-2026.com/a | `unreachable` (DNS) | Made-up domain |
| https://en.wikipedia.com/wiki/Korea_War | `ok`, `final_url` on wikipedia.org | Lookalike domain redirect |
| https://www.hvu.edu.vn/file/1350440875/9.Trịnh Thế Truyền.pdf | `ok`, PDF | Vietnamese characters and spaces in the URL |
| https://en.wikipedia.org/wiki/Eiffel_Tower | `ok`, `image` is a logo | og:image is not always the subject |
| https://example.com/eiffel-facts | `dead` (404) | Plain 404 |

Rule-level tests (whole answers graded by hand) are in `../../evals/`.
