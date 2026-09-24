# Moving averages — historical genre comparisons

**Start with [all-genres figures](figures/all_genres/)** and the
[nine-figure shortlist](moving_average_findings.md#recommended-all-genres-figures-9).
Read [moving_average_findings.md](moving_average_findings.md) for findings, coverage
limits and the original overall-trajectory shortlist.

| Location | Contents |
|---|---|
| [figures/all_genres/](figures/all_genres/) | Preferred comparisons: 42 all-genres and 42 major-coverage overlays, plus 84 full-scale references |
| `figures/<classifier>/` | Original 420 overall, major-genre, individual-genre and rank-sensitivity figures |
| [data/](data/) | Monthly series, coverage, endpoint summaries, rank sensitivity and duplicate audit |
| [manifest.json](manifest.json) | Original-analysis provenance and hashes |
| [figures/all_genres/manifest.json](figures/all_genres/manifest.json) | Overlay hashes, palette, plotted counts and extended findings hash |

Reproduce from the repository root, in this order:

```bash
python3 src/moving_average_analysis.py
python3 src/moving_average_all_genres.py
```

The first command reads the final public monthly dataset; the second reads its saved
series. Equal-weight monthly means, 12 consecutive qualifying months and ≥5 scored
songs per genre/month remain unchanged. Cleaner overlays require ≥120 valid endpoints;
this selects figures, not a different calculation. Missing periods remain gaps.
Rank weighting is a separate sensitivity view, never the primary measurement.

The two large monthly CSVs are generated locally and ignored by Git; tracked lossless
`.csv.xz` copies contain identical bytes. The base command regenerates the original
findings; the overlay command appends its additional section. No recommended-image
copies or symlinks are created: the shortlist links directly to canonical images,
so provenance and updates remain unambiguous. See [detailed methods](../../docs/methodology/descriptive_analysis.md).

Default overlays scale each Y-axis independently to its finite plotted values, with
8% padding per side and a minimum span of 0.02. The window shifts inward at domain
boundaries; bounds round outward to multiples of 0.01 and stay within [0, 1]. Empty
charts use [0, 1]. Numeric ticks and a note disclose the theoretical 0–1 domain.
Visual line separation alone does not establish effect magnitude. Reference files
append `_full_scale` (including `<classifier>_major_coverage_full_scale.png`).
To rebuild only these figures without recalculating any series, run
`python3 src/moving_average_all_genres.py`.
