# Join validation

The machine-readable [audit](join_validation.json) records 818 overall music months, 81,797 source song-month rows and 355,487 source chart locations. All source locations and the 3 repeated song-month rows are retained. Score-specific denominators follow the existing descriptive series; genre cells are observed cells rather than a manufactured full grid.

Each monthly/quarterly/annual external panel has one row per natural period. Music summaries join many-to-one onto that panel. Quarterly GDP and annual population/conflict data are absent from monthly columns. Quarter/year music means aggregate original monthly source rows and flag incomplete calendar periods. They are not equal-song or exposure-weighted substitutes.

The as-of view includes 9 historical-release series and 1,468 values across 556 music months. It excludes 128 other series. Only a release strictly earlier than the chart cutoff day is usable. Same-day ordering is unknown; no intraday availability is asserted. Original industrial-production initial/revised estimates and NBER announcement-event types remain distinct from latest estimates and actual recession state.

Release-context statuses: `{"candidate_after_chart_debut_review_required": 1602, "missing_release_date": 5947, "retrospective_candidate_month_only_original_unverified": 5738, "year_precision_no_month_join": 14754}`. Year-only dates never receive an invented month. A candidate after debut is flagged and excluded. Even accepted candidate months remain original-edition-unverified and unsuitable for an as-of release forecast.

Run `python3 src/music_enrichment_validate.py --private` for source hashes, temporal checks and independent return replay. The public-only command omits `--private` and verifies both published manifests and exact original music fields. The tests exercise duplicate preservation, missing-month lags, future publication rejection, edition matching and invalid values.
