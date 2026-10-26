# Research artifact validation

Completed 2026-10-26 against canonical `main`, research baseline `2979f0d`. Publication scope is **14 new Markdown/CSV research files in this directory only**. The nine requested deliverables are present; five supporting audit files make the evidence and validation reviewable. No feature pipeline, classifier, model, audio, lyrics, private database or existing data/analysis artifact is included.

## Research inventory checks — PASS

- 188 unique candidate IDs and proposed names; 182 substantive candidates and 6 explicitly excluded Tier 4 rows.
- Tier counts reconcile across inventories and reports: 59 / 66 / 57 / 6.
- All required candidate/source cells populated with a value, explicit UNKNOWN, NOT_APPLICABLE, or a resolvable source-condition reference; CSV widths and headers valid; CSV line endings normalized to LF for repository whitespace checks.
- Every candidate resolves to a source record and HTTPS primary-source/evidence URL. All source IDs unique.
- All candidate names differ from the 80 existing public-export column names. A manual redundancy review additionally excludes duration, raw TTR variants, synonymous emotions, vector-coordinate padding and outcome relabeling.
- Feasibility matrix contains exactly the candidate ID set. Reconstructable inventory contains exactly the 59 Tier 1 candidates.
- Commercial and historical ranks each form a unique 1–20 sequence; all commercial forecast-ranked rows have primary availability A–C. D/F measures are not silently forecast-ranked.
- Academic references resolve to 20 study entries. Incomplete methods/rights are explicitly flagged rather than assumed verified.
- Source totals reconcile: 62 records = 58 external + 4 local. External status = 41 documentation-verified + 1 live-sample-verified + 11 partial + 4 access/unverified + 1 withdrawn.
- Fourteen API probe rows reconcile to five HTTP 200 and nine HTTP 404 responses. Their source reference is S02, the final AcousticBrainz inventory ID. This is diagnostic evidence, not a population estimate.
- All identities/titles/credits in both small audit files match the existing public `songs.csv`. Audit exports contain field names/statuses, not private lyric/audio text or new feature values.

The checks used temporary research-audit scripts outside the repository. They validate documentation/inventory consistency and preservation; they do not compute any proposed feature or estimate scientific usefulness. External links were inspected during research, with failures recorded in source statuses; no claim is made that every URL will remain available.

## Protected-file preservation — PASS

SHA-256 comparison against the pre-research baseline verified **1,511 existing files** unchanged. This includes the raw snapshot, ten existing public files, 1,436 prior analysis files, prior reports, and all four private databases checked: the Phase 1 foundation, working research database, catchup metadata database and catchup lyrics database. Private databases were inspected read-only. The temporary hash manifest and sample-preparation file were removed from the publication directory; neither is committed.

No existing dataset was regenerated, no acquisition progress was rebuilt or discarded, no previous analysis result was edited, and no new feature values were published. The source snapshot remains the reported upstream Billboard history, not independently reverified Billboard content.

## Repository checks — PASS

`python3 src/repository_layout.py` completed successfully:

- frozen release hashes: PASS;
- immutable artifacts checked: 1,069;
- local Markdown links checked: 574;
- private tracked files: 0;
- stale active paths: 0.

`python3 -m unittest discover -s tests -v` completed: **495 tests run in 74.640 seconds; OK; 13 skipped**. The skipped tests require existing optional Streamlit/demo environments and completed demo artifacts. No test failures remain. An earlier check during document drafting found links to files that had not yet been created; after the files were completed, layout validation and the entire suite were rerun successfully.

`git diff --check` passed. A final fetch before publication showed `HEAD...origin/main` at `0 0` on `main`. Only this new research directory was changed. Staging is restricted to its Markdown and CSV files. No dependency installation, paid API, bulk dataset download, external message, classifier production, regression campaign or new COVID/statistical analysis was performed.

The resulting commit is identified in repository history and the final delivery message. Work stops after the research commit is pushed; implementation remains unapproved.
