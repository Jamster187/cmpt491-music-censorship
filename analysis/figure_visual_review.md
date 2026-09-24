# Manual figure review

The review checks readability and honest presentation, not effect magnitude or new
statistical conclusions. All 13 families are represented below. Default and companion
views are inspected together where clipping or a nonlinear axis is used.

| Family | Representative image | Visual findings |
|---|---|---|
| Overall rolling | `moving_averages/figures/detox_identity_attack/overall.png` | Rolling line legible; faint context, outside count, exterior legend and count panel clear. |
| Individual genre rolling | `moving_averages/figures/detox_identity_attack/country.png` | Both weighting lines visible on 0–0.019; 11 out-of-view raw points disclosed; full-scale companion retains them. Count panel and gaps remain clear. |
| Major-genre rolling | `moving_averages/figures/detox_identity_attack/major_genres.png` | All five primary series retained; genuine between-genre level differences remain. Individual views provide detail for lower-score genres; no high primary values are hidden. |
| Rank sensitivity | `moving_averages/figures/detox_identity_attack/rank_sensitivity.png` | Solid and dashed rolling lines legible; both determine limits; exterior legend clear. |
| All-genres overlay | `moving_averages/figures/all_genres/emotion_joy.png` | Existing independent scale, labels, gaps and genre legend remain readable; preserved unchanged. |
| Major-coverage overlay | `moving_averages/figures/all_genres/detox_threat_major_coverage.png` | Small-score trajectories and numeric scale readable; domain note explicit; preserved unchanged. |
| Histograms | `milestone2/figures/hist_emotion_joy.png` | Linear panel preserves the dominant near-zero bin; log-density companion exposes the tail using the same bins and all observations. Shared legend is outside the panels. |
| Score boxplots | `milestone2/figures/song_score_boxplots.png` | Emotion boxes visible on individual central views; per-panel excluded counts explicit. Full-domain companion retains outliers. Independent axes prevent cross-panel distance comparisons. |
| Genre boxplots | `milestone2/figures/genre_ll_violence.png` | Near-zero boxes are legible on the disclosed symlog X-axis; all outliers and sample labels remain. Linear full-scale companion inspected alongside it. |
| Correlation heatmap | `milestone2/figures/selected_spearman_heatmap.png` | Signed colour scale preserved; coefficients readable with contrasting text; rotated labels fit. |
| Hexbin relationships | `milestone2/figures/relationship_ll_explicit_language_vs_chart_weeks.png` | Dense low-chart-week region and isolated long-chart observations both visible; log-count colour scale explicit; no observations truncated. |
| Missingness | `milestone2/figures/missingness_by_decade.png` | Percentage domain retained intentionally; legend outside plot. Lyrics and classifier availability curves nearly coincide because their values do; no jitter introduced. |
| Annual summaries | `milestone2/figures/annual_sentiment_emotion.png` | Both means and the median remain visible, including near-zero medians; partial-year marks and neutral 2020 reference visible; shared exterior legend clear. |

Full-scale references intentionally have low utilization when scores are small. They
are contextual companions, not unresolved default-view failures. Some major-genre
comparisons still show low-score genres near the baseline because other **primary**
series are genuinely much higher; their individual genre charts provide the detail.

The manually reviewed preview PNGs were compared with the published counterparts
and matched byte-for-byte. The final suite passed 364 tests, including the Country
regression, primary-value containment, audit coverage and immutable-data checks.
