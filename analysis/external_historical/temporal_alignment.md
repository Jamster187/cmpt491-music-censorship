# Temporal alignment and reproduction

Each external record stores series ID, observation date/period end, native frequency, geography, value, units, provider/URL, retrieval time, publication/vintage information when available, license and transformation. Source rows carry original response path/hash. Derived rows identify every parent and formula; they do not fabricate original release times.

- Monthly values join on calendar chart month. Means use documented observed music source rows and score-specific denominators. Chart dates are not writing or recording dates.
- Quarterly and annual observations retain their native frequency and join only to quarterly/annual music summaries. No interpolation or repeated invented monthly GDP/population values.
- Daily French returns are separately compounded into months. Realized and downside volatility use sums of squared daily log returns, in monthly nonannualized percent units. Source-day counts are diagnostic; monthly and daily factor histories have different constructions and are retained separately. Their measured differences are reported, not repaired.
- Running drawdown includes the initial unit of wealth and refuses to bridge missing returns. Rolling returns require contiguous calendar months. Rate spreads retain instrument and quoting-basis differences. Nominal/real income, SAAR flows, index bases and mixed seasonal adjustment are explicit.
- Oxford monthly policy means require all calendar days. Values outside the 2020–2022 collection are missing. No COVID breakpoint or statistical design is selected. UCDP counts are threshold-defined source categories; US-involved conflict fatalities are not US deaths or US-caused deaths. Low/best/high counts are uncertainty bounds, not three independent discoveries.
- As-of queries fail closed unless the provider retains historical release values with original release dates. Releases must precede chart cutoffs by at least one day. Latest revised data remain retrospective even when a recent publication date is recorded. NBER announcement events are not contemporaneously known recession membership; undated periods after the last closed cycle remain unclassified.
- Original release candidates retain precision and source uncertainty. Year-only values have no month key. Candidates after chart debut are flagged. No candidate establishes lyric-writing date or verified original edition.

Offline rebuild: run `python3 src/external_historical_sources.py normalize`, then `python3 src/external_historical_features.py`, then `python3 src/external_historical_joins.py build`. Retained original caches are required. Public-only selective query:

```bash
python3 src/external_historical_joins.py query --permitted --view chart --series US_UNEMPLOYMENT US_CPI_YOY --output /tmp/chart_context.csv.xz
python3 src/external_historical_joins.py query --permitted --view release --series US_UNEMPLOYMENT --output /tmp/release_context.csv.xz
```

As-of chart queries require `--mode asof` and an eligible series from the source dictionary, such as the retained initial industrial-production growth series. A rejection for latest-snapshot unemployment is intentional. Queries repeat context across chart rows for convenience; they do not increase the number of independent economic observations.
