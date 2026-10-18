# trev-search

Web search on any topic, with opened sources and date-aware freshness checks, for users from age 14 up and in any line of work. The skill's instructions are in English; it answers in the user's language.

| Command | Use when | Result |
| --- | --- | --- |
| `/search <question>` | You need a short answer with sources | Concise answer, a source beside each claim, images (≤3) when the subject has a visual form |
| `/search-url <topic>` | You want to read and synthesize yourself | Table of opened, checked links; no answer written |
| `/search-check-fast <content>` | You want to check a passage, a post or an AI answer | Verdict per claim (True / Partly true / Outdated / False / Unverifiable), link checks, reference images when a claim is about appearance or you send a photo |
| `/search-check-deep <long text>` | You want a whole article, report, essay or long AI answer checked thoroughly | Every checkable claim with its location; adds the verdict **Misleading**; internal contradictions and the text's own citations checked; top 5 errors first. The full report is saved as `search-check-deep-report.md`; the chat gets a short summary |
| `/search-help [need]` | You don't know which command to use | Alone: the command table with examples and tips. With a question, topic or text: one recommended command with a reason and a ready command line; no search |
| `/search-deep <topic>` | You want a deep, multi-angle picture | Asks the number of sources (4-8, 8-12, 12+), the research style and whether you want illustration images (2-3, more up to 8, or none) first, then writes a report to match, with the images taken from owners' pages and shown next to the sections they illustrate; also cross-checks appearance facts with images. The full report is saved as `search-deep-report.md` (images in `media/` beside it); the chat gets a short summary |

No command: paste content and ask whether it is right → check-fast; ask only for links → url; anything else → search. Prefixes `!url`, `!check`, `!checkdeep`, `!deep`, `!help` also work. Asking "how do I use this" or "which command should I use" switches to search-help. search-check-deep and search-deep run only when named, because they take many steps; check-fast suggests search-check-deep for texts with more than ~15 claims.

Examples:

- `/search current gold price`
- `/search-url causes of the Great Depression of 1929`
- `/search-check-fast "Vietnam has 63 provinces and its GDP grew 8% in 2025" (source: https://...)`
- `/search-check-deep` + paste a long article → the AI splits it into claims, finds each origin, checks every claim, and reports the top errors first
- `/search-deep circular economy in Vietnam` → the AI asks the number of sources, the style and whether to add illustration images → answer `8-12, comparison, 3 images` or `default`.

## How freshness works

Whether an old source is still usable depends on the claim, not on the topic or the calendar year. Each claim gets one of five classes:

| Class | Examples | Current means |
| --- | --- | --- |
| Live | Gold, fuel, stock and farm-produce prices, exchange rates, weather, live scores, breaking news | The owner's latest update, dated |
| Fast | Software versions, retail prices, office holders, rankings, schedules, deadlines, admissions, visa rules | Published after the latest change |
| Periodic | GDP, inflation, census, cut-off scores, fees, tax brackets, minimum wage | The latest edition, whatever its year |
| Status | Laws, decrees, standards, codes, drug approvals, medical and safety guidelines | Still in force (status checked), whatever its year |
| Stable | History, mathematics, settled science, language, definitions, arts, religions, established techniques | Any authoritative source; old primary documents are often best |

Questions about a past period use sources about that period. Safety advice (health, medicines, first aid, chemicals, electricity, road rules) always follows the authority's current guidance. No source is dropped for its age alone.

## Long runs

search-deep runs in 6 milestones, each with a "done when" gate, recorded in a source ledger (`search-deep-ledger.md` in the conversation folder when files can be written):

| Milestone | Work | Done when |
| --- | --- | --- |
| M0 Setup | Ask the number of sources, style, illustration images and scope | Choices known or defaults used |
| M1 Plan | Split into facets, assign freshness classes, write queries, mark facets that get an image | Every facet and every entity has its own query |
| M2 Collect | Run queries, filter candidates | Every facet has at least 2 good candidates |
| M3 Read | Read pages, record figures, download the chosen illustrations, compare images | Enough sources read, every facet covered, images downloaded or gap stated |
| M4 Verify | Link check, vet site owners, confirm dates, check each image | Every remaining source and image passed |
| M5 Write | Write the report file from the ledger only, images beside their sections, then a short chat summary with the file's location | Report file checked, final check passed |

Estimate: 4-8 sources about 20 tool calls, 8-12 about 40, 12+ about 70, plus about 3 per image. If the conversation is summarized mid-run, the AI re-reads the ledger and continues from the first unfinished milestone.

search-check-deep uses the same milestone frame and ledger (`search-check-deep-ledger.md`):

| Milestone | Work | Done when |
| --- | --- | --- |
| M0 Get the text | Get the full text, author, date written | Full text in hand, date known or marked "unknown" |
| M1 Split claims | Number every claim with location, type, freshness class, priority (asks once if more than ~60) | Every sentence with a checkable fact has a number |
| M2 Search | Find each claim's origin, open the text's own citations first | Every high-priority claim has a candidate origin |
| M3 Compare | Verdicts, recomputed figures, internal contradictions, misleading context, cited sources | Every high-priority claim has a verdict from a read source |
| M4 Verify | Link check, vet site owners, confirm dates | Every source in the ledger passed |
| M5 Write | Report file: overview, top 5 errors, all-claims table, contradictions, cited sources, unchecked claims; then a short chat summary with the file's location | Report file checked, final check passed |

Estimate: about 2-4 tool calls per high-priority claim, 1 per low-priority claim; a 1,500-word article (~30 claims) takes about 60-100. The AI does not rewrite the text unless asked.

## Where the reports go

The two long modes keep their working files in one folder (`<conv_dir>`: the session scratchpad when the host gives one, otherwise the working folder): `<mode>-ledger.md`, `<mode>-report.md` and `media/` (downloaded images). The report uses relative image paths (`media/...`), so the folder can be moved or opened in a Markdown preview. The chat shows only a short summary (about 15 lines) and where the report is; if the host cannot write files, the full report goes in the chat instead.

## Structure

- `SKILL.md`: shared rules (including freshness classes), the rules of search, search-url and search-check-fast, the per-mode image table, the final check.
- `references/long-runs.md`: milestone frame, ledger, budget and progress messages for the two long modes.
- `references/search-deep.md`, `references/search-check-deep.md`: milestones M0-M5 of each long mode. Their adapters make the AI read these files first and stop if they cannot be read.
- `references/images.md`: when an image is allowed, where it comes from, how to download, compare and show it; read before getting an image.
- `references/topic-routing.md`: trusted sources per domain, including work and trades.
- `scripts/check_links.py`: checks that links are real (404, disguised 404, redirect to homepage, unreachable by DNS, timeout or server error, bot block), reads the title and metadata dates, and finds phrases in the page (`--find`). Required for search-url, search-check-fast and search-check-deep.
- `scripts/fetch_media.py`: safe image download for search, search-check-fast, search-check-deep and search-deep (`check_links.py` also returns the page's lead `image`).
- `scripts/tests/`: offline automated tests for both scripts. Run from the skill folder: `python -m unittest discover -s scripts/tests -v`. `scripts/tests/README.md` lists what each test file covers, how to add a test for a bug, and the live links that exposed past bugs.
- `evals/README.md`: scenarios per mode; `evals/results-*.md`: results of earlier runs. The last section of SKILL.md points other AIs to these files for bug hunting.

Note: the helper scripts and their tests still contain Vietnamese strings on purpose (soft-404 detection for Vietnamese pages, Vietnamese URLs and titles as test data).
