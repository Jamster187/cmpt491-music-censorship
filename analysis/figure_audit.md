# Repository-wide analytical figure audit

Inventoried **615 original analytical PNGs** in 13 families before changes. A repository image search found none in reports, figures or archive; no decorative images were modified.
The current catalog contains **951 figures**, including useful full-scale companions. **400 default figures** were flagged for scale/distribution readability; **0 unresolved flags** remain.

## Inventory and audit rules

`figure_inventory_before.csv` preserves the original inventory, renderer, intended series, axis rule and measured ranges. `figure_audit.csv` records every current image, the primary range, axis range, utilization, old limits, issue, action and reference availability. For multi-panel figures, headline metrics describe the least-utilized primary panel; `panels_json` retains every primary panel. Histogram metrics refer to the linear density panel, boxplot metrics to the X-axis, correlation metrics to the colour axis, and scatter metrics to the Y-axis. Nonlinear-axis utilization is left blank; a vertical utilization ratio alone is not a distribution-quality measure.

- Nonconstant rolling trajectories occupying <25% of the old axis are high-priority flags. 25–50% receives contextual review. Neither threshold is an effect-size criterion. Constant/ranges ≤0.000001, full-scale references, percentage axes and signed correlation colour axes are reviewed separately, not blindly zoomed.
- Histograms with a >100:1 ratio among positive bin densities get a log-density companion panel using the same bins and complete support. Zero-density bins remain visible on the linear panel. Legitimate tails are not dropped.
- Shared score boxplots compress near-zero emotion boxes. Defaults show separate central 1.5-IQR whisker views with per-panel outside counts; a complete 0–1 companion retains all outliers. Genre comparisons and scatterplots retain their complete distributions.

## Deterministic presentation rules

- Older moving-average defaults use only finite **displayed** rolling series: equal weight plus rank sensitivity when present. Pad observed extrema by 8% of their range; use only a 0.000001 score-unit guard for constant/numerically tiny ranges. Clamp to [0,1] and round bounds outward at the power-of-ten step `10**floor(log10(padded_span)-1)`. Zero is not forced. Numeric tick precision follows the actual tick interval, without offsets or scientific notation.
- Raw monthly lines stay faint. Out-of-view raw points are explicitly counted on the chart; whenever any are clipped, a `_full_scale.png` companion displays every qualifying monthly value on 0–1. Primary rolling values are never clipped. Sample-size panels, thresholds, date gaps, genre eligibility and rank weighting are unchanged.
- Newer all-genres overlays and their full-scale references retain their previously validated scale rule and image bytes. Annual plots scale all displayed means AND medians, never discard a subordinate but analytical series.
- Readable 10–13 point text, exterior legends for trajectories, light grids, stable major-genre colours and 300 dpi. Historical time plots identify 2020 as a neutral reference. Independent classifier axes disclose the theoretical 0–1 domain; line separation alone does not establish effect magnitude.

## Families

| Family | Current figures | Flagged defaults |
|---|---:|---:|
| annual_summary | 2 | 0 |
| correlation | 1 | 0 |
| genre_boxplot | 5 | 1 |
| histogram | 12 | 10 |
| missingness | 1 | 0 |
| moving_average_all_genres | 84 | 3 |
| moving_average_individual_genre | 586 | 272 |
| moving_average_major_coverage | 84 | 3 |
| moving_average_major_genres | 42 | 29 |
| moving_average_overall | 84 | 41 |
| moving_average_rank_sensitivity | 42 | 40 |
| scatter_hexbin | 6 | 0 |
| score_boxplot | 2 | 1 |

## Regression example: Country / Detoxify identity attack

- Old Y-axis: 0–0.41131788. New Y-axis: 0–0.019.
- Displayed equal/rank-weighted rolling range: 0.00074255128–0.017125968. Utilization: 4.0% → 86.2%.
- 11 qualifying raw monthly points outside the default range; their faint line is visually clipped and the full-scale companion preserves the complete range. The scored-song panel remains unzoomed.

## Validation and visual review

The renderer checks every primary rolling/annual value against its limits, every visible axis label against the canvas, source and numerical-artifact hashes, original figure coverage and complete current image catalog. The manifest stores all current PNG hashes and all protected numerical-file hashes. Run the presentation rebuild twice and compare the manifest, audit and image hashes; numerical exports are never rewritten.

Manual review samples are recorded in [figure_visual_review.md](figure_visual_review.md). Tests and deterministic rebuild results are reported in the completion sitrep.

Rebuild presentation only: `python3 src/figure_audit.py`. Validate published images/data: `python3 src/figure_audit.py --validate`.
