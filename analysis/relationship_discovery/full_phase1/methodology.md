# Full relationship discovery, Phase 1

This is the explicitly approved exhaustive expansion of the frozen
[pilot methodology](../methodology.md). The pilot publication remains unchanged.
The discovery classroom UI and its UI test are explicitly extended; their prior
versions remain in commit `5e77ab9`. The old artifact manifest remains historical,
and the new manifest records both historical and current UI provenance. The
statistical code and all previous numerical artifacts retain their original bytes.
This campaign covers exactly 2,775 pairwise candidates, 3,192 nonlinear candidates,
and 3,192 genre-interaction candidates: **9,159 primary hypotheses**. It does not
run numeric interactions, threshold interactions, historical breakpoints or
additional PCA/clustering. Period and genre summaries come from the same approved
four chronological evaluations; they are descriptive diagnostics.

## Frozen calculations and complete correction

All candidate generators, model implementations, support rules, preprocessing,
seeds, four outer periods and two inner periods per outer fold are reused byte for
byte from commit `5e77ab9`. `protocol.json` locks their identity, the new runner,
the complete candidate list and the correction denominator before execution.
Candidates are processed in deterministic candidate-hash order. Nothing is
screened by its observed association, significance or perceived novelty.

The primary null and resampling settings are unchanged: 999 within-debut-year
permutations for pairwise dependence; 32,767 paired two-year-block sign flips
for predictive improvement; 499 fixed-analysis block resamples for uncertainty.
The resolutions are 0.001 and 1/32,768, respectively. No attractive candidate gets
selective extra permutations. One primary hypothesis belongs to each candidate;
secondary dependence measures, inner method comparisons, genre cells and period
summaries are diagnostics, not separately certified discoveries.

Benjamini–Yekutieli correction is recomputed across **all 9,159 attempted primary
hypotheses**, including reconstruction controls and failures (unavailable p=1).
Family BY values are also reported, but global BY defines the reported 0.05
threshold. Prior pilot q-values are never imported. The campaign is exploratory;
BY permits dependence between valid p-values but does not repair invalid
exchangeability or sign-symmetry assumptions, model-selection uncertainty,
shared artist effects, or previous inspection of these outcomes.
Displayed 95% intervals are marginal fixed-analysis intervals, not simultaneous
post-selection confidence sets.

The four outer evaluation windows remain 1990–1999, 2000–2009, 2010–2017 and
2018–2025. Songs must fit wholly inside their train/evaluation chart-history
windows. Each fit needs 500 training and 200 evaluation songs. Genre interactions
require 100 training songs in five debut years; evaluation subgroups need 100
songs and five years. Unsupported subgroups remain in coverage records. The
incomplete 2026 year is not evaluated. Whole-window purging also removes
boundary-crossing and ongoing hits, which can change cohort composition and
underrepresent recent long-running songs. All preprocessing and nonlinear method
selection use training/inner periods only. Historical metadata and completed
chart outcomes make these retrospective analyses, not as-of forecasts.
Disjointness is checked under the frozen exact title/artist study-song identity.
Alternate credits, titles or shared recordings are not newly resolved or merged;
this does not establish performer- or recording-disjoint generalization.

## Results and interpretation

Complete family tables retain nulls, negative effects, failed coverage and
reconstruction controls. Every row carries its sample size, primary effect,
interval, raw p, family/global q, comparison performance, absolute outer metrics,
period stability, original A/B/C category and warnings. Detailed local checkpoints
retain every method comparison, curve, subgroup and timing measurement.

The interpretation layer adds a **broader-domain distinction** without
changing A/B/C: lyrical affect and lyrical content are different conceptual
domains in the frozen policy but both derive from the same lyrics and classifier
pipeline. They remain in complete cross-domain results; the presentation-priority
cross-domain view requires different broader domains (lyrics, genre, historical
calendar, chart performance, MusicBrainz metadata). This does not establish independent measurement: genre and catalog
features can share metadata and artist information. Genre is itself classified
metadata and is not ground truth.

