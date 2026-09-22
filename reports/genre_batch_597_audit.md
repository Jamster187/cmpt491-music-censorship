# Genre batch 597: identity audit

Attempt 569; finished 2026-09-22T04:06:15.036082+00:00. Expected 10 IDs; returned 10 rows.
Missing: 1. Foreign: 1. Duplicate IDs: 0.

## Expected IDs

| Title | Artist | Exact expected song_id | Exact unique ID returned |
|---|---|---|---|
| Electric Relaxation (Relax Yourself Girl) | A Tribe Called Quest | `song_abf0f0abf5c49f849392d260f605c237ed7500d7eab05d90c5fa2dd46cb69b5e` | True |
| Lost | Linkin Park | `song_2fec851cae8f3dbb2e79b071c934723eef98099b61aa1a99a80b5723734f5d24` | True |
| (I Know) I'm Losing You | Uptown | `song_90368f5ae8b23eed403131c3fefc07a15eedf4a23995f362794fee3bd9cc5aff` | True |
| Attack Of The Name Game | Stacy Lattisaw | `song_de8b47ce7d89e72a8b6688ecbd6228de40422a23d7343ae81a1f14b544ea42fd` | True |
| Forever In Blue Jeans | Neil Diamond | `song_db119d6d7e63fa4f2ecd1af07fb65400e53b3c8193a458d8bd8ec5e7ed5e3c81` | True |
| Shadows Of The Night | Pat Benatar | `song_0a847fb8c809f874214337e585894d9797deacc261338f5eac2b7d0f9d42c3c9` | True |
| Love Me For A Reason | The Osmonds | `song_187e9fd579a533f661c98fe0649c8e2c0f08f2061071d9a1b806fc127af60250` | True |
| Whatchulookinat | Whitney Houston | `song_c9456565f255ede1f5cb53cb24a506c466b003b7fceca7627cc951f3b78aadae` | True |
| Gypsy Queen - Part 1 | Gypsy | `song_3849d45b7d059d6b2db130a7f6200e710931b39af2e6b26540d0f678011720de` | False |
| All Of The Girls You Loved Before | Taylor Swift | `song_fcf16a3b0c3f553a541f461e60ec45019acb2ebcad74c11a1b730f2b85538638` | True |

## Returned IDs (response order)

- `song_abf0f0abf5c49f849392d260f605c237ed7500d7eab05d90c5fa2dd46cb69b5e`
- `song_2fec851cae8f3dbb2e79b071c934723eef98099b61aa1a99a80b5723734f5d24`
- `song_90368f5ae8b23eed403131c3fefc07a15eedf4a23995f362794fee3bd9cc5aff`
- `song_de8b47ce7d89e72a8b6688ecbd6228de40422a23d7343ae81a1f14b544ea42fd`
- `song_db119d6d7e63fa4f2ecd1af07fb65400e53b3c8193a458d8bd8ec5e7ed5e3c81`
- `song_0a847fb8c809f874214337e585894d9797deacc261338f5eac2b7d0f9d42c3c9`
- `song_187e9fd579a533f661c98fe0649c8e2c0f08f2061071d9a1b806fc127af60250`
- `song_c9456565f255ede1f5cb53cb24a506c466b003b7fceca7627cc951f3b78aadae`
- `song_3849d45b7d059d6b2db130a7f62000e710931b39af2e6b26540d0f678011720de`
- `song_fcf16a3b0c3f553a541f461e60ec45019acb2ebcad74c11a1b730f2b85538638`

## Missing IDs

- `song_3849d45b7d059d6b2db130a7f6200e710931b39af2e6b26540d0f678011720de`

## Foreign IDs

- `song_3849d45b7d059d6b2db130a7f62000e710931b39af2e6b26540d0f678011720de`

## Duplicate IDs

None.

## Decision

Only schema-valid predictions carrying exact, unique requested IDs may be retained. A foreign ID is not repaired or mapped by response position, even when its text appears to describe an input song. Genre plausibility and exact identity reconciliation are separate questions.

For batch 597, nine rows match exact requested IDs and their reasons refer to the corresponding input artists or evidence. The remaining row contains an extra zero in the ID associated with Gypsy’s “Gypsy Queen - Part 1”; its label is not attached to that song. That unresolved input requires a new exact-ID response.

Rebuild: `python3 src/genre_batch_audit.py 597 569`.
