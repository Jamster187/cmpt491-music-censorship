# Refined genre pilot

Only the original 300 identities are evaluated. `pilot.csv` holds candidate v2
assignments; `ambiguity_audit.csv` accounts for all 150 v1 ambiguous identities.
`summary.json` contains transitions, estimates and input hashes. Raw evidence and
complete per-category support records remain in ignored local experiment files.

`review.csv` contains an **assistant qualitative metadata review**, not independently
collected human labels. Its 60 cases prioritize challenge identities, uncommon
genres and recovered assignments within each period. A blank human review sheet
is supplied separately. Review references are diagnostic only; they are never
read by the assignment engine or used as new production evidence.

The 47 cases marked cross-genre evidence have multiple strong non-parent candidate
categories, not independently proven musical ground truth. Nineteen have a dominant
primary; 28 remain tied. The other 103 have weak support or generic-parent/noise
issues. Multiple compatible tags occur in 127 cases but never explain v1 ambiguity
by themselves, because v1 already combined tags into broad-category sets.

As with the first pilot, MusicBrainz contributors are credited for supplementary
annotation data and these derived pilot data are provided under
[CC BY-NC-SA 3.0](https://creativecommons.org/licenses/by-nc-sa/3.0/).
Wikidata structured data is CC0. These are experimental genre outputs, not a new
public master release. No lyrics or classifier scores are included.