No weighted novelty score is used. Predictive views put supported positive
performance first: all four periods evaluated, positive pooled outer R²,
positive mean-baseline skill, positive model-vs-comparison improvement in all four
periods, and a positive block-interval lower bound. Within that explicitly labelled
tier they sort worst-period relative MSE improvement, then the block-interval
lower bound, then candidate ID. Other candidates remain visible in lower tiers.
This is a descriptive, post-hoc presentation order, never model reselection.
Positive pooled R² does not imply positive R² in each period: the pooled target
variance also includes differences between period means. Period-specific values
must be inspected before describing a model as predictively useful.

Pairwise ordering is kept separate by effect type (Spearman, eta-squared,
Cramér's V); absolute values on incompatible scales are not compared. Within a
type, global-BY status and stable annual sign (where defined) precede magnitude.
Pairwise and predictive effects also do not share a magnitude scale. The report's
cross-domain shortlist allocates five numerical pairwise, two categorical
pairwise and three predictive examples for presentation coverage; these quotas
are not a test or a claim that the groups have a common numerical rank.
Two supplemental presentation examples use the same predictive ordering,
restricted respectively to broader-domain genre interactions and MusicBrainz
metadata predicting chart outcomes. They receive separate bounded artist checks;
the original shortlist and its sensitivity cache are retained unchanged.

Sign-reversal summaries are computed from the saved genre-interaction diagnostics.
A displayed substantial reversal requires an absolute pooled rho of at least
0.10 and an opposite partial rho of at least 0.05, or adequate genres with rho
at least +0.10 and at most −0.10. A descriptive attenuation flag means pooled
absolute rho ≥0.10 and genre-adjusted absolute rho ≤25% of the pooled magnitude.
These cutoffs are presentation rules, not inferential thresholds. A sign flag is
not proof of Simpson's paradox, causation or a replicated subgroup discovery.
Period sign-change flags require a pooled rho at least +0.10 in one approved
outer window and at most −0.10 in another, with at least 200 complete pairs in
each displayed window. These use saved diagnostics and add no historical tests.

## Artist-aware sensitivity

The leading nontrivial findings receive an additional descriptive cluster
bootstrap using the exact original artist-credit string. Each replicate samples
artist-credit clusters with replacement and retains all of their eligible songs.
For prediction, the original two-year-block weighting is retained inside each
replicate; models and training selections are held fixed. For pairwise effects,
fixed numerical ranks and categorical values retain their original estimator.
499 cluster replicates give an artist-credit interval. The result reports artist
count, largest cluster share, and the share of evaluation songs whose exact
artist credit occurred in that fold's training set.

This check addresses repeated exact credits, not all shared performers:
collaborations and spelling variants can split the same performer into different
clusters. Artist bootstrap and temporal bootstrap are separate sensitivities;
neither jointly resolves time dependence and artist dependence. They exclude
refitting/selection uncertainty, are chosen after seeing the full search, and
receive no new p-values or significance labels. Agreement is robustness evidence,
not independent confirmation. Genuinely new data and a frozen replication design
are needed for confirmation.

## Checkpoints and resource accounting

Each candidate writes an atomic gzip checkpoint containing its protocol hash,
logical result hash and complete result. Resume verifies all existing checkpoints
before skipping work. Failed numerical candidates remain explicit p=1 records;
unexpected programming errors stop the process. Checkpoints, intermediate
predictions and private artifacts remain in ignored `data/experiments/`.

Progress records completed/remaining candidates by family, fit calls, status counts,
wall time, throughput, estimated completion, peak process RSS and free disk.
The runner pauses after a completed checkpoint if memory exceeds 3 GiB, free disk
falls below 2 GiB, or after 200 new candidates the estimated total candidate time
exceeds 102 minutes (1.5 times the approximately 68-minute estimate). Estimates
are family-weighted observed costs; they are not confidence limits. Report
rendering, validation and sensitivity refits are accounted for separately.

The initial preservation snapshot also included one untracked CPython bytecode
cache. Importing its unchanged source regenerated that cache. The original
snapshot is retained locally; a narrowly revised snapshot excludes only the
verified runtime cache and checks every other hash. The public
[audit](preservation_runtime_cache_audit.json) records both cache hashes, the
unchanged source hash and unchanged protocol identity. No scientific result,
input, statistical code, candidate or checkpoint was revised.
