# Changelog

## 2026-10-17 — Reports as .md files (both plugins)

- `search-deep` and `search-check-deep` now write their full report to `<conv_dir>/<mode>-report.md` in M5 and post only a short summary in the chat (about 15 lines: Note/Summary or count line, up to 5 key findings or top errors, where the report is). With no file access, the full report goes in the chat as before. `<conv_dir>` (ledger, report, `media/`) is defined in `references/long-runs.md`: the session scratchpad when the host gives one, else the working folder.
- M5 gains a file check (file exists, every `media/` path exists, Sources equal the ledger; check-deep also every ledger claim in the table) and the gates and core "Check before sending" require it. Reports use relative image paths (`media/<filename>`), never `file:///`.
- `images.md` has a new "Report files" section. Deliver the report by giving its full path in the chat.
- README, mode table, adapters, evals 38-41 updated. Not yet run; open questions: whether Antigravity renders relative image paths in a `.md` preview.

## 2026-10-17 — search-deep illustration images

- `search-deep` now asks in M0 whether to add illustration images: (a) 2-3, (b) more (up to 8), (c) none; default 2-3 when the user answers "default". Skipped when the request already states it, forbids downloads, or the host cannot run Python 3.10+ / write files (then no offer, one line saying so).
- M1 marks the facets whose subject has a visible form and says what to show (overview and central subject first; no faces, no number/date/opinion facets). M3 downloads each image from the owner's or original page with `fetch_media.py`, views it and records it in a new ledger table `Images` (section, what it shows, source page, image URL, local file, version/date, status). M4 checks each row against `images.md`. M5 places each as `![...](file:///...)` beside its section with caption and source link; the M3/M5 gates require the chosen count or a stated gap. Budget +3 tool calls per image.
- `images.md`: the 3-image cap now says search-deep follows the user's choice (default 2-3, max 8). SKILL.md image table, mode table, search-help tip, the search-deep adapter, command description and README updated. Evals 32-37 added, not yet run.

## 2026-10-17 — English-only instructions and freshness classes

- All instructions are now in English: SKILL.md, `references/*.md`, the five adapters and README. Output labels, verdicts and fixed phrases are English in the files (`Sources`, `Search log`, `Note`, True / Partly true / Misleading / Outdated / False / Unverifiable, `Reference images`...) and are written in the user's language at answer time. The description's trigger phrases are English with "in any language". Kept on purpose: Vietnamese official names in `topic-routing.md` (search terms), Vietnamese strings in the scripts and tests (soft-404 detection, test data), eval prompts (user input), and earlier changelog and eval-result entries (history).
- Replaced "a source dated before the current year with no newer update is not current evidence" (a calendar cutoff that dropped valid sources, e.g. a law still in force, the latest census, history, and that flipped every January) with five freshness classes per claim: Live, Fast, Periodic, Status, Stable, each saying what counts as current and what to do with an older source. New rules: a named past period uses sources about that period; safety advice (health, medicines, first aid, chemicals, electricity, road rules) is at least Status and follows current guidance; age alone never drops a source; "latest available, as of <date>"; unsure class → search as the faster class but keep older authoritative sources until replaced.
- Queries follow the class (anchors for Live/Fast, "latest edition"/"in force" for Periodic/Status, none for Stable). search-url picks pages by class; check verdict "Outdated" needs a newer replacing source. search-deep: facets get a class in M1, the M3 count line counts sources current for their class (not "from the current year"). search-check-deep: claims get a class in M1; safety, health, legal and money claims are always high priority.
- Audience: users from age 14 and any profession; one line on plain vocabulary. `topic-routing.md` adds rows for work/employment, agriculture, engineering/construction and transport/driving, and status checks for law and health guidelines. search-deep defaults to sources in the user's language + English.
- Evals: labels in "Pass if" switched to English; scenarios 25-31 (freshness classes, safety, past period, replaced law) added, not yet run.

## 2026-10-16 — New mode search-help

