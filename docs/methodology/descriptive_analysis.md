# Descriptive analysis and moving-average methods


With the existing dependencies in `requirements.txt` installed, run from the repository:

```bash
python3 src/descriptive_analysis.py
python3 -m unittest discover -s tests -v
```

The analysis reads only `data/public/master_monthly.csv` and validates its 81,797
rows, 78 columns, 818 chart months, 28,041 identities, 16 genres, required measurements
and rank/score ranges. It never opens private databases or lyrics. Outputs are built
in a temporary directory and published only after successful generation and a source
SHA-256 check. Individual output files are replaced atomically. The manifest records
input/code hashes, runtime versions and artifact hashes; reruns in the same runtime
produce identical artifacts. Weekly analysis is not implemented here.

See the generated [factual cheat sheet](../../analysis/milestone2/descriptive_findings.md)
for values, limitations, milestone mapping and eight suggested figures. The output
folder contains 12 CSV tables and 27 PNG figures:

- `summary_statistics.csv`: all 52 prioritized numerical measurements, observation weighted.
- `song_level_summary_statistics.csv`: 48 stable numerical fields, each unique song once.
- `categorical_summary.csv`: category counts and percentages for both weightings, including missing categories.
- `genre_summary.csv` and `artist_summary.csv`: descending song-month counts and distinct-song counts; the bottom of the genre table gives rare genres. Artists are exact Billboard credits, including collaborations, not resolved people/acts.
- `genre_statistics.csv` and `song_level_genre_statistics.csv`: all 16 genres, available Ns and small-group flags. Fewer than 30 total or feature-available unique songs is a descriptive caution flag, not an inferential cutoff. No taxonomy is changed.
- `pearson_correlations.csv` and `spearman_correlations.csv`: long-form unordered numerical pairs, weighting and pairwise N. Both observation and song versions are included.
- `missingness.csv`: blank-cell missingness for every source column. `availability_by_group.csv` separately describes lyrics, all-score and per-score availability and duration coverage by decade, genre and rank band, with observation and distinct-song denominators. Songs can belong to multiple decades or rank bands.
- `yearly_summary.csv`: nine scores, annual means/medians and available Ns under observation and song-within-year weighting; partial years are flagged.
- `figures/`: 12 representative histograms, a score boxplot panel, four genre boxplots, a selected correlation heatmap, six relationship hexbins, a missingness plot and two annual panels.

Blank cells are missing; zeros remain measurements. Means and quantiles omit missing
values. Quartiles use linear interpolation; standard deviations and variances use
`ddof=1` (sample formulas; undefined for fewer than two values). Potential outliers
are strictly outside Q1 − 1.5 IQR and Q3 + 1.5 IQR, remain in every calculation, and
are counted as a percentage of non-missing values. These flags do not imply bad data.

Observation weighting describes chart exposure across song-month rows; song weighting
describes the unique song population. Before deduplication, all non-chart fields must
be invariant within each song_id, including missingness. Time-varying ranks are excluded
from song summaries/correlations rather than selecting an arbitrary month. Genre
comparison figures count each song once. Annual song weighting counts a song once
within each calendar year, so songs may still recur across years. Group means use
available scores, with no imputation or removal of outliers.

Correlations use pairwise complete values with at least three paired observations;
Spearman ranks ties by average rank within the paired subset. Constant variables
produce undefined/blank coefficients. These are descriptive associations: repeated
observations are not independent songs, and no p-values, confidence intervals or
hypothesis tests are produced. The selected heatmap uses observation weights;
relationship figures use song weights except when monthly rank is involved. Rank 1
is best and 100 worst; the rank axis is inverted in relationship plots. No derived
popularity field is added to the dataset. Annual summaries are chart-calendar
summaries, not release-year cohorts or COVID comparisons.

## Monthly classifier moving averages

Rebuild all tables and figures with the existing Python dependencies:

```bash
python3 src/moving_average_analysis.py
python3 -m unittest discover -s tests -v
```

Outputs are in [analysis/moving_averages](../../analysis/moving_averages/). Start with the
[findings and ten-figure shortlist](../../analysis/moving_averages/moving_average_findings.md).
Every one of the 42 classifier scores remains a separate measurement. This is
exploratory description, with no composite score or COVID hypothesis test.

