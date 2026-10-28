# Recommended acquisition plan — awaiting separate review

No acquisition is started by this plan. First reconcile the current external-series catalog with [existing_local_series.csv](existing_local_series.csv); many core rates, labor, income, consumption and French-factor inputs already exist in another session's work. Reuse only after validating their schemas, source hashes, frequency, coverage and rights. Do not overwrite those artifacts.

## Top 25 candidate inputs

Ranks are qualitative research priorities, not fitted importance. Inputs used only to construct a proposed measure remain explicit. Exact IDs, source links, access conditions and uncertainties are in [indicator_inventory.csv](indicator_inventory.csv).

| Rank | Input | Why prioritize it / main qualification |
|---:|---|---|
| 1 | French US market excess return | Long-run broad-market channel; pair with matching RF for total return; not S&P 500 |
| 2 | US unemployment rate | Long history and direct prior lyric research; revisions/publication timing |
| 3 | All-items CPI | Inflation/cost-of-living denominator; avoid level-trend regressions |
| 4 | Michigan consumer sentiment | Perceptions distinct from realized conditions; early history is not uniformly monthly |
| 5 | 10-year Treasury yield | Long-run borrowing/discount-rate context |
| 6 | 3-month Treasury bill yield | Short-rate context and long-run slope; discount-basis caveat |
| 7 | Effective federal funds rate | Monetary conditions; distinguish target decisions |
| 8 | Moody's Baa yield | Long-run credit stress input; provider rights |
| 9 | Moody's Aaa yield | Baa–Aaa comparator; same-provider overlap |
| 10 | Industrial production | Monthly real activity, with release-vintage possibilities |
| 11 | Disposable personal income | Household purchasing capacity; deflate coherently |
| 12 | PCE price index | Deflator for income/consumption; overlaps CPI but different population/basket |
| 13 | Personal saving rate | Household buffer/behavior; revised NIPA estimate |
| 14 | Production/nonsupervisory hourly earnings | Longer wage history than all-worker earnings; composition effects |
| 15 | Initial unemployment claims | Timely labor deterioration; begins 1967 |
| 16 | Youth unemployment | Audience-related hardship hypothesis; cannot identify individual listeners |
| 17 | Chicago NFCI | Broad financial conditions from 1971; reconstructed/revised history |
| 18 | Excess bond premium | Credit risk-appetite channel from 1973; model estimate |
| 19 | Economic policy uncertainty | Media uncertainty context; historical/modern series differ |
| 20 | Real GDP | Broad cycle anchor; quarterly, revised, not invented monthly data |
| 21 | Gold price | Wealth/uncertainty alternative; fixed/floating regime differences |
| 22 | WTI spot oil price | Energy-cost channel; modern benchmark begins 1986 |
| 23 | Household debt-service ratio | Direct payment burden; old/new methods must remain separate |
| 24 | Credit-card delinquency | Modern household credit stress |
| 25 | SF Fed economic-news sentiment | Perceived conditions/media channel from 1980; not an objective shock |

The matching French risk-free return is a mandatory dependency of rank 1. The top 25 is not a list of 25 independent discoveries or a mandate to include every input in one model.

## Separate useful blocks

**Long-history candidates:** unemployment, CPI, industrial production, federal funds, Treasury bill/10-year yields, Baa/Aaa yields, quarterly real GDP, French returns and Shiller composite prices. Starts before 1958 are reported coverage leads, not a completeness guarantee. French total returns and Shiller prices must retain their different definitions.

**Financial stress:** EBP, NFCI/ANFCI as alternatives, STLFSI4, KCFSI, OFR FSI, high-yield OAS and VIX for their actual available spans; Baa–Aaa/Baa–Treasury spreads for longer context. Select a few complementary measures before testing.

**Market regimes:** trailing cumulative returns, running drawdown, trailing maximum drawdown, realized/downside volatility and distance from high. Predeclare one online drawdown convention and a small number of alternatives; 20-percent thresholds, moving averages and retrospective turning points answer different questions. Do not count distance from high twice.

**Household stress:** unemployment/youth unemployment, real wage and income growth, savings, delinquency, debt service, poverty and food insecurity. SCE/SHED financial expectations, emergency-expense inability and financial satisfaction are promising modern/low-frequency additions.

**Market psychology:** consumer sentiment and its components, news sentiment, Yale crash confidence, Baker–Wurgler sentiment, expected job loss and credit access. AAII, Conference Board and proprietary fear/greed products have additional access/rights gates.

**Genre and commercial channels:** youth/demographic unemployment, income and wealth distribution, recreation consumption, leisure time and music-industry revenue. These suggest audience-resource and consumption mechanisms; no expected association or genre-specific effect is asserted.

## First proposed sprint

1. **Reuse audit.** Inspect current local BLS, H.15, G.17, BEA and French metadata/observations against the source hashes and native frequencies. Reconcile duplicates, units and whether reported rows include missing observations. Record exact overlap rather than redownloading everything.
2. **Small public statistical core.** Confirm unemployment, CPI, industrial production, Treasury/federal-funds rates, disposable income, PCE prices, savings and wage histories. Add only missing series/periods through official BLS/BEA/Fed interfaces or authorized FRED API. Keys, if needed, are supplied through existing secure configuration and never committed.
3. **One market-return route.** Validate the existing French market/RF files and their vintage, units and calculation conventions. Obtain or document rights before redistributing raw market data. If a literal S&P 500 series is required, resolve the full-history license; do not relabel French or Shiller as S&P 500.
4. **Small perceptions/stress extension.** Verify exact Michigan aggregate access/reuse, NFCI and EBP download/vintage histories. Include one news-sentiment series if its documented measurement period and permissions fit. Defer paid AAII/Conference Board/MOVE/CRSP sources unless separately authorized.
5. **Validation deliverable before any model.** Produce a source manifest, missingness/coverage by decade, revision/publication metadata, frequency-preserving tables and a private/public rights split. Keep raw responses immutable. Document source anomalies separately. Do not change the music population, song identities or classifiers.

Expected engineering difficulty is modest for already-downloaded official series and higher for vintage reconstruction, older surveys, licensed market histories and OCR archives. No precise runtime or success rate is claimed before a bounded source benchmark. This sprint is deliberately smaller than the full candidate universe.

## Later optional sprints

Add household credit/housing and modern surveys; then distributional/regional panels; then international/commodity shocks and policy event registers. A survey's annual or triennial granularity is a feature of the source, not a defect to hide through monthly interpolation. Regional/age inputs need a justified bridge to a national chart before modeling.

After acquisition validation, seek separate review of the statistical estimand, aggregation/weights, permitted lag family, dependence treatment and multiple-testing strategy. No COVID date, model class, causal design, sampling rule or predictor search is approved by this document.
