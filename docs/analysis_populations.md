# Weekly and monthly analysis populations

Build locally with Python 3.9+ and the standard library:

```bash
python3 src/populations.py
python3 -m unittest discover -s tests -v
```

The pipeline reads `data/processed/music.db` through a read-only SQLite attachment.
It never updates the canonical database or raw Billboard JSON. It computes and
validates temporary outputs before publishing reproducible files under
`data/processed/populations/`, which is already ignored by Git:

- `populations.db`: the `monthly_top100` table and build provenance. It contains
  no copied song metadata or weekly table.
- `weekly_top100.csv`: every original observation, including source row identifiers,
  with `weekly_points = 101 - rank` appended.
- `monthly_top100.csv`: month, monthly_rank, song_id, monthly_points, weeks_present,
  best_weekly_rank, average_weekly_rank, and weekly_observations.
- `month_inventory.csv`: available chart dates and eligible identities per month.
- `new_monthly_songs_by_year.csv`: first appearance in a monthly basket by year.
- `months_per_song.csv`: exact frequency distribution of selected months per song.
- `population_summary.json`: complete statistics, examples, validation, and hashes.

The readable report is [`reports/analysis_populations.md`](../reports/analysis_populations.md).
Rerunning safely rebuilds the derived artifacts. Failed validation does not publish
the staged build; if publication is interrupted, rerun to refresh all artifacts.

## Definition

Each original weekly observation contributes `101 - rank` to its chart date's
calendar month. Sum per month/song_id. Sort by points descending, best rank
ascending, mean rank ascending, and stable song_id ascending (binary order).
Select 100 identities, or all available if fewer. No weeks are split across months.

`weeks_present` counts distinct chart dates, while `weekly_observations` counts
all contributing rows. Existing duplicate song-week rows each contribute points
and enter the mean rank. They are preserved and reported, not silently repaired.
No title/artist normalization or external entity resolution is involved.

Month sizes refer to selected identities, not completeness of calendar coverage.
September 2026 is incomplete in this snapshot. The beginning of the series also
limits what can be called a new entrant; first monthly entry is neither first
weekly chart entry nor release date. Counts by historical period use calendar
months and can overlap across periods; the report separately provides disjoint
first-entry cohorts. No COVID breakpoint is chosen.

## Read and join the two views

SQLite does not support a persistent view spanning attached databases. The helper
creates a session-local `weekly_top100` view directly over the read-only Phase 1
table; the monthly table persists in the separate derived database:

```python
import sqlite3
from pathlib import Path
from src.populations import attach_weekly

path = Path('data/processed/populations/populations.db').resolve()
conn = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
attach_weekly(conn)

weekly = conn.execute('SELECT * FROM weekly_top100 LIMIT 5').fetchall()
monthly = conn.execute('''
    SELECT m.*, s.title, s.artist
    FROM monthly_top100 m JOIN source.songs s USING (song_id)
    WHERE m.month = '2019-06' ORDER BY m.monthly_rank
''').fetchall()
conn.close()
```

Both views retain the canonical song_id. A future song-score table can therefore
join on that ID to either temporal view without duplicating song-level scores.
No score table or classifier is created here. SQLite cannot enforce a foreign key
to another database, so the build explicitly checks every monthly ID against
`source.songs` and checks canonical-source hashes for provenance.

Validation independently recomputes every aggregation and basket in Python, using
exact rational average-rank comparisons to check SQLite's ordering. It checks
contiguous unique ranks, the 100-song limit, referential integrity, CSV contents,
and unchanged source hashes. Tests cover month boundaries, persistence, all tie
breakers, cutoff ties, short baskets, duplicate observations, invalid ranks,
read-only access, and corrupted aggregates.
