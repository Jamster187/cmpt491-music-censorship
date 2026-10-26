# Academic evidence for feature expansion

Research date: 2026-10-26. This is a literature review, not a new analysis of our data. Entries distinguish association, retrospective description, experimental evidence, and forecasting. A paper supports investigation of a construct; it does **not** validate our proposed operationalization or imply transferable predictive improvement. Dataset reuse rights are separate from article access. UNKNOWN means the inspected evidence did not establish the detail.

## A01 — Limits of audio-only hit prediction

**François Pachet and Pierre Roy (2008). _Hit Song Science Is Not Yet a Science_. ISMIR, 355–360.** Peer-reviewed conference paper. [Official proceedings PDF](https://archives.ismir.net/ismir2008/paper/000133.pdf).

**Dataset/predictors/target:** Approximately 32,000 titles with 632 manually entered labels per title, plus two audio-feature sets; popularity labels are targets rather than permissible inputs. **Method/evaluation:** Supervised learning experiments comparing audio and human descriptors; exact fold construction and temporal isolation are UNKNOWN from the accessible extraction. **Finding:** Learning some descriptive labels did not translate into reliable popularity prediction. **Limits/application:** An older proprietary corpus and coarse popularity labels differ from our within-Hot-100 Top-10 task. The result is a warning against assuming audio determines success, not proof that every audio feature is useless. Publication year follows the official ISMIR 2008 index; some mirrored PDF headers incorrectly say 2009.

## A02 — Audio within a narrowly defined market

**Dorien Herremans, David Martens and Kenneth Sörensen (2014). _Dance Hit Song Prediction_. Journal of New Music Research.** Peer-reviewed journal article; the 2019 arXiv deposit is a later manuscript copy. [DOI](https://doi.org/10.1080/09298215.2014.881888), [author manuscript](https://arxiv.org/pdf/1905.08076).

**Dataset/predictors/target:** UK dance-chart material, especially 2009–2013, with earlier historical comparisons; acoustic features distinguish Top-10 tracks from lower-chart tracks, including positions 30–40. **Method/evaluation:** Multiple classifiers, repeated ten-fold cross-validation and a separate out-of-time exercise. **Finding:** Audio can discriminate the selected dance-chart classes, with changing relationships across time. **Limits/application:** Genre-specific sampling and the omitted middle positions make this easier/different from all Billboard entrants. Do not transfer published accuracy or treat repeated random folds as historical validation. Supports a small, version-controlled audio pilot after legal waveform/archive matching is solved.

## A03 — Prior artist success matters

**Myra Interiano, Kamyar Kazemi, Lijia Wang, Jienian Yang, Zhaoxia Yu and Natalia L. Komarova (2018). _Musical trends and predictability of success in contemporary songs in and out of the top charts_. Royal Society Open Science 5:171274.** Peer-reviewed. [DOI](https://doi.org/10.1098/rsos.171274), [full-text record](https://pmc.ncbi.nlm.nih.gov/articles/PMC5990848/).

**Dataset/predictors/target:** Large UK-oriented 1985–2015 song collection with AcousticBrainz descriptors; chart membership and prior artist chart success. **Method/evaluation:** Random forests; train on earlier years and test 2014, with additional 1994/2004 exercises; non-charted training examples are sampled to balance charted examples. **Finding:** Adding prior artist success materially improves discrimination over sound descriptors alone in their setting. **Limits/application:** Charted versus non-charted is different from Top 10 among already-charting songs; balanced samples change prevalence. Artist identity and historical success must be reconstructed before the target cutoff. No quantitative gain is projected for our data.

## A04 — Social influence and unpredictability

**Matthew J. Salganik, Peter Sheridan Dodds and Duncan J. Watts (2006). _Experimental Study of Inequality and Unpredictability in an Artificial Cultural Market_. Science 311:854–856.** Peer-reviewed randomized experiment. [DOI](https://doi.org/10.1126/science.1121066), [publication record](https://pubmed.ncbi.nlm.nih.gov/16469928/).

**Dataset/predictors/target:** 14,341 participants choosing unfamiliar songs; experimentally manipulated visibility of other listeners' choices; downloads/choice shares. **Method/evaluation:** Independent-choice condition compared with parallel social-influence markets; randomized conditions permit a stronger inference about that intervention than observational charts. **Finding:** Social information increases inequality and unpredictability of success. **Limits/application:** An artificial market is not the US industry and does not establish effects of a particular playlist, budget, or follower count. It motivates measuring exposure and feedback and retaining uncertainty even with rich content features.

## A05 — Musical differentiation and institutional context

**Noah Askin and Michael Mauskapf (2017). _What Makes Popular Culture Popular? Product Features and Optimal Differentiation in Music_. American Sociological Review.** Peer-reviewed; inspected author manuscript. [Stable author PDF](https://business.columbia.edu/sites/default/files-efs/pubfiles/25509/Mauskapf_productfeatures.pdf).

**Dataset/predictors/target:** Nearly 27,000 Hot 100 songs; audio-feature typicality relative to peers, artist familiarity, genre and institutional support; peak position and chart persistence. **Method/evaluation:** Observational ordered-logit and truncated-negative-binomial models, alternative specifications and historical comparisons; prior 52-week reference features in relevant models. **Finding:** Relative sonic positioning adds explanatory information alongside familiarity and industry context. **Limits/application:** Explanatory regression is not a held-out deployment test or a causal experiment. Modern feature extraction and selected chart population remain concerns. Supports prior-only similarity, prior artist history and dated label information, with separate evaluation of each block.

## A06 — Lyrical atypicality

**Jonah Berger and Grant Packard (2018). _Are Atypical Things More Popular?_ Psychological Science 29:1178–1184.** Peer-reviewed. [DOI](https://doi.org/10.1177/0956797618759465), [author PDF](https://faculty.wharton.upenn.edu/wp-content/uploads/2018/04/Atypicality.pdf).

**Dataset/predictors/target:** 1,879 unique songs and 4,200 rankings from seven genre charts in 2014–2016; lyric topic distributions and distance from genre norms; chart-based popularity. **Method/evaluation:** LDA representations and observational models with artist/airplay covariates; not a chronological forecasting benchmark. **Finding:** Within-genre lyrical differentiation is associated with popularity. **Limits/application:** Genre-conditioned chart selection and topic fitting affect interpretation; full-corpus prototypes would leak future information in our prediction design. A12 reaches a different conclusion under different novelty measures, so novelty's direction is a hypothesis, not a fixed rule.

## A07 — Repetition and processing fluency

**Joseph C. Nunes, Andrea Ordanini and Francesca Valsesia (2015). _The power of repetition: Repetitive lyrics in a song increase processing fluency and drive market success_. Journal of Consumer Psychology.** Peer-reviewed; online publication December 2014. [DOI](https://doi.org/10.1016/j.jcps.2014.12.004), [author PDF](https://www.francescavalsesia.com/uploads/1/0/5/1/105151509/the_power_of_repetition_jcp_2015.pdf).

**Dataset/predictors/target:** Controlled lyric/song-excerpt experiments and Billboard 1958–2012 comparisons; lexical repetition; fluency, chart success and time to number one. **Method/evaluation:** Laboratory manipulation plus observational chart models, including number-one versus low-chart comparisons; not a general held-out Top-10 benchmark. **Finding:** Repetition facilitates processing experimentally and is associated with selected market outcomes. **Limits/application:** Laboratory mechanisms do not make the chart association causal; extreme-group sampling limits transfer. Supports compression and repetition measures with careful chorus expansion/formatting checks, not many redundant repetition formulas.

## A08 — Historical changes in sound

**Matthias Mauch, Robert M. MacCallum, Mark Levy and Armand M. Leroi (2015). _The evolution of popular music: USA 1960–2010_. Royal Society Open Science 2:150081.** Peer-reviewed. [DOI](https://doi.org/10.1098/rsos.150081), [full-text record](https://pmc.ncbi.nlm.nih.gov/articles/PMC4453253/).

**Dataset/predictors/target:** Approximately 17,000 chart songs with audio excerpts; harmonic and timbral representations; stylistic diversity and historical change. **Method/evaluation:** Topic/cluster-based musical representation and temporal descriptive analysis; no hit-forecast holdout. **Finding:** Musical history contains uneven stylistic change rather than one uniform trend. **Limits/application:** Excerpts, coverage and extraction choices shape measured diversity. Published historical transitions are not preselected breakpoints for our study. Supports timbre, harmony, instrumentation and novelty as historically useful additions even if their commercial predictive value is modest.

## A09 — Timbre, pitch and loudness

**Joan Serrà, Álvaro Corral, Marián Boguñá, Martín Haro and Josep Lluís Arcos (2012). _Measuring the Evolution of Contemporary Western Popular Music_. Scientific Reports 2:521.** Peer-reviewed. [DOI](https://doi.org/10.1038/srep00521).

**Dataset/predictors/target:** Million Song Dataset-derived recordings with dated metadata and pitch/timbre/loudness descriptors; aggregate musical change across historical periods. **Method/evaluation:** Statistical/network descriptions of feature distributions and transitions; no chronological song-success prediction test. **Finding:** The study reports changes in musical vocabulary and loudness across its corpus. **Limits/application:** Catalog dates, sampled recordings and production/mastering versions may confound historical comparisons. Our archive overlap is UNKNOWN. Supports sound-production measures, but not an assumption that newly measured remasters faithfully describe the sound originally charted.

## A10 — Lyrical simplicity and available song choices

**Michael E. W. Varnum, Jaimie Arona Krems, Colin Morris, Alexandra Wormley and Igor Grossmann (2021). _Why are song lyrics becoming simpler? A time series analysis of lyrical complexity in six decades of American popular music_. PLOS ONE 16:e0244576.** Peer-reviewed. [Article/DOI](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0244576).

**Dataset/predictors/target:** 14,661 US chart-song lyrics, 1958–2016; compression, proxies for new song supply and socioecological covariates; annual complexity and song chart position. **Method/evaluation:** Rank correlations, detrending, autocorrelation corrections, auto.ARIMA and exploratory multilevel song models; future aggregate projections are not observed held-out song forecasts. **Finding:** Simpler lyrics and greater song-choice supply are associated; many contextual relationships weaken under time-series controls. **Limits/application:** Catalog-based supply is incomplete and retrospective; few annual units versus many songs. Supports compression and strictly prior chart-entry supply, while requiring trend/autocorrelation controls in any later approved study.

## A11 — Multiple dimensions of lyric form

**Emilia Parada-Cabaleiro, Maximilian Mayerl, Stefan Brandl, Marcin Skowron, Markus Schedl, Elisabeth Lex and Eva Zangerle (2024). _Song lyrics have become simpler and more repetitive over the last five decades_. Scientific Reports.** Peer-reviewed. [Original DOI](https://doi.org/10.1038/s41598-024-55742-x), [author correction](https://www.nature.com/articles/s41598-024-62519-9).

**Dataset/predictors/target:** Large lyric corpus spanning 1970–2020 and five genres; lexical diversity, structure, rhyme, readability and affect; release-year trends and lyric-view popularity. **Method/evaluation:** Genre-specific regression/descriptor analyses; retrospective trend and popularity associations, not a historically available Billboard predictor benchmark. **Finding:** Simplification and repetition vary across genres and descriptor families. **Limits/application:** Current lyric views are not original chart performance. A correction fixes the difficult-word syllable threshold and changes numerical results and descriptor rankings; use corrected tables. Supports a diverse small set of linguistic-form measures rather than treating word count alone as complexity.

## A12 — Novelty is multidimensional and evidence conflicts

**Yulin Yu, Pui Yin Cheung, Yong-Yeol Ahn and Paramveer S. Dhillon (2023). _Unique in What Sense? Heterogeneous Relationships between Multiple Types of Uniqueness and Popularity in Music_. ICWSM 17:914–925.** Peer-reviewed conference paper. [Article/DOI](https://ojs.aaai.org/index.php/ICWSM/article/view/22199).

**Dataset/predictors/target:** More than 50,000 songs; lyric, chord and audio uniqueness; music popularity. **Method/evaluation:** Multiple statistical association models and mediation analyses; exact forecast split is UNKNOWN from the inspected abstract, and no chronological predictive validation is claimed here. **Finding:** Novelty is negatively associated with popularity in this dataset, with different roles for audio, lyrics, genre and repetition. **Limits/application:** This differs from simple optimal-differentiation claims. Dataset/target/representation differences prevent a universal direction-of-effect assumption. Compare multiple meaningful reference sets, but do not search thousands of distance variants for favorable results.

## A13 — Lyrics in a short-horizon popularity system

**Giulio Prevedello, Ines Blin, Bernardo Monechi and Enrico Ubaldi (2024). _Lyrics for Success: Embedding Features for Song Popularity Prediction_. NLP4MusA workshop proceedings.** Peer-reviewed workshop paper. [ACL record and paper](https://aclanthology.org/2024.nlp4musa-1.13/).

**Dataset/predictors/target:** 12,428 Spotify tracks; lyric embeddings/stylometry plus audio, playlist/platform and early reactions; popularity 15 days after release. **Method/evaluation:** Gradient-boosted models and embedding experiments; chronological train/validation/test subsets (9,812/1,391/1,225), with internal cross-validation. Some language-model adaptation uses training plus validation text. **Finding:** Embeddings contribute within a multimodal short-horizon system. **Limits/application:** Early post-release reaction features make this partly nowcasting, not pure pre-release forecasting. Spotify popularity differs from Billboard outcomes; platform access/terms have changed. Supports local scalar novelty and dated exposure research, not importing reported gains or using current Spotify snapshots.

## A14 — Metadata can look strong under non-temporal evaluation

**Mengyisong Zhao, Morgan Harvey, David Cameron, Frank Hopfgartner and Valerie J. Gillet (2023). _An Analysis of Classification Approaches for Hit Song Prediction using Engineered Metadata Features with Lyrics and Audio Features_.** Inspected arXiv preprint; peer-reviewed venue status not established here. [Full text](https://arxiv.org/html/2301.13507v1).

**Dataset/predictors/target:** Billboard Hot 100 song sample with Spotify audio, lyrics, title topics, genre and popularity-continuity features; Top-10 classification. **Method/evaluation:** Five classifiers including random forest/logistic regression; 80/20 split and five-fold tuning with oversampling. Temporal dependence is explicitly not addressed. **Finding:** Metadata-inclusive models outperform narrower feature sets in that evaluation. **Limits/application:** Reported high performance cannot be treated as historical forecasting evidence. Inspect feature chronology, artist overlap and oversampling placement. This is a methodological caution and candidate-discovery lead, not a performance target for our repository.

## A15 — Chart dynamics and established acts

**Marta Ewa Lech, Sune Lehmann and Jonas L. Juul (2024). _Is it getting harder to make a hit? Evidence from 65 years of US music chart history_.** arXiv preprint; no journal status established in inspected record. [Stable record](https://arxiv.org/abs/2405.07574).

**Dataset/predictors/target:** Hot 100 history since 1958; rank trajectories, chart lifetime, turnover and established versus new chart acts. **Method/evaluation:** Historical descriptive comparisons and trajectory clustering; no prospective Top-10 validation. **Finding:** Persistence and turnover change differently at different ranks; established acts occupy more positions in recent periods. **Limits/application:** Chart rules and consumption systems also change; chart selection does not reveal all released songs. Supports prior-credit success, competition, turnover and explicit methodology context. Our exact full-credit histories are weaker proxies for artist entities and must be named accordingly.

## A16 — Memory, turnover and trajectory structure

**Arthur A. B. Pessa, Angelo A. Flores, Matjaž Perc and Haroldo V. Ribeiro (2026). _Charting the life of Billboard hits through memory, turnover, and predictability_. Royal Society Open Science 13:261312.** arXiv record reports acceptance and journal reference; journal full text not independently inspected. [Record](https://arxiv.org/abs/2607.11446), [journal DOI](https://doi.org/10.1098/rsos.261312).

**Dataset/predictors/target:** Nearly seven decades of Hot 100 songs and six decades of Billboard 200 albums; persistence, re-entry, turnover and rank dynamics. **Method/evaluation:** Rank-turbulence divergence, entropy and trajectory clustering; descriptive uncertainty is not a deployed forecast's accuracy. **Finding:** Songs and albums exhibit different persistence/memory patterns and recurrent trajectory types. **Limits/application:** Full-run trajectory labels are future information at debut. Supports prior-chart competition measures and explicitly landmarked nowcasting; does not authorize full-run clustering as a predebut feature.

## A17 — Directly relevant cultural-trend research, with dependence controls

**Markus Foramitti, Urs Markus Nater, Claus Lamm and Maurício Martins (2025). _Societal crises disrupt long-term increases in stress, negativity, and simplicity in US Billboard song lyrics from 1973 to 2023_. Scientific Reports 15:41733.** Peer-reviewed; preregistered study plus disclosed exploratory analyses. [Article/DOI](https://www.nature.com/articles/s41598-025-28327-5).

**Dataset/predictors/target:** 266,086 song-week entries before filtering and 20,186 retained unique lyric texts; LIWC stress, VADER sentiment, compression, income and event periods. **Method/evaluation:** Aggregated temporal trends and interrupted-time-series models; dynamic OLS with three lags and HAC errors supplements original preregistered OLS; empirical comparisons with other temporal windows. **Finding:** Long trends and event associations differ; income relationships weaken after trend control. **Limits/application:** Repeated chart entries weight persistent songs; English-only filtering, event choice and observational confounding matter. This motivates reviewing exposure weighting and temporal dependence later. We adopt no COVID breakpoint, causal conclusion, model or new analysis from it.

## A18 — Listener networks, not performer-credit networks

**Niklas Reisz, Vito D. P. Servedio and Stefan Thurner (2024). _Quantifying the impact of homophily and influencer networks on song popularity prediction_. Scientific Reports 14:8929.** Peer-reviewed. [DOI/primary PDF](https://www.nature.com/articles/s41598-024-58969-w.pdf).

**Dataset/predictors/target:** Last.fm listening and listener social links; musical homophily/influencer information; subsequent song popularity. **Method/evaluation:** Network-informed prediction models; exact split, sample sizes and leakage controls are UNKNOWN because full text was not reliably retrievable during this review. **Finding:** The abstract reports predictive relevance of listener-network structure. **Limits/application:** Do not transfer this evidence to writer/producer collaboration centrality: those are different networks. The LFM-2b download is now withdrawn, and this paper's data access must be separately established. Treat as a useful but partially inspected lead, not implementation-ready evidence.

## A19 — Human-coded historical themes

**Peter G. Christenson, Silvia de Haan-Rietdijk, Donald F. Roberts and Tom F. M. ter Bogt (2019; online 2018). _What has America been singing about? Trends in themes in the U.S. top-40 songs: 1960–2010_. Psychology of Music 47:194–212.** Peer-reviewed. [DOI](https://doi.org/10.1177/0305735617748205), [university manuscript](https://research-portal.uu.nl/files/70012731/0305735617748205.pdf).

**Dataset/predictors/target:** 1,040 Top-40 songs, 19 human-coded themes; historical theme prevalence. **Method/evaluation:** Content coding and structural-change analysis; this is descriptive history, not a popularity forecast. Exact coding reliability estimates were not extracted here. **Finding:** Relationship themes persist while several lifestyle/sexual themes change, and many civic/religious themes remain relatively uncommon. **Limits/application:** A sampled Top-40 corpus differs from our month-end population; themes overlap existing classifiers and human/model constructs are not interchangeable. Supports targeted references, perspective and a manual validation sample before expanding classifiers.

## A20 — Rhyme, grammar and lyric form

**Rudolf Mayer, Robert Neumayer and Andreas Rauber (2008). _Rhyme and Style Features for Musical Genre Classification by Song Lyrics_. ISMIR, 337–342.** Peer-reviewed conference paper. [Official paper](https://archives.ismir.net/ismir2008/paper/000235.pdf).

**Dataset/predictors/target:** 397 lyric texts in ten genres; rhyme, parts of speech, simple text statistics and bag-of-words; genre classification. **Method/evaluation:** Naïve Bayes, SVM, decision trees and nearest neighbors under ten-fold cross-validation. **Finding:** Form/style features complement lexical content in this small classification task. **Limits/application:** Genre prediction is not chart-success prediction, and the small corpus does not validate multilingual or historical dialect coverage. Supports syllable/rhyme and grammatical structure as genuinely different lyric information, with local human checks and no automatic claim of commercial value.

## What the combined evidence supports

Prior success and exposure deserve priority for commercial prediction; lyric structure, sound and temporal measurement context deserve priority for cultural analysis. None of the inspected studies validates a specific performance gain for our exact 28,041-identity population. Network evidence is heterogeneous, novelty results conflict, and strong random-split accuracy is not a substitute for chronological evaluation. Research targets and data access have to be reconsidered under current licenses, not inherited from publication-year APIs.
