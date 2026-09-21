# Broad genre evidence refinement, v2 pilot

Same 300 song IDs, same frozen raw evidence and 16 categories as v1. No new source,
entity matching, inferred artist nationality, lyric reading or classifier feature
is used. The original v1 reports and decisions are preserved.

The v1 dictionary already mapped compatible subgenres to broad categories. This
experiment changes support and selection, not the taxonomy or alias dictionary.
Spelling variants and exact synonyms are collapsed into tag families; different
subgenres can collectively support their category. Rap and hip-hop count as one
family, while trap and southern hip-hop remain distinct. Multiple labels are
*compatible observations*, not necessarily independent annotators.

Frozen candidate settings live in `refinement_rules.json`. For each broad category
at each semantic level, keep raw labels, distinct tag families, provider/entity
counts, maximum votes per family, and backed-family count (at least two votes).
Duplicate cache responses, editions, genres/tags copies and aliases do not add
votes. Maxima across versions are retained conservatively as historical support;
these are not independent voters or calibrated confidence.

Strong direct support requires either a label with at least three votes, at least
two distinct compatible families with at least two votes each, three compatible
families with at least one having two votes, or agreement of two
direct providers. Provider agreement is not proof of independence: sources may
share references. Recording/accepted song-item evidence controls primary labels.
Release and artist support is separately reported; existing release links include
compilations, so neither context tier can independently establish a primary.

If one category is strong, assign it. With multiple strong categories, ignore only
generic Pop (`pop`, `pop music`, `am pop`) when a specific category is strong.
Specific Pop styles and composite tags with backed support remain competing evidence.
Isolated one-vote style tags cannot disable parent suppression; if no label is
backed, all labels are considered. A pre-review implementation correction aligned
this parent check with the support gate and collapsed additional spelling synonyms;
the initial trial is retained locally, and the numerical thresholds were unchanged at that correction. Generic Rock
is a parent when Metal/Alternative is strongly supported; hard rock and compound
styles remain evidence for Rock, not automatic Metal. A contender can dominate
only when its maximum tag support is at least twice every remaining competitor's
and its backed-family count is no smaller. Otherwise preserve ambiguity. Category
order is never a tie-breaker for a primary. Other must pass the same evidence gate.
No strong direct support means insufficient evidence, even if context exists.
`genre_ambiguous` means unresolved primary competition; a dominant primary can
still have secondary genres.

Keep both `primary_genre` and `mapped_genres` (all strongly supported direct broad
categories), plus `secondary_genres`, weak `all_mapped_evidence`, per-level support,
candidates, parent suppression and the exact decision reason. A weak tag remains
in raw evidence; it is not silently deleted. These thresholds are pilot hypotheses,
not approved production rules. The review does not override assignments.

```sh
python3 src/genre_refinement.py
python3 -m unittest discover -s tests -v
python3 src/genre_validate.py
```

Results go to `reports/genre_refinement/`, with full support records in the ignored
`data/experiments/genre_refinement/`. Never run v1's builder to replace its report
as part of this experiment. No full-population genre labels are generated.

Development was exploratory on this pilot, not a held-out accuracy study. The
first gate yielded 75 primaries; parent/synonym consistency correction yielded
80. Inspection of coherent broad-category clusters motivated one final extension:
three compatible families with at least one two-vote family can also establish
strong support. All-one-vote clusters still cannot. Trial summaries are retained
locally; no production thresholds are approved by these comparisons.

Review selection uses up to nine primary cases from each of the six older periods
and six from the latest period, then fills to 60 by the same deterministic
priority/hash order. Within periods, challenge cases, uncommon genres and newly
recovered primaries are prioritized. The blank human-review template is generated;
copy it before filling human labels so a rebuild does not replace your work.
