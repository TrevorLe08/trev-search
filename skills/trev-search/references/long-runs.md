# Long runs: milestones and ledger

Read with [search-deep.md](search-deep.md) or [search-check-deep.md](search-check-deep.md). All rules of the core [SKILL.md](../SKILL.md) still apply.

Applies to search-deep and search-check-deep. Both are long runs (dozens of tool calls), so each works through numbered milestones M0 to M5 in order. Each milestone ends with a **Done when** gate: do not start the next milestone until the gate passes, or until its gap is written in the ledger. Do not start writing the report early, never skip M4, and do not ask the user anything after M0 unless the input turns out to be ambiguous or the mode's own rules say so (search-check-deep asks once about very long texts).

- **Folders.** `<conv_dir>` is the host's per-conversation folder for working files: the session scratchpad when the host gives one, otherwise the working folder. The ledger, the report and the downloaded images (`media/`) all live there.
- **Ledger.** Start it at M1 and update it at the end of every milestone. If the host can write files, keep it at `<conv_dir>/<mode>-ledger.md` (e.g. `search-deep-ledger.md`); otherwise keep it as a compact working note. It is the only record of what was searched, read and decided: the final report, `Sources` and `Search log` are built from it, never from memory.
- **Report.** M5 writes the full report to `<conv_dir>/<mode>-report.md` and posts only a short summary and the file's location in the chat; with no file access the full report goes in the chat. Details are in each mode's M5. If the conversation is summarized or interrupted, re-read the ledger and continue from the first milestone not marked done. Show it to the user only if asked.
- **Budget.** Each mode gives a rough tool-call budget. When a milestone runs past its share, stop it, write the gap in the ledger and move on; never stretch silently.
- **Progress.** If the host shows messages while you work, post one line after each milestone, in the user's language, e.g. `M3/5 done: read 9/12 sources, facet "criticism" still missing`.