- `search-help` (adapter, `commands/search-help.toml`, prefix `!help`, also inferred from "dùng sao", "nên dùng lệnh nào"): alone it shows the mode table with examples and short tips; with a need it recommends one command (plus at most one follow-up) with a reason and a ready command line, never copying a long text back. It runs no search. Evals 22-24 added.

## 2026-10-16 — Core split into references

- SKILL.md cut from ~7,200 to ~4,200 words: search-deep, search-check-deep and the shared milestone rules moved to `references/search-deep.md`, `references/search-check-deep.md`, `references/long-runs.md`; image rules to `references/images.md` (the per-mode image table stays in the core); the testing section to `scripts/tests/README.md` and `evals/README.md`, with one pointer line left.
- Repeated text removed: the deep modes' M2-M4 now point to the core's source, vetting and link-check rules instead of restating them; mode-specific checklist lines moved into each mode's M5 gate and `images.md`. Every rule kept (checked sentence by sentence against the pre-split file).
- Adapters for the deep modes name the reference files to read and stop if they cannot be read; all adapters point to `images.md` before getting an image.

## 2026-10-16 — Image table and Vietnamese image URLs

- Images section opens with a per-mode table (when to get an image, its job, where it goes) and the five shared steps.
- `to_ascii_url` moved into `fetch_media.py` (used by both helpers), so image URLs with Vietnamese characters or spaces now download; new e2e test. 52 tests pass.

## 2026-10-16 — New mode search-check-deep

- `search-check-deep` (adapter, `commands/search-check-deep.toml`, prefix `!checkdeep`): thorough fact-check of a long text as milestones M0 Nhận văn bản → M1 Tách ý → M2 Tra → M3 Đối chiếu → M4 Kiểm → M5 Viết, with its own ledger. Beyond check-fast: every checkable claim with location and priority, origin sources, recomputed figures, internal contradictions, misleading context (new verdict **Gây hiểu lầm**), the text's own citations verified, top 5 errors first; asks once when a text has more than ~60 claims.
- The milestone rules shared by search-deep and search-check-deep moved to "Long runs: milestones and ledger". search-check-fast now suggests search-check-deep for texts with more than ~15 claims. Images and the link check apply to the new mode.
- Evals 19-21 added. Not yet run.

## 2026-10-16 — search-deep milestones

- search-deep now runs as milestones M0 Setup → M1 Kế hoạch → M2 Thu thập → M3 Đọc → M4 Kiểm → M5 Viết, each with a "Xong khi" gate, for long runs on any model (written with Gemini in Antigravity in mind: no early synthesis, no skipped verification).
- A ledger (sổ nguồn, `<conv_dir>/search-deep-ledger.md` when files can be written) records queries, candidates, read sources with extracted facts and link-check results, and gaps; `Nguồn` and `Đã tra` are built only from it, and a summarized or interrupted run resumes from it.
- Rough budgets per source level (≈20 / 40 / 70 tool calls), a one-line progress message per milestone, facet counts per level. Eval 9 and 10 expectations updated; eval 18 (resume from ledger) added. Not yet run.

## 2026-10-16 — Tests folder

- Moved the helper tests to `scripts/tests/` (`test_check_links.py`, `test_fetch_security.py`, `test_fetch_e2e.py`), each adding `scripts/` to the import path; run with `python -m unittest discover -s scripts/tests -v` from the skill folder (51 tests pass, also from inside `scripts/`).
- Added `scripts/tests/README.md`: coverage per file, how to add a test for a bug, live URLs that exposed past bugs.
- SKILL.md has a "Testing and finding bugs" section pointing other AIs to the tests and the evals.

## 2026-10-16 — Images for checking

