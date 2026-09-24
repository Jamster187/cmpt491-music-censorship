# LRCLIB production matcher: cached pilot safety check

This replay uses pure automatic rules, with no pilot-specific IDs or manual overrides. The approved reviews are comparison labels only. Zero LRCLIB requests.

Automatic usable: **154/200**; reviewed usable: **171/200**. False accepts relative to the reviewed exclusions: **0**.
Acceptance precision against reviewed labels: **100.0%**; usable recall: **90.06%**.
Exact disposition agreement: **182/200**; selected candidate changes: **21**; incompatible selected texts against reviewed sources: **0**.

Gate requires zero observed false accepts, no incompatible selected sources, and at least 145 automatic usable assets. This is a precision-first engineering check on the development pilot, not independent test-set evidence or a statistical guarantee. The 29 reviewed exclusions are a small negative set.

Candidate changes were inspected through metadata, word counts, sequence differences and short local text excerpts. Review found that a plural Remixes album label escaped the initial singular-only warning rule; plural detection was fixed and regression-tested before scaling. Final differences were limited transcription/formatting changes or compatible repetitions; no new obvious wrong-song/artist or materially defective acceptance was identified. Duration disagreements remain version uncertainty, not evidence of recording-level verification.

The production run carries forward all 171 approved usable pilot texts as reviewed decisions and preserves the other 29 reviewed dispositions. Automatic replay performance is reported separately; manual overrides do not inflate it.

## Disagreements

| Billboard title | Reviewed disposition | Automatic disposition | Reason |
|---|---|---|---|
| Where Are U Now | accepted | quarantined | Materially different plausible lyric texts |
| My True Story | accepted | quarantined | No full compatible title and artist credit |
| Spin That Wheel | accepted | quarantined | No full compatible title and artist credit |
| Midnight Train To Georgia | accepted | quarantined | Materially different plausible lyric texts |
| Gato de Noche | accepted | quarantined | Materially different plausible lyric texts |
| Steady Mobbin' | accepted | quarantined | All safe candidates conflict with available durations |
| Sitting Home | accepted | quarantined | Materially different plausible lyric texts |
| Sweet Thing | accepted | quarantined | Materially different plausible lyric texts |
| Use Your Heart | accepted | quarantined | Materially different plausible lyric texts |
| Family Man | accepted | quarantined | No full compatible title and artist credit |
| Like A Child | accepted | quarantined | Materially different plausible lyric texts |
| Whatever You Want | accepted | quarantined | Materially different plausible lyric texts |
| Wonderland | bad_missing_text | quarantined | Identity established; text or version requires review |
| Blue Magic | accepted | quarantined | Materially different plausible lyric texts |
| It Matters To Me | accepted | quarantined | Materially different plausible lyric texts |
| Contagious | accepted | quarantined | No full compatible title and artist credit |
| If It Wasn't For Bad Luck | accepted | quarantined | No full compatible title and artist credit |
| Say You'll Be Mine | accepted | quarantined | Materially different plausible lyric texts |