The primary series represents equal-weight Billboard song-month presence. A song
contributes in every snapshot where it appears, without weighting by rank or
collapsing its appearances across time. Three source song-months have duplicate
rows; `data/duplicate_song_months.csv` records their identities and ranks. Verified
identical scores/genres contribute once within those months (81,794 analysis
song-months from 81,797 immutable source rows). Source counts remain in exports.
This is an explicit difference from the earlier Milestone 2 source-row descriptives.
No input rows or public files are edited.

For each calendar month, overall and within each of 16 genres, the pipeline reports
`n` (distinct songs with a score), `n_songs_total`, `source_observations`, mean,
median and sample standard deviation (`ddof=1`). Missing scores are omitted from
measurement calculations, never replaced by zero. All 818 calendar months are
reindexed for every score/genre, so absent groups have zero counts and blank
statistics, rather than disappearing from the time axis.

A monthly mean qualifies for plotting with at least **30 scored songs overall** or
**5 within a genre**. These are conservative display choices, not guarantees of
statistical precision. `sample_size_flag` distinguishes `no_scores`,
`below_minimum` and `sufficient`. Raw low-count statistics remain in the CSVs.
The trailing mean requires **12 consecutive qualifying calendar months**, including
the current month, and weights their means equally. It is not a pooled average
weighted by each month's N. A missing/low-count month interrupts rolling output
until a new full qualifying window exists. No interpolation or gap bridging occurs.
`rolling_qualifying_months`, `rolling_12m_n` and `rolling_12m_min_monthly_n` preserve
coverage context. Rolling N counts song-months, not independent songs.

Rank sensitivity uses `101 - monthly_rank` among scored songs within each month,
then the same equal-month rolling calculation and coverage mask. The three duplicate
song-months use their average source-row rank weight. This sensitivity never replaces
the primary series. Both versions retain their original score scale.

The data folder contains:

- `monthly_classifier_overall.csv`: 34,356 rows (818 × 42).
- `monthly_classifier_by_genre.csv`: 549,696 rows (818 × 16 × 42).
- `trajectory_summary.csv`: first/latest/minimum/maximum eligible rolling values, dates and sample counts for all 714 series. Tied extrema use the earliest date.
- `coverage_summary.csv`: failures across all calendar months and among months with the genre present, for each classifier; absent months and present-but-unscored months are distinguished.
- `rank_weighting_sensitivity.csv`: paired rolling differences and endpoint changes.
- `duplicate_song_months.csv`: the explicit within-month duplicate audit.
- `figure_inventory.csv`: every generated chart and its series.

The two large monthly CSVs are generated locally and ignored by Git. Deterministic,
lossless `.csv.xz` copies are included for sharing; for example, they can be read
with `pd.read_csv('analysis/moving_averages/data/monthly_classifier_by_genre.csv.xz')`.
The rebuild command restores both plain and compressed versions. No spreadsheet
steps are required.

There are 420 figures: for every classifier, overall raw/smoothed means, five-major-
genre rolling comparisons, overall rank sensitivity, and seven eligible individual
genres (Pop, Rock, Hip-Hop / Rap, R&B / Soul, Country, Alternative / Indie,
Electronic / Dance). Individual genre plots require at least 12 available rolling
endpoints; ineligible genres are retained and explicitly reported in coverage tables.
All charts include scored-song counts. Limits are shared within a classifier, start
at zero and cover the eligible monthly means, allowing small-scale emotion outputs
to remain visible. Different classifiers can have different y-limits and are not
cross-model effect-size comparisons. The vertical line labelled 2020 is orientation
only. Figures contain gaps wherever coverage is insufficient.

Input SHA-256 and in-memory equality checks protect the public data, classifier
values and genres. The build validates grid sizes, unique keys, counts, score bounds
and rolling eligibility before publishing. The manifest records code/source hashes,
runtime versions and every artifact hash; files are staged in a temporary directory
and replaced individually only after a complete successful build. Rebuilding in the
same runtime is deterministic. Tests include hand-calculated rolling windows,
missing-period recovery, weighting, deduplication, sparse genres and the actual
818-month population. No private data or model inference is used.