- search-check-fast and search-deep now use images to cross-check: visual claims and user photos are compared with a reference image from the owner's/original page (`Ảnh đối chiếu`), matched to the right version, on visible features only; a photo's date/origin stays unverified without its earliest publication; no face identification. search-url still has no images.
- `check_links.py` returns the page's lead image (`image`, from og:image). Tried live: Wikipedia and PDSA return logos, VnExpress the article photo, so the rule says to check it shows the subject. 51 tests pass.
- Evals 15-17 added.

## 2026-10-16 — Fixes from the independent Sonnet run

- Sonnet re-ran cases 1, 4, 6, 9 and 12 ([results](evals/results-2026-10-16-sonnet.md)): all passed (12 weakly, the trap was announced). Its 10 rule gaps are now closed in SKILL.md:
  - injection warning has a fixed slot (`Cảnh báo:` before `Nguồn`); local/localhost pages the user supplies are read as data, never cited;
  - fetch-tool digests are not page text; image-only PDFs do not count;
  - homepages are leads in every mode; freshness is per figure, checked against the owner's latest publication;
  - older sources count toward a search-deep target only for what they still support, with the current-year count stated;
  - `unreachable` never drops an official page on the script alone; a block that removes one side of a debate triggers a substitute search;
  - "known site" is defined for lateral reading; a partly answered search-deep setup asks only the missing question;
  - JSON keys differ by verdict, and a Windows console encoding hint.

## 2026-10-16 — Fixes from the first eval run

- Ran the 14 eval scenarios by hand ([results](evals/results-2026-10-16.md)); 11 passed, 2 with notes, 1 partial, 1 not gradable by the author, and 1 scenario expectation was wrong.
- Rules: session date beats cached search dates; search-tool summaries are level 3; Wikipedia via its citations; blocked → fetch tool → browser, stop at bot checks; content-farm patterns (off-field businesses, random subdomains); header/tag-page dates; "reachable is not read" for claims and source targets; check the context of `--find` matches; list final URLs; balanced sources in search-url on contested topics; no date anchors on stable parts; pets row and encyclopedia row in topic routing.
- `check_links.py`: percent-encodes Vietnamese URLs; new verdict `unreachable` (DNS, timeout, 5xx) separate from `dead`; note on pages with little HTML text. 51 tests pass.

## 2026-10-16 — Link check and source vetting

- Added `scripts/check_links.py` (stdlib, reuses fetch_media's SSRF-safe opener): per-URL verdict `ok` / `dead` / `soft_404` / `homepage_redirect` / `blocked` / `refused` / `error`, final URL, title, metadata dates, `--find` phrase matches; handles gzip/deflate with an output cap. Required for search-url and search-check-fast, and for the final source list in search and search-deep.
- Tried on live sites: caught a 200-status redirect to `/404.html` (soft 404), a bot-blocked news page (`blocked`, not `dead`) and a nonexistent domain; this led to adding the 404-path check and gzip decoding.
- New rules: lateral reading for unfamiliar sites, lookalike domains, content farms / AI-written pages, tracing numbers and quotes to their origin.
- 49 tests pass (12 new in `test_check_links.py`).

## 2026-10-16 — New plugin trev-search

- Created from the search parts of an earlier research suite: `search` and `search-deep` now live here.
- Merged the standalone `trev-search` skill's rules: date check before current-state queries, anchored queries, per-entity queries, confidence levels 1-3, user-premise check (a/b/c/d), `Nguồn` and `Đã tra` sections.
- New modes: `search-url` (verified links only, no generated answer) and `search-check-fast` (fact-check supplied content, including link status).
- `search-deep` asks setup first: source count (4-8 / 8-12 / 12+), research style, optional focus; defaults 8-12, overview + deep analysis, Vietnamese + English.
- Topic-agnostic: the old search-boost fan-out was tech-centric (architecture, code); facets are now chosen per domain, and `references/topic-routing.md` maps domains to authoritative sources. Neutrality rules for politics/religion; no individualized health/legal/financial advice.
- `scripts/fetch_media.py` and its tests carried over unchanged from the earlier suite; 37/37 tests passed in the new location on 2026-10-16.
