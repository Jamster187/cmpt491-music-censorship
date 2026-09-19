# Lyrics permission follow-up

Reviewed 2026-09-19 for this specific workflow: approximately 25,363 Billboard
assets, automated retrieval, private local full-text storage, classifier input,
and publication of numerical results only. No texts would go to GitHub or be
redistributed. **Acquisition remains blocked; the existing 200-song pilot was not
attempted.** This is an unresolved permission finding, not a conclusion that
private academic analysis is unlawful.

## Separate permission questions

“Permitted” below requires an affirmative source statement within its stated
scope. “Unclear” means no applicable affirmative permission was established;
it does not mean prohibited. Technical functionality alone is insufficient.

| Question | LRCLIB | Musixmatch | LyricFind | Genius / LyricsGenius |
|---|---|---|---|---|
| Technically accessible? | Public API; title/artist lookup and full texts documented | Official matching/lyrics API, account entitlement required | Licensed lyric delivery/search products | Metadata API; wrapper retrieves full text from webpages |
| Automated API retrieval permitted? | Yes, service explicitly offers machine-readable API [L1] | Yes for authorized API clients under applicable terms [M1]; no project entitlement | Available through licensing; no project agreement [F1] | Metadata access does not establish a full-text API grant [G1] |
| Bulk retrieval at ~25,363? | Mass downloading explicitly supported for offline music libraries [L2]; this corpus/request volume not expressly addressed | Unclear without agreed quota and full-text scope | Unclear without agreed delivery scope/quota | No verified grant for this workflow |
| Local storage/caching? | Explicitly supported for offline music-library downloads [L2]; research-corpus scope still unclear | Unclear; applicable API/storage terms not verified | Unclear without agreement; website reproduction is prohibited unless otherwise stated [F2] | Unclear; no applicable corpus-retention permission established |
| Academic computational analysis? | Unclear; no explicit research/mining grant found | Unclear; display API documentation is not a research license | Research arrangement is demonstrably possible [F3], but no permission for this project | Unclear; wrapper reports that its scraping violates provider terms [G1] |
| Derived numerical features/results? | Unclear; no applicable statement about computing/publishing them | Unclear without agreement | Prior licensed research published derived measures [F3]; permission does not transfer to us | Unclear; no applicable grant found |
| Required attribution? | Identifying client header required [L1]; no verified content/research attribution policy found | Exact research attribution and any copyright/link/tracking requirements must be confirmed in applicable terms | Contract-specific; research precedent requests a paper citation [F3] | No established attribution rule that would authorize this corpus |
| Rate limits / etiquette? | Identified client, obey HTTP 429 and Retry-After; no fixed numerical quota verified [L1] | API key required; account quota not verified | Partner API credentials, quota and delivery schedule need agreement | Metadata token/API limits do not authorize full-text scraping |

## What the deeper LRCLIB review adds

The maintainer responded to a question about commercial API use with “It's
generally OK” and requested an identifying client header [L3]. This is affirmative
service-use evidence, not merely silence about restrictions. Combined with
LRCGET, it supports API automation and saving downloads locally. It does **not**
expressly cover computational research, publication of derived features, or the
underlying lyrics rights for a 25,363-asset corpus. This last distinction is our
assessment of the scope of the evidence, not a claim that LRCLIB prohibits research.

The homepage links database dumps [L4], another indication of intended bulk
technical access. The dump page did not expose usable terms to the research tools;
no dump was downloaded and no content license was inferred from that link.
The repository's MIT license covers its software [L5]. It is not treated as an
express license to all lyrics obtained through the service. The legal-documentation
pull request remains open [L6], so proposed text is not adopted policy. The later
commercial-use issue asks about caching and rights but supplies no answer we can
rely on [L7]. Neither a forum user's question nor a third-party wrapper grants rights.

The API documentation was accessible through its search-indexed primary-source
text; direct requests returned an unrendered page or failed. It requires an
application name/version and project URL or contact address in the identifying
header and handling of 429/Retry-After. The prior assessment's 200–500 ms pacing
figure is **not treated here as a verified numerical quota or authorization for
bulk retrieval**. Any eventual client should use conservative sequential pacing,
cache completed responses, and honor the current provider instructions.

Private storage and numerical-only publication narrow our request substantially.
They do not, by themselves, resolve a missing source-use grant. We will not equate
non-public use with automatic permission or make an unsupported fair-dealing
legal determination.

## Other realistic routes

Musixmatch's official SDK establishes licensed automated matching and lyric
retrieval, API-key authentication, and the requirement to read its API terms [M1].
Those linked terms were inaccessible in this review. Therefore no current free-tier
quota, full-text entitlement, caching duration, or research-use permission is
asserted. A project-specific academic entitlement remains a possible route.

