# Methods and interpretation

## Scope and population

The user explicitly authorized this execution campaign beyond the repository's
ordinary maintenance scope. The method inventory follows the Chapters 5–8 methods
listed in that request; no lecture PDFs were present in the checkout. No previous
regression, breakpoint, genre-production or classifier-production campaign is repeated.
The supplied chart snapshot's **reported upstream** is the
[Billboard archive](https://github.com/mhollingshead/billboard-hot-100), not evidence
of an independent verification of Billboard's history.

The only fitted input is `data/public/songs.csv`: 28,041 exact original title/artist
identities in the monthly study population. Chart dates are not release dates.
The 42 lyrical scores are four LyricLens, seven Detoxify, 28 GoEmotions and three
sentiment dimensions. Analyses require all 42 scores: 20,979 songs qualify. Missing
scores are not zero and are not imputed. [Coverage by decade](coverage.csv) records
the complete-case selection; the principal results do not represent songs without
usable scores. Alternate credits, recordings, versions and collaborations are not
merged, and exact artist credits are not necessarily distinct performers.

## Chronological separation and scenarios

The shared primary split is training histories ending before 2010, validation
histories beginning in 2010 or later and ending before 2018, and test histories
beginning in 2018 or later and ending before 2026. Whole-history boundary purging
gives 16,079 / 1,907 / 2,382 songs, with 611 complete-score songs outside these three
sets. Preprocessing never sees validation/test observations. Splits use observed
chart histories; later re-entries remain possible. Boundary purging excludes
continuing hits and disproportionately affects recent/long-running songs.

Classification additionally evaluates 1990–1999, 2000–2009 and 2010–2017 outer
windows. For each outer start, the immediately preceding five years form the inner
validation window; earlier whole histories form inner training. After selecting
the tree using inner validation, it is refit to all whole histories ending before
the outer start. All fitted transforms belong to that training population.

The chart prediction scenario is a hypothetical prediction from measured lyrics
before first chart entry, **conditional on eventual Billboard inclusion**. Only
the 42 lyrical scores are predictors. Final ranks, duration, chart points, dates,
genre and present-day MusicBrainz catalogs are excluded from these models. The
actual scores were computed retrospectively by modern pretrained classifiers;
their availability and training corpora do not establish an authentic historical
forecast. No claim concerns whether an arbitrary released song becomes a hit.

Top 10 means observed best rank ≤10. Long longevity means strictly above the
inner-training 75th percentile of observed chart weeks, held fixed for that outer
fold. It is not an uncensored lifetime-duration target. Association transactions
use the separate fixed pre-2010 training 75th percentile. Broad genre retains Pop,
R&B / Soul, Rock, Hip-Hop / Rap, Country, and Electronic / Dance, pooling the other
ten labels into “Other broad genre.” These are classified metadata labels, not
ground truth. The existing [genre prompt](../../docs/genre/llm/prompt.txt) explicitly
excluded lyrics/content scores/chart performance; artist/song familiarity and
shared catalog sources can still create dependencies.

## Frequent patterns

The comparison mines exactly the same pre-2010 complete-score song transactions.
For each score, and MusicBrainz median duration, recording count and release count,
training Q25/Q75 define low (`x ≤ Q25`), middle, and high (`x > Q75`). Low/high tails
emit categorical items; the middle interval emits no tail item. Equal quantiles
and discrete ties are retained, so marginal item frequencies need not equal 25%.
Missing metadata emits no item. Each transaction also contains primary genre,
debut decade, Top-10 yes/no and long-chart yes/no. No variable can contribute two
mutually exclusive values to an itemset. A missing or middle item is not a low score.

Support thresholds were fixed at 5%, 8% (primary) and 12%, with minimum count
`ceil(support × training N)` and maximum size four. Apriori uses breadth-first
candidate joins and downward-closure pruning with vertical support counts.
ECLAT uses depth-first intersections of vertical transaction bitsets. FP-Growth
uses frequency-ordered prefix trees and recursive weighted conditional databases.
All enumerate deterministically; independent brute-force fixtures check their
counts, and the actual-data benchmark requires identical complete itemset maps.
This compares these Python implementations, not universal algorithm complexity
or best optimized-library performance. Wall timings exclude shared transaction
construction. RSS is the process high-water mark at completion, not isolated
incremental memory per algorithm; algorithms run sequentially in one process.

Closed/maximal sets are derived by checking **every compatible single-item
extension**, including size-five extensions of published size-four sets. If an
extension has equal support the original is not closed; any frequent extension
means it is not maximal. This suffices to test the global definitions without
unbounded enumeration. All true closed/maximal sets within the size cap are retained;
larger closed/maximal sets themselves are outside scope.

The implementation follows the structures described by
[Han et al.'s FP-tree paper](https://www.cs.sfu.ca/~jpei/publications/dami03_fpgrowth.pdf)
and [the SPMF ECLAT documentation](https://www.philippe-fournier-viger.com/spmf/Eclat_dEclat.php).
No SPMF code or additional mining dependency is used.

## Association rules and inference

Every primary frequent itemset of size two through four yields all singleton-
consequent rules, giving one to three antecedent conditions. A bounded supplemental
search covers every directed cross-domain singleton pair with a training joint
count of at least `max(20, ceil(.005 × N))`; already-primary rules are deduplicated.
It tests both observed positive and negative consequents. Negative numerical items
mean an **observed value outside the named tail**. Missing consequent metadata is
excluded from their denominator, while the complete positive-item transaction
population is retained. Accordingly, positive and negative metadata results can
have different N. Genre complements retain the full population. No complements
of multi-condition antecedents or exhaustive higher-order rare search are attempted.

Each rule stores training, validation and test sample size, antecedent count,
joint count, support, confidence, consequent baseline, lift, leverage and risk
difference. It also stores the highest confidence of its immediate simpler
antecedent rules and improvement over that best parent. Confidence alone, including
confidence near one for a common negative outcome, is not evidence of usefulness.

One two-sided asymptotic Cochran–Mantel–Haenszel test per searched rule evaluates
held-out association conditional on debut year. Evaluation requires at least 20
observations in each pooled antecedent/consequent marginal and complement;
unsupported/degenerate tests contribute p=1. Benjamini–Yekutieli correction uses
**every searched rule**, including same-family, complementary, null and unsupported
rules. There is no selective p-value refinement. CMH has large-sample and conditional
independence assumptions; sparse rare cells and repeated artists can weaken them.
BY does not repair an invalid p-value or turn previously inspected evaluation
data into independent confirmation. No rare-cell q-value alone supports a claim.

Interpretation distinguishes reconstruction (A), measurement overlap (B), strict
cross-domain relationships (C), multidimensional conditions (D), and historical
comparisons (E). A target domain also present among antecedents retains B even if
an incidental condition introduces another domain. The strict priority flag
requires the consequent's broad domain to be absent from **all** antecedents.
The five broad domains are lyrics, genre, chart performance, history and metadata.
No automatic correlation-based feature deletion occurs. This vocabulary contains
no direct deterministic reconstruction rule, but overlap controls are retained.

The display leaderboard requires ≥100 test antecedents and ≥20 joint observations,
excludes calendar consequents/conditions, prioritizes positive lift across all
three splits, then global BY status and absolute test risk difference. It is a
post-hoc display order, not new model selection. The presentation shortlist takes
up to two distinct variable combinations per domain/direction and single/multiple-
condition stratum. Multidimensional examples must exceed their best parent's
test confidence by more than one percentage point. All raw rules remain available.

For those selected examples, decade, genre and pre-/post-2020 diagnostics retain
unsupported cells and require subgroup N≥100 plus antecedent N≥20 for adequate
labels. Fixed-rule intervals use 299 exact-artist-credit cluster bootstraps.
These marginal, post-selection intervals do not include selection uncertainty.
The supplemental conditional table contains all eligible positive cross-domain
singleton pairs, excluding a genre-valued side, across test genres. A descriptive
reversal flag requires opposite pooled/within-genre risk differences, each at least
five percentage points, and adequate subgroup counts. These are descriptive
screens, not separately certified subgroup hypotheses or proof of Simpson's paradox.

During implementation review, the priority-domain definition was tightened and
negative numerical denominators were corrected to exclude missing values. The
entire first development output/checkpoint set was retained locally before the
final full rerun. This did not change the itemset universe or any prior campaign.

## Classification and interpretable rules

Decision trees evaluate depths 3–6 with unweighted and balanced class weights,
minimum leaf size 50, and a fixed seed. Inner validation selects greatest balanced
accuracy, then macro F1, then smaller depth, then unweighted fitting. The complete
eight-candidate grid is saved for every target/window. Gaussian Naïve Bayes uses
all 42 training-standardized scores with fixed `var_smoothing=1e-9`; no test-driven
tuning, threshold optimization or probability calibration is performed.

Tree root-to-leaf IF–THEN paths form the rule classifier. The exported rule engine
casts inputs to float32 exactly as scikit-learn does, and every song matches exactly
one leaf. Native tree, numeric export and independent rule predictions must agree.
The Bayes export contains numeric means, variances, scales and class priors; an
independent NumPy-only demonstration replays its predictions. No executable model
pickle is published. The rule classifier is an equivalent explanation of the tree,
not independent evidence of a second successful learner.

Metrics include accuracy, balanced accuracy, macro/weighted precision, recall and
F1, binary positive precision/recall, per-class support, and complete confusion
matrices. Baselines are training-majority and training-frequency stratified random
prediction with fixed seed. Sparse or absent classes are visible; zero-division
precision/F1 are zero. Balanced accuracy averages recall over classes present in
the evaluation group, while macro metrics use the fixed target-label inventory.

Fixed-model balanced-accuracy and macro-F1 gains over the majority baseline receive
299 two-year-block and 299 exact-artist-credit bootstrap intervals separately.
Small numbers of time blocks limit temporal intervals, particularly in the latest
eight-year window. Historical and genre metrics and the subset of future songs
with previously unseen exact credits are descriptive sensitivity checks. They do
not resolve shared performers, repeated recordings or all time/artist dependence.
No p-value claim is attached to selecting the best validation tree.

The learners use the recorded scikit-learn implementation of
[decision trees](https://scikit-learn.org/1.5/modules/tree.html) and
[Gaussian Naïve Bayes](https://scikit-learn.org/1.5/modules/naive_bayes.html).
Correlated classifier dimensions violate the latter's conditional-independence
assumption; its probabilities are not presented as calibrated certainty.

## Clustering

All 42 scores are standardized using the primary training set. Three fixed
representations are compared: standardized 42 dimensions; full-SVD PCA retaining
at least 90% of training variance; and family-balanced standardized features,
dividing each family by the square root of its feature count. Each family's summed
training marginal variance is then one. This balances dimension counts, not all
correlations, semantic quality or measurement noise. PCA has 28 components here.

K=2–12 is evaluated for each representation and each method: 99 configurations.
K-means uses all training songs, ten initializations and at most 300 Lloyd steps.
Alternating k-medoids and Ward agglomeration use a common seeded 1,200-song training
sample. K-medoids alternates nearest-medoid assignment with the exact minimum
within-cluster distance-sum medoid; it is a bounded local heuristic, **not full PAM
swap optimization**. Its objective must be nonincreasing, and saved medoids must
be actual training songs. The largest individual distance matrix is 11.52 MB.

Ward has no native out-of-sample predictor. Validation/test and full-population
descriptions explicitly use nearest training-cluster-centroid transfer. K-means
uses its fitted centers and k-medoids its fitted exemplars. Native sample sizes
and transferred full-training sizes are both retained. No full-population
quadratic-distance clustering is run.

Each base fit has two additional seeded resample fits: K-means uses 80% of training
songs; the expensive methods use new 1,200-song samples. Adjusted Rand indices
compare assignments on the same validation songs. These are only two resample
replicates and hold training preprocessing fixed, so they are conditional stability
diagnostics, not precise uncertainty estimates for the full pipeline.

Within each method/representation, select highest validation silhouette among
configurations with minimum transferred training-cluster share ≥1% and mean
resample ARI≥0.6; ties prefer smaller K. If none qualify, explicitly mark the best
silhouette fallback unsupported. Test data never choose K. Silhouettes use fixed
1,200-song samples. Each configuration's validation scores and selected models'
test scores are also computed in the original standardized 42-dimensional space;
PCA/weighted-space silhouette values alone cannot establish superiority across
representations. High silhouette from a tiny outlier group is not interpreted as
an interesting taxonomy.

All nine selected/fallback configurations have full numeric exports, song assignments,
profiles, genre compositions, decade prevalence and chart-performance distributions.
These descriptive tables assign all complete-score songs whose observed histories
end before 2026, including boundary songs excluded from model evaluation. Saved
assignment split labels distinguish them. Raw pre-/post-2020 prevalence contrasts
compare very unequal historical spans and are not breakpoint analyses. Separate
299 artist-credit bootstrap intervals and prevalence standardized to the training
broad-genre mixture are sensitivities. Genre standardization includes only genres
with ≥100 songs on both sides and reports retained training genre mass. No causal
COVID inference follows from any of these comparisons.

See the [scikit-learn clustering reference](https://scikit-learn.org/1.5/modules/clustering.html)
for K-means, Ward, silhouette and ARI definitions. Cluster selection is unsupervised;
genre/chart summaries do not choose the fitted configurations.

## Preservation and reproducibility

Raw inputs, Phase 1/research databases, lyrics, old analyses and recovered experiment
artifacts retain their original paths/bytes. The full pre-existing data/analysis
snapshot is local and never committed. Public results contain only public identities,
numeric features/predictions, summaries and ordinary numeric model specifications.
Large checkpoints and initial development outputs stay ignored. No acquisition,
external model training, HTTP metadata retrieval or new breakpoint campaign runs.

Transactions are sorted canonically before hashing, so serializing/reordering the
bin-schema keys cannot change their identity; a regression fixture verifies this.
Seed 491202610, deterministic enumeration, source/input hashes, atomic file
replacement, checkpoint checksums and the numerical environment make the campaign
auditable. The scientific checks independently recount itemsets/rules, recompute
global BY, replay saved model metrics and cluster assignments, refit chronological
classifiers and an outcome-blind clustering grid subset, and check all existing
data/analysis hashes. Operational timings are not expected to be bitwise repeatable.
Earlier frozen numerical results and documentation remain unchanged.
