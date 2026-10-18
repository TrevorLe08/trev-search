# Images

Read before getting any image. When each mode uses images is in the core's [Images](../SKILL.md#images) table; all core rules still apply.

Every mode follows the same five steps: decide whether an image is allowed (below) → open the owner's or original page → pick the image URL → download it with the helper → look, compare and show.

Use images only when all hold: the subject has a visual form and an image helps the answer or the check; the host can run Python 3.10+ and write files; the request does not forbid browsing, downloads or file writes; the subject is not a private individual (for a public figure, only when asked or clearly identifying, from an official/press source). At most 3 images per answer; search-deep follows the number the user chose in its setup (default 2-3, at most 8) and its `Images` ledger table.

**Where the reference image comes from**

- From a page you opened that owns or originally published it (the maker, the institution, the official site, the publisher of the original photo), never from an image-search thumbnail or a CDN link with no page behind it.
- `check_links.py` returns the page's `image` (its `og:image`). It is often a logo or banner (Wikipedia and PDSA both return logos): use it only if it shows the subject; otherwise take an image URL from the page content with a page-reading or browser tool.
- Match the version: model year, product generation, before/after renovation, the date of the map or chart. A reference of another version is labelled as such and cannot settle the claim.

```powershell
python "<trev-search-root>/scripts/fetch_media.py" --url "<image url>" --dest "<conv_dir>/media"
```

`<trev-search-root>` is the folder of SKILL.md (one level above this file). The helper blocks private IPs, non-image files, SVG and files over 10 MB; it does not check licenses, so always show the source.

**Comparing**

- If you can view images, look at the downloaded file before using it; if you cannot, rely only on the page's caption/alt text and say so.
- An image supports only what is visible in it. List the concrete matches and differences (shape, color, text, layout, landmarks), then give the verdict.
- A user's photo cannot prove when or where it was taken, or that it is unedited or not AI-generated. Without its earliest publication (from a reverse image search tool, if the host has one, or the original publisher), mark origin claims "Image origin unverified".
- Never identify or confirm a person from their face.

**Showing**

Each image as `![Description](file:///<local_path>)` with a caption: what it shows, the version/date, and the source-page link. In search-check-fast and search-check-deep, put each reference next to the claim it checks under `Reference images`, with one line `Match: ... / Differs: ...`. If the helper fails or cannot run, give the source-page link and describe what the page's image shows. Never fabricate image URLs.

**Check before showing:** taken from an opened owner/original page, right version, actually showing the subject (not a logo), compared on visible features only, no face identification.

## Report files

search-deep and search-check-deep write their report to a `.md` file in `<conv_dir>` (see their M5) and keep the downloaded images in `<conv_dir>/media/`, the folder given to `fetch_media.py --dest`, so the report and `media/` sit side by side.

- Inside the report file, write each image with a relative path: `![Description](media/<filename>)`, where `<filename>` is the helper's `filename` field. Never `file:///` inside a report file; a relative path keeps working when the folder is moved or the file is opened in a Markdown preview.
- Put the caption under each image: what it shows, the version/date, and the source-page link.
- After writing the file, confirm that every `media/` path in it exists.
- Delivering: give the report's full path in the chat message. Do not claim the chat shows the images; the user opens the file. In search-check-deep, each reference image stays next to the claim it checks.
