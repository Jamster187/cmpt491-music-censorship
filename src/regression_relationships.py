"""Definition-based interpretation policy; no correlations or test scores are used."""
from __future__ import annotations

import regression_spec as spec

VERSION = "meaningful-v1"
A = "A: circular/reconstruction"
B = "B: redundant/same-family"
C = "C: cross-domain"
DATES = set(spec.original.DATES)
DURATIONS = set(spec.original.DURATIONS)
EXPOSURE = {"chart_weeks", "weekly_observation_count", "snapshot_months_selected"}
FIRST = {"first_chart_date", "first_snapshot_month"}
LAST = {"last_chart_date", "last_snapshot_month"}

RULES = [
    dict(id="row_date_count_alias", kind="pair", targets=["chart_weeks","weekly_observation_count"],
         explanation="Rows and distinct chart dates count the same weekly appearances; duplicates are the documented exception.",
         sources=["data/public/README.md:76","src/public_dataset.py:126"]),
    dict(id="same_career_calendar", kind="pair", targets=sorted(DATES),
         explanation="First/last weekly dates and first/last selected months locate the same observed chart career. Exclude these alternative calendar coordinates as episode reconstruction, including opposite endpoints. They are not asserted to be mathematically identical; gaps and monthly sampling matter.",
         sources=["data/public/README.md:74","data/public/README.md:78","src/month_end_snapshots.py"]),
    dict(id="same_recording_duration", kind="pair", targets=sorted(DURATIONS),
         explanation="Min/median/max summarize the same set of distinct positive recording lengths. Treat predicting one length summary from another as reconstruction of the same physical measurement. Different versions prevent universal equality; this is an explicit interpretation restriction, not an equality claim.",
         sources=["data/public/README.md:83","data/public/README.md:94","src/public_dataset.py"]),
    dict(id="career_interval_exposure", kind="combination", targets=sorted(EXPOSURE),
         explanation="Both a first and a last coordinate bound the same chart-history window whose observations/months are counted. Exclude interval-to-exposure reconstruction. Counts need not equal elapsed intervals because of gaps; this conservative scope rule follows the shared history window, not a correlation threshold.",
         required_groups=[sorted(FIRST),sorted(LAST)],sources=["data/public/README.md:74","data/public/README.md:76","data/public/README.md:78"]),
    dict(id="sentiment_complement", kind="combination", targets=spec.original.SENTIMENT,
         explanation="The other two softmax outputs reconstruct the remaining sentiment probability. Already forbidden by the original campaign; this policy does not restore those candidates.",
         sources=["analysis/planning/regression_search/audit.py","docs/regression_search_plan.md"]),
]


def domain(name):
    if name.startswith(("ll_","detox_")):
        return "lyrical_content"
    if name.startswith(("emotion_","sentiment_")):
        return "lyrical_affect"
    if name in spec.original.GENRES:
        return "genre"
    if name in DATES or name in {"mb_release_year","chart_date","snapshot_chart_date"}:
        return "historical_calendar"
    if name.startswith("mb_"):
        return "musicbrainz_metadata"
    if name in set(spec.original.HISTORY_COUNTS) | {"best_chart_rank","weekly_rank","monthly_rank",
            "reported_last_week_rank","reported_peak_position","reported_weeks_on_chart"}:
        return "chart_performance"
    raise ValueError("Variable has no reviewed domain: "+name)


def circular_reasons(target, predictors):
    p=set(predictors)
    reasons=[]
    if target in {"chart_weeks","weekly_observation_count"} and p & ({"chart_weeks","weekly_observation_count"}-{target}):
        reasons.append("row_date_count_alias")
    if target in DATES and p & (DATES-{target}):
        reasons.append("same_career_calendar")
    if target in DURATIONS and p & (DURATIONS-{target}):
        reasons.append("same_recording_duration")
    if target in EXPOSURE and p & FIRST and p & LAST:
        reasons.append("career_interval_exposure")
    if target in spec.original.SENTIMENT and set(spec.original.SENTIMENT)-{target} <= p:
        reasons.append("sentiment_complement")
    return reasons


def classify(target, predictors):
    reasons=circular_reasons(target,predictors)
    same=[p for p in predictors if domain(p)==domain(target)]
    cross=[p for p in predictors if domain(p)!=domain(target)]
    return dict(category=A if reasons else B if same else C,circular_rules=reasons,
        target_domain=domain(target),predictor_domains=[domain(p) for p in predictors],
        same_family_predictors=same,cross_domain_predictors=cross,
        mixed_domains=bool(same and cross),pure_cross_domain=not reasons and not same)


def policy():
    names=sorted({p for t in spec.specs() if t["model_family"]=="regression" for p in [t["target"]]+t["predictors"]})
    return dict(version=VERSION,categories={"A":A,"B":B,"C":C},rules=RULES,
        variables={n:dict(domain=domain(n),availability=spec.original.availability(n)) for n in names},
        precedence="A if any reconstruction rule applies; otherwise B if any predictor shares the target domain; otherwise C. Mixed B/C models remain B with cross-domain tags.",
        domain_rationale={"lyrical_content":"LyricLens and Detoxify measure overlapping content moderation constructs.",
            "lyrical_affect":"GoEmotions and sentiment measure related affective constructs; conservatively grouped together.",
            "genre":"Frozen genre assignments.","historical_calendar":"Calendar placement, including linked release year.",
            "musicbrainz_metadata":"Counts and recording-length summaries from the same linked metadata evidence.",
            "chart_performance":"Ranks, exposure counts and chart-point totals."},
        cross_domain_caveat="Different constructs can still share lyrics, models or provenance. C is not evidence of independent measurement or causality.",
        retained_examples=["MusicBrainz counts remain B, including counts versus durations.",
            "Total chart points versus weeks/rank remains B: sum(101-rank) cannot be recovered exactly from count plus best rank.",
            "Monthly sample count versus weekly count remains B: sampling and gaps affect the counts.",
            "A single episode endpoint versus a count remains available; the two-endpoint combination is excluded."],
        selection="Filter saved complete validation hierarchies; retain original skill/k/id order. No final-test values or correlation cutoffs enter the policy.",
        evaluation="POST-HOC EXPLORATORY: the 2018-onward test was inspected in the unrestricted campaign; no newly untouched holdout is claimed.")
