# Temporal alignment specification for later review

An external observation needs at least `series_id`, geography, unit, reference-period start/end, value, original publication timestamp, vintage/revision timestamp, retrieval time and source hash. Missing publication dates stay missing. Date parsing must preserve quarterly, annual, fiscal-year and event semantics.

| Question | Join anchor | Defensible interpretation |
|---|---|---|
| Contemporaneous association | Chart month and economic reference month | Which lyrics were prominent during measured conditions? Revised data are acceptable only with a retrospective label. |
| Conditions before first chart entry | Exact song's first chart date | Conditions before observed chart success; neither release nor writing date. |
| Conditions preceding release | Approved recording/release date with precision | Release context; unresolved or year-only dates must remain uncertain. No substitution of chart debut. |
| Historical retrospective association | Reference periods using a documented present-day vintage | Economic history as now measured; not what audiences or artists knew then. |
| Genuine forecasting | Explicit prediction cutoff and data actually released by that instant | Requires historical vintages and timestamps, and temporally valid music predictors/outcomes. |

For an as-of join at cutoff `c`, retain only values with `publication_time <= c` and `vintage_time <= c`, then select the latest available vintage for each reference period. A present-day retrieval date is not the original publication date. Lagging a revised series by one month does not repair vintage leakage. ALFRED coverage must be inspected per series and vintage; a series beginning in 1948 does not imply 1948 archived vintages. [FRED/ALFRED API documentation](https://fred.stlouisfed.org/docs/api/fred/).

A weekly chart date is not necessarily the close of the measurement week, and stock exchanges have different holidays/time zones. A same-week Friday close may be after the relevant chart information cutoff. Exact market and chart timing must be frozen before forecasting. For retrospective monthly comparisons, distinguish monthly average prices, last trading-day prices, flows summed within a month, end-of-month stocks and rates averaged across the month. Their differences are substantive.

Quarterly GDP joins should use quarterly music aggregates, or an explicitly documented mixed-frequency design. Carrying a quarterly value across three months may be a display convenience; it does not produce three independent GDP observations. Annual poverty or food-insecurity estimates are not monthly household stress observations. Fiscal years differ from calendar years; the 1976 federal transition quarter is separate. Survey reference periods can precede interview/publication dates by months.

Lag and rolling-window families in [derived_indicators.csv](derived_indicators.csv) are proposals. They should use only completed reference periods before the chosen anchor, retain minimum-history flags and avoid centered windows. Warm-up histories should precede 1958 where available. Unavailable Nasdaq, VIX, credit or household histories must not be filled with a conceptually different proxy under the same name.

Repeated appearances of the same song create dependence, and a national monthly economic value repeated for thousands of song rows does not create thousands of independent economic shocks. Choose between chart-exposure aggregation and debut cohorts; document ranks/weights and partial months. Preserve the exact title/full-credit identities and all source observations. The original reported Billboard snapshot source is [mhollingshead/billboard-hot-100](https://github.com/mhollingshead/billboard-hot-100); this is source attribution, not new independent verification.

Any later statistical plan must address autocorrelation, seasonality, unit roots/shared trends, revised versus initial releases, changing genre composition, lyric/classifier coverage by era, chart methodology changes and multiple comparisons across indicators/lags/emotions/genres. Possible tools include difference/return models, explicit trend controls, time blocks and dependence-aware uncertainty, but none is selected here. Chart success is conditional on entering the Hot 100 and cannot reveal unsuccessful releases or population listening behavior by itself. Historical release context also cannot establish when a song was written.

NBER recession dates, retrospective peak/trough labels and complete recovery durations belong to hindsight analyses. Online market regimes must record when a threshold became observable. The regime alternatives in the catalog are illustrative definitions, not an adopted bull/bear classification or COVID design.
