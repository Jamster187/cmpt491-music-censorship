## What the disagreements show

All seven disagreements with the refined strong primary rule were inspected:
Elvis's *Can't Help Falling in Love* (Rock → Pop), Mel Carter's *Hold Me, Thrill
Me, Kiss Me* (Soul → Pop), England Dan & John Ford Coley's *What Can I Do With
This Broken Heart* (Rock → Pop), Chaka Khan's *I Feel for You* (Pop → Soul),
Ricky Martin's *Livin' La Vida Loca* (Pop → Latin), Marshmello/CHVRCHES's *Here
With Me* (Pop → Dance), and Olivia Rodrigo's *Good 4 U* (Pop → Rock). The first
three are defensible broad-boundary choices; the others make useful style-specific
corrections. [Chaka Khan's R&B Grammy recognition](https://www.grammy.com/video/27th-annual-grammy-awards-best-rb-vocal-performance-female/)
is external review support, not new classifier input.

The LLM also recovers Silk's *Hooked on You*, YNW Melly's *Murder on My Mind*,
Childish Gambino's *Redbone*, and Wizkid's *Essence* without blindly following
isolated Pop, Rap or Dance tags. These were known failure cases from previous
reviews, not newly selected input examples inserted into the prompt.

Two clear errors were low-confidence Other assignments for *Baby Face*
(Wing and a Prayer) and *Black Kisses Never Make You Blue* (Curtie & the Boom Box).
A [contemporary disco review](https://jameshamiltonsdiscopage.com/1975/12/13/december-13-1975/)
establishes the former recording's dance context; a
[recording-specific discography](https://www.allbutforgottenoldies.net/bands-and-artists/info.php?id=curtie-and-the-boombox)
describes the latter's techno-pop sound. Other here is failed recognition rather
than a genuine musical category. The third clear primary error was Sweet Sensation’s *Sincerely Yours*, assigned
R&B/Soul at medium confidence rather than its defining
[freestyle dance identity](https://freestylemusic.org/sincerely-yours-sweet-sensation/).
All labels remain unchanged.

The paired A review was 68 plausible / 7 questionable / 2 clearly wrong, compared
with B's 71 / 6 / 0. All 77 paired cases were reviewed. Do not conclude that tags
improved quality: four of eight primary disagreements had no tags at all. The
empty evidence key and different batch composition can also condition output.
The 30/30 exact and 41/42 rebatching repeats show substantial stability for those
particular samples, not invariance to every prompt change. Steelheart’s *I’ll Never
Let You Go* changed between Rock and Metal under rebatching.

Soul/country (*I Can't Stop Loving You*) and Latin/jazz (*Viva Tirado*) are
legitimate crossover differences. Both final arms agree on Rap for *911*, while
its Soul secondary preserves a real crossover. *Hangover* exposes K-pop scene
versus EDM/hip-hop style: [contemporary reporting](https://www.koreajoongangdaily.com/korea/psy-and-snoop-dog-are-hungover/10083574)
recognizes its hip-hop character. *Geronimo* supports both pop and indie-pop;
the [band's own description](https://wearesheppard.com/pages/about-us) uses Pop.
These are not automatically misclassifications.

High confidence sometimes overstates a difficult boundary: generic Rock for
Linkin Park's *In the End* and Pop for Drake's *One Dance*. *Hangover* is medium
confidence in the final screened-input run.
*One Dance* has [specific dancehall/Afropop/UK-funky influences](https://pitchfork.com/reviews/tracks/18160-drake-one-dance-ft-wizkid-and-kyla/).
The unfamiliar *Sugar on My Tongue* illustrates an artist-based Rap fallback
that underrepresents [its dance/electro-funk direction](https://www.revolt.tv/article/tyler-the-creator-drops-provocative-sugar-on-my-tongue-video).
Its low confidence is useful, but does not repair the label.

Secondary genres are less defensible than the primary counts suggest. For example,
Dance on Debbie Gibson's ballad *Lost in Your Eyes*, Rock on *My Heart Will Go On*,
and Dance on *Feels So Good* are weakly justified. These fields should remain
provisional model suggestions, not independently validated song-level memberships.
The 143-case counts assess primary assignments; notes explicitly flag some
secondary problems, but no exhaustive secondary-label accuracy claim is made.

Older unfamiliar recordings and very recent titles carry more uncertainty than
familiar catalog tracks. Genre-specific styles versus market/scene categories
(K-pop, Latin, African Pop, Christian) remain an interpretive limitation of the
frozen taxonomy. No taxonomy values were changed. These diagnostics cannot
establish time-invariant error rates or unbiased future genre trajectories.

## Recommendation: A — ready for full LLM primary-genre classification

The main objective is a broad, model-derived **primary** feature. The pilot offers
substantially more usable judgments than 90 tag-only primaries, with strong tag
agreement and low observed clearly-wrong counts, while exposing uncertainty.
This supports a production pass with the current method; it does not validate
all secondary labels or make the results objective truth. Team review of the
provided template would strengthen validation, particularly for obscure songs.

Freeze the existing prompt/schema unchanged, requested `gpt-5.5` model and CLI
0.155.1, medium reasoning, ten-song batches, input-screen version 2 excluding performance/outcome tags,
exact identity/first chart date plus positive raw genre evidence grouped by provider/level/label, maximum support and
entity count. Keep recording/release/artist levels separate when scaling; no
previous assignments, chart-performance values, lyrics or content scores enter
inputs. Preserve raw responses, input/prompt/model/interface versions and all
confidence/reason fields. Do not silently promote low-confidence Other into a
known style. Keep secondary labels explicitly provisional. The model alias is a
recorded reproducibility limitation, not a pinned checkpoint guarantee.

Production engineering should freeze all 28,041 inputs and batch membership before
requests, use an incremental per-song/batch result store, skip completed work,
record failures separately, and respect account quotas. This pilot deliberately
provides no full-population runner. Moving to a pinned API snapshot or another
interface requires a small equivalence replay before adopting that configuration.
No production run has started and no public dataset has changed.
