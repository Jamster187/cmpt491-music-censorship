# Acquisition findings

The validated local release contains **70 native-frequency series**, **176,476 source rows** and **825 monthly rows**. The monthly view has **55 raw/native or explicitly aggregated columns** and **47 derived columns** (102 total numerical columns). Ten quarterly series remain in separate alignment views; four French daily factor series and the NBER event series are not directly averaged into monthly columns.

The public monthly panel has **69 numerical columns**. Public source values cover federal statistical releases, World Bank commodities under CC BY 4.0, and the Baker–Bloom–Davis policy-uncertainty series under CC BY 4.0. Other research downloads and their dependent transforms remain local. Column counts include alternatives, dependencies and diagnostics, not independent economic constructs.

Across the local monthly panel, **11,181 of 84,150 cells are missing (13.29%)**. Missingness includes unavailable early years, publication-tail gaps, historical source gaps and transformation warm-up. No interpolation or winsorization was applied. **14 native/aggregated monthly inputs** and **15 derived columns** meet the strict complete-month criterion for January 1958–September 2026. Daily market-calendar completeness remains unverified and is excluded from that certification.

The complete native monthly inputs are: `FF_HML`, `FF_MKT_EXCESS`, `FF_RF`, `FF_SMB`, `US_FED_FUNDS`, `US_IP_MANUFACTURING`, `US_IP_MINING`, `US_IP_TOTAL`, `US_IP_UTILITIES`, `US_NONFARM_EMPLOYMENT`, `US_POLICY_UNCERTAINTY_NEWS`, `US_PRIME_RATE`, `US_TBILL_3M_DISCOUNT`, `US_TREASURY_10Y`. Full calendar coverage does not erase EPU's historical newspaper-design change, French FIZ/CIZ/revision issues, changes in the economy or measurement definitions.

Material gaps and distinctions:

- Unemployment, youth unemployment, participation and CPI have one missing source month (October 2025). Their early start does not make them complete through 2026. Payroll employment is complete in this snapshot.
- BEA monthly income, saving and PCE prices start in 1959 and currently end August 2026. The acquired real consumption/recreation table starts in 2007; an older table must be acquired separately if needed. No source-tail values were invented.
- Corporate Aaa/Baa values in H.15 end September 2016. Their long-run credit spreads therefore stop there. EBP (1973 onward) and FCI-G (1990 onward) add modern stress context without pretending to be the same measure.
- Michigan monthly sentiment begins in 1978; its quarterly archive is separate. Claims begin in 1967, NFCI in 1971, economic-news daily effects in 1980, the current debt-service method in 2005 and selected credit-card delinquency in 1991.
- World Bank gold starts in 1960. Its WTI benchmark starts in 1982; it is not claimed identical to the EIA Cushing series commonly reported from 1986. Commodity benchmark definitions and the fixed-price gold era remain documented.
- The NBER closed-cycle membership series stops at the last dated trough (April 2020). Later months are unknown in that derived chronology; no unannounced present-day recession status is inferred. Announced turning-point event history is a separate view.

The strongest ready-to-review families are long-run monetary rates and industrial activity; near-complete labor/inflation; income/saving; historical broad-market returns; and shorter, complementary credit/perception measures. Their different coverage and revision histories require an explicit analytical design before comparison with music. The sample join validates 81,797 music rows, 28,041 exact song identities, 818 chart months and genre-specific summaries without changing the source music data.

Phase 2 should prioritize original-release/ALFRED vintages, a separately identified old-method debt-service archive, pre-2007 consumption tables, a cleared modern corporate-yield continuation and exact EIA Cushing oil data. A literal licensed S&P 500 total-return history and wider household surveys can follow if justified. More redundant predictors are lower priority than coverage, vintage integrity and source rights. **No music-versus-finance model has been run.**
