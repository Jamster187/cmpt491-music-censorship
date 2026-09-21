# Month-end snapshot candidate

The new frozen definition selects the **latest available Billboard chart date in
each calendar month**. Membership and monthly rank come directly from that chart.
Weekly resolution uses each original weekly chart. Changing resolution therefore
changes sampling frequency, not the definition of popularity.

The current public CSVs still use the old aggregated-month population. The
[comparison report](../reports/month_end_population_comparison.md) documents the
candidate and the acquisition gap; it does not authorize publishing or acquisition.

```bash
python3 src/month_end_snapshots.py build
python3 src/month_end_snapshots.py validate
python3 -m unittest discover -s tests -v
```

Both commands work offline using retained local databases and the raw Billboard
snapshot. They validate the existing classifier outputs without loading models.
Generated candidate CSVs remain ignored under
`data/experiments/month_end_snapshots/`. The builder has no public-output option
and does not migrate or rescope any research/acquisition database.

- `monthly_snapshots.csv`: one original observation per selected chart/rank,
  including source chart and row coordinates for auditing.
- `songs.csv`: one exact Billboard title/artist identity per candidate song_id.
  Whole-chart-history summaries and existing production enrichment are reused.
  Selection dates/counts are recomputed for the new snapshot membership.
- `master_dataset.csv`: monthly observations joined to song fields and the same
  42 classifier features. Missing values are blank, not zero.
- `manifest.json`: counts, column names, checksums, protected-input fingerprints,
  known source gaps and enrichment inventory.

The raw source supports 818 snapshots and **81,797 rows**, not 81,800: three
selected charts lack rank 100. Those gaps are retained explicitly. The last
month is incomplete in the source, ending September 19, 2026. No missing chart
observations are invented and no earlier chart is substituted.

The 72-column candidate removes old within-month aggregates. Its first seven
columns are month, snapshot date, monthly rank, song_id and three reported weekly
fields (previous rank, peak position, weeks on chart). The next 23 are song-level
fields; the last 42 are the unchanged classifier columns. The exact schema is in
the comparison JSON and `src/month_end_snapshots.py`.

New identities have `not_attempted` production enrichment statuses. The separate
population-change ledger records archived MusicBrainz pilot dispositions for 19
added songs; these require an explicit provenance-preserving import/replay before
they become production metadata. No candidate caches or unreviewed provider
matches are silently promoted.