LyricFind is the clearest documented research-contact route. Its partnership with
NUS supplied a full corpus through a special arrangement; the researchers
published numerical lexical-novelty measures and released bag-of-words data [F3].
Its LyricIQ product also demonstrates licensed computational analysis as a product
[F4], but neither fact authorizes us to download full lyrics or substitutes its
features for our future classifier. The old NUS bag-of-words release cannot supply
ordered lyrics or establish 2020–2026 coverage. The current partner contact form
is preferable to relying on a person's contact details from 2015 [F5].

Genius is not a workaround. LyricsGenius explicitly distinguishes its API metadata
from its web scraping and says the latter violates Genius terms [G1]. Direct Genius
terms/docs were inaccessible here; we do not claim to have independently verified
the current legal wording. No scraper, bypass, or full-text request was used.
No additional source reviewed supplied a verified grant and suitable modern
Billboard full-text coverage.

## Concrete way to resolve the blocker

The next evidence needed is a provider response/agreement covering this precise
scope, or an institutionally approved legal basis addressing both retrieval terms
and content use. No provider has been contacted on the user's behalf. This draft
is ready to send to LRCLIB's published maintainer contact [L5] or LyricFind's partner
contact [F5]:

> We are conducting a CMPT 491 university project using approximately 25,363
> Billboard song title/artist identities. May we retrieve their full lyrics
> automatically and retain them privately on a local machine for computational
> classification? We would publish numerical features and aggregate research
> results, never the lyric text or a redistributable corpus. Please confirm whether
> your terms and content permissions cover this use, including publication of
> derived features; the permitted request volume/rate or bulk-delivery option;
> retention/deletion requirements; and required attribution. We would begin with
> a 200-song pilot. Please identify any separate rightsholder permission needed.

This request does not assume cloud classifier processing is allowed. If the later
classifier sends text to a third party, that use needs separate explicit treatment.

## Pilot and workload

Existing pilot: 200 frozen study identities, unchanged. Attempts/retrievals/errors:
**0/0/0**; matching quality, historical coverage, and especially 2010–2019 and
2020–2026 provider coverage are **unmeasured**. No full acquisition started.

For planning only, one title/artist search per asset would mean 200 pilot requests
and 25,363 full-population requests. At a hypothetical one-request-per-second
schedule, the latter has a 7.05-hour pacing floor, before latency, extra candidate
lookups or retries. This is arithmetic, not a verified LRCLIB allowance or measured
runtime. Use the actual permitted rate and pilot measurements before bulk work.

## Evidence

- **L1:** [LRCLIB API documentation](https://lrclib.net/docs).
- **L2:** [Official LRCGET README](https://github.com/tranxuanthang/lrcget): mass downloads saved beside local music files.
- **L3:** [Maintainer's July 22, 2025 response](https://github.com/tranxuanthang/lrclib/discussions/53). The discussion identifies the author and date.
- **L4:** [LRCLIB homepage](https://www.lrclib.net/) links [database dumps](https://lrclib.net/db-dumps).
- **L5:** [LRCLIB repository and contact](https://github.com/tranxuanthang/lrclib), inspected main commit `05ad8590f6fc4d47a2d74e70f4915273df20f63c`; [MIT software license](https://github.com/tranxuanthang/lrclib/blob/05ad8590f6fc4d47a2d74e70f4915273df20f63c/LICENSE).
- **L6:** [Open legal-documentation proposal #74](https://github.com/tranxuanthang/lrclib/pull/74), not adopted policy.
- **L7:** [Commercial-use/caching question #111](https://github.com/tranxuanthang/lrclib/issues/111).
- **M1:** [Official Musixmatch SDK](https://github.com/musixmatch/musixmatch-sdk/blob/master/README.md), including its API-terms link (unavailable in this review).
- **F1:** [LyricFind licensing/products](https://www.lyricfind.com/).
- **F2:** [LyricFind website terms](https://www.lyricfind.com/terms-and-conditions), separate from a negotiated API/research agreement.
- **F3:** [NUS/LyricFind research corpus](https://smcnus.org/lyrics/) and [original research paper, section 3.2](https://smcnus.org/wp-content/uploads/2015/08/LNS_ISMIR2015_116.pdf).
- **F4:** [LyricIQ product](https://www.lyricfind.com/products/lyriciq).
- **F5:** [Current LyricFind contact page](https://www.lyricfind.com/contact).
- **G1:** [LyricsGenius implementation documentation](https://lyricsgenius.readthedocs.io/en/master/how_it_works.html).
