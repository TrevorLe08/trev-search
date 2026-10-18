# search-deep

A thorough, multi-angle search on any topic, scaled to what the user wants, run as milestones M0-M5 with a ledger. Read [long-runs.md](long-runs.md) first; all rules of the core [SKILL.md](../SKILL.md) still apply. Ledger template:

```markdown
# Source ledger: <topic>
Choices: <source count> | <style> | <scope, languages> | <images: none / N> | Milestones done: M_
## M1 Plan
| Facet | Query | Freshness class | Date anchor? | Image wanted? (what to show) |
## M2 Candidates
| Facet | Link | Publisher | Keep / drop (reason) |
## M3 Read
| # | Link | Publisher | Published | Facet | Facts taken (figures, verbatim quotes) | Class | Level | Link check (M4) |
## Images (only when the user chose images)
| # | Facet / report section | What it shows | Source page (link) | Image URL | Local file | Version / date | Status (downloaded / failed / dropped) |
## Gaps
- <facet or claim without a source, and why>
```

**Budget:** 4-8 sources ≈ 20 tool calls, 8-12 ≈ 40, 12+ ≈ 70; M2 and M3 take most of it. Each illustration adds about 3 calls (open the owner's page, download, view), so 2-3 images add 6-9 calls.

## M0 Setup

Unless the request already answers them, ask these in one short message before searching (use the host's question tool if it has one), then wait:

1. Number of sources: (a) 4-8 (b) 8-12 (c) 12+ (takes much longer)
2. Research style (one or more): (a) Easy overview (b) In-depth analysis (c) Multi-dimension comparison (d) Timeline / history of development (e) Multiple viewpoints / debate (f) Practical guide
3. Illustrations: should the report include images that show the subject? (a) Yes, 2-3 images (b) Yes, more: tell me how many (up to 8) (c) No images. Images are taken from the owners' or original pages and shown with their source; they are skipped when the topic has nothing visual to show or when the host cannot download files.
4. Optional: an aspect, region or period to focus on; source languages (default: the user's language + English); whether academic sources are needed.

End with: "Reply 'default' to use 8-12 sources, overview + in-depth analysis, 2-3 images, sources in your language + English." If the user says "default", "up to you" (in any language) or skips a question, use those defaults and say so in one line. Ask only once. The request already gives 1, 2 and 3 → no setup, defaults for 4, one line saying so. It gives only some of them → ask just the missing ones, in one message. A request that says "no images" or forbids downloads answers 3 as (c).

If the host cannot run Python 3.10+ or write files, do not offer images: say so in one line and record `images: none (host cannot download)`.

**Done when:** source count, style, image choice and scope are known (or the defaults are stated).

## M1 Plan

Break the topic into facets, chosen from the style and the domain: background and definitions; how it works / causes; current state and latest figures; key actors and viewpoints (Multiple viewpoints: one facet per main side); comparisons, limits and controversies; impact and applications; origins and timeline; practical experience. Use 4-5 facets for 4-8 sources, 5-6 for 8-12, 6-8 for 12+. For each facet write 1-3 queries in the ledger: one per entity, in each chosen language, with the owners' domains from [topic routing](topic-routing.md) where SEO pages are likely. Give each facet its freshness class from the core's [Time and dates](../SKILL.md#time-and-dates); a facet that mixes classes is split. When the user chose images, mark the facets whose subject has a visible form (a place, a building, a product or design, a species, an artwork, a map, a chart, a process, a historical object or scene) in the `Image wanted?` column, say what to show, and pick the N facets where an image helps most: the overview and the central subject first, then the facets that are hard to picture from words. Never a person's face unless the topic is that public figure and an official or press source exists; not for number, date or opinion facets.

**Done when:** every facet has at least one query and a class; with images chosen, N facets are marked (or fewer, with the reason); every entity has its own query and no query combines entities; only Live and Fast queries carry a date anchor, Periodic and Status queries ask for the latest edition or current status, Stable queries carry none; no past year appears unless the user asked about that period or it is the known year of the latest edition. For 4-8 sources, M1 and M2 may be done in one pass.

## M2 Collect

Run the planned queries and record candidates per facet. Apply the core's [source rules](../SKILL.md#sources-and-confidence) and [vetting](../SKILL.md#vetting-an-unfamiliar-source) here: search-tool summaries, homepages, tag pages, content farms and lookalike domains are dropped with the reason; SEO-dominated results are rerun with a domain filter; a side of a debate lost to a block gets a substitute search.

**Done when:** each facet has at least 2 candidates from owners or reputable sources (or a gap line), and the total is about 1.5 times the source target, since some candidates will fail.

## M3 Read

Read the candidates, best first, and fill one `Read` row per page: exact figures, dates, definitions and short verbatim quotes, the article's own date, the claim's class and the confidence level. Follow the core's reading rules in [Link check](../SKILL.md#link-check) (reachable is not read, digests, blocked pages, image-only PDFs) and freshness per figure. Cross-check decisive claims across at least 2 independent sources. Cross-check visual facts (design, appearance, a place, a map, a chart's content) with reference images, following [Images](images.md). When the user chose images, get the illustrations for the marked facets while reading that facet's pages: take the image from a page you opened that owns or originally published it (often one of the facet's own sources), download it with `fetch_media.py`, look at it, confirm it shows the subject in the right version, and fill one `Images` row. A failed or wrong image is replaced by one from another owner's page, or dropped with the reason; never padded with a thumbnail or a logo. Stop at the chosen number. Use scholarly papers when the topic is academic or the user asked; a literature review or paper synthesis is a job for `research`, so say so in one line.

A source counts only for the claims its class allows: for Live and Fast facets it must be current for that class, otherwise it supports background labelled `as of <date>`; Periodic facets use the latest edition; Status facets use a text whose status was checked; Stable facets accept authoritative sources of any age. 12+ means at least 12 read sources, normally up to ~20.

**Done when:** the read sources, from distinct domains, reach the chosen range; every facet has at least one read source; each decisive claim has 2 independent sources or is marked level 2; when the topic has Live, Fast or Periodic facets, the ledger states how many sources on those facets are current for their class; and with images chosen, the `Images` table holds the chosen number of downloaded, viewed images or states why fewer. If the budget runs out first, write `Only N sufficiently reliable sources found` and the missing facets in `Gaps`. A narrow fact that one record settles does not need padding.

## M4 Verify

Run the [link check](../SKILL.md#link-check) on every `Read` link and handle each verdict as the core says. Vet unfamiliar sites, confirm article dates on the page, record final URLs, and check every `Images` row against the check in [images.md](images.md) (owner or original page, right version, shows the subject, file downloaded and viewed). Remove rows that fail and log the reason.

**Done when:** every remaining row has a link-check result (or was opened by a page-reading tool when the script could not run), unfamiliar sites are vetted, and dates are confirmed. If removals drop the count below the target, update the count line instead of going back to pad.

## M5 Write

Write only from ledger rows that passed M4. Scale to the question and the chosen style; no placeholders or silent truncation.

**Where it goes.** Write the full report to `<conv_dir>/search-deep-report.md`, in the user's language, with images as described in [images.md](images.md#report-files). Then post a short summary in the chat (below). If the host cannot write files, put the full report in the chat instead, with the same sections; if a length limit applies, say what was left out.

**Report file**, in this order:

1. Title line: the topic, today's date from the session, the source count and the style.
2. `Note` lines for outdated or wrong user premises (if any), worded as the core's [User premises](../SKILL.md#user-premises) says.
3. `Summary` (3-5 sentences answering the core question).
4. Body by style: Overview → main sections in plain language; In-depth analysis → mechanisms, exact figures, examples (code/config only for technical topics); Comparison → multi-dimension table plus trade-offs; Timeline → dated milestone table; Multiple viewpoints → each position, who holds it, its evidence, where they disagree; Practical guide → ordered steps with requirements and pitfalls. Images, if any, come from `Images` rows that passed M4 and sit in the section named in their row, each with a caption of what it shows, version/date and the source-page link. An image never carries a claim the text does not state.
5. Separate **Facts** (supported by read sources), **Inferences** and **Hypotheses**. Missing data: "No verified data for [detail]".
6. `Disputed / unclear`, including the ledger's `Gaps`, when relevant.
7. `Sources`: table `# | Link | Publisher | Date | Information taken`, exactly the ledger rows that passed M4, plus the count line (e.g. "20 sources, 11 of them current for their facets") when current sources on changeable facets fall short of the target. Unread search results may appear in one separate line `Unopened leads`; they never count.
8. `Search log`: the M1 queries and the sources dropped in M2-M4, with short reasons.

**Check the file** before the chat message: it exists, every `media/` path in it exists in the media folder, and its `Sources` table equals the ledger rows that passed M4.

**Chat message** (about 15 lines at most, in the user's language): the `Note` lines (if any); the `Summary`; up to 5 key findings, one line each; one line on what is disputed or missing, if relevant; then where the full report is and what it holds (e.g. "Full report: <path> — 14 sources, 3 images"), delivered as [images.md](images.md#report-files) says. Do not paste the body, the source table or the search log.

**Done when:** every milestone gate passed or its gap is in the ledger; the report's `Sources` equals the ledger rows that passed M4; every image in the report is an `Images` row that passed M4, with its caption and source link, and the count matches the choice or the gap is stated; the count line is there when current sources on changeable facets fall short; the report file passed the check above (or the full report is in the chat); the chat summary is posted with the report's location; and the core's [Check before sending](../SKILL.md#check-before-sending) passes.
