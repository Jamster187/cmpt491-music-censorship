# CMPT 491 - Popular Music Content Analysis

We are studying popular music from 1958–2026: tracking lyrical content, comparing genres, and eventually testing unusual changes around/post COVID against historical trends. This would not establish causation.

## Billboard data and time resolution

Our [Billboard Hot 100 source](https://github.com/mhollingshead/billboard-hot-100) contains:

- 3,555 weekly charts
- 355,487 chart observations
- 32,723 unique title + artist combinations

**Weekly:** each chart is one snapshot. **Monthly:** we use the final available weekly chart in each calendar month. Both views use the same definition of popularity; monthly simply samples less frequently.

The final month-end population contains **28,041 songs, 818 snapshots and 81,797 song-month observations**. Three historical snapshots contain 99 songs because rank 100 is absent upstream. We preserve those gaps.

## Metadata and lyrics

MusicBrainz adds release dates, durations and album/release information, with **22,290 / 28,041** high-confidence matches.

We have confidently matched, usable lyrics for **20,981 / 28,041 songs**: **74.82%** overall, **81.33%** for 2015–2019 and **80.59%** for 2020–2026. Copyrighted lyrics remain local and are not distributed on GitHub.

## Four lyrical-content classifiers

Every song with usable lyrics is processed by four pretrained models, producing **42 numerical features**. Two songs lack LyricLens outputs because its preprocessing leaves their text empty; their other model results are preserved.

### LyricLens

Designed specifically for music lyrics, LyricLens supplies four scores: sexual content, violence, explicit language and substance use.

### Detoxify Unbiased

This toxicity/offensive-language model supplies seven scores: toxicity, severe toxicity, obscene language, threat, insult, identity attack and sexual explicitness. It was trained on online comments rather than lyrics, so that domain mismatch matters.

### GoEmotions

The GoEmotions-based RoBERTa model supplies 28 emotion-related scores, including anger, fear, joy, love, sadness, disgust, excitement, optimism, grief and surprise.

### Cardiff multilingual sentiment

CardiffNLP supplies negative, neutral and positive sentiment scores. Its multilingual support is useful because not every Billboard song is English.

These are model-derived features, not ground truth. We preserve individual outputs rather than combining them into an arbitrary “hardness” score. This lets us examine changes and relationships between measurements. Long lyrics are processed in chunks so the complete lyric is represented, not just its beginning.

## Genre classifier

Genre is separate from lyrical-content classification. Metadata-only assignment had weak coverage, so we validated an LLM approach. **Production genre classification and its final audit are complete: 28,041 / 28,041 songs.**

GPT-5.5 with medium reasoning uses a frozen structured prompt containing title, artist, first-chart-date context and available genre/tag evidence—not lyrical-content scores. Chart dates are not release dates.

Each song receives one primary genre from this fixed taxonomy:

Pop; Rock; Hip-Hop / Rap; R&B / Soul; Country; Latin; Electronic / Dance; Alternative / Indie; Metal; Folk / Singer-Songwriter; Jazz / Blues; Reggae / Dancehall; Gospel / Christian; K-Pop; Afrobeats / African Pop; Other.

We also preserve secondary genres and high/medium/low model confidence. These classifications are model-derived, not objective ground truth.

The [300-song pilot](reports/llm_genre_evaluation.md) assigned every song: 217 high, 65 medium and 18 low confidence. Agreement with strong existing genre evidence was 92.2%. Qualitative review found 117 plausible, 23 questionable and 3 clearly wrong assignments among 143 reviewed cases; this is not a formal accuracy estimate.

The [final genre audit](reports/genre_final_audit.md) records 18,621 high, 7,538 medium and 1,882 low-confidence assignments, with no unresolved errors. Its deterministic 160-song assistant review found 129 plausible, 29 questionable and 2 clearly wrong primary labels. Labels remain unchanged; this diagnostic review is not an accuracy estimate. Final master datasets are still pending.

## Downloads and next steps

The published [master_dataset.csv](https://raw.githubusercontent.com/Jamster187/cmpt491-music-censorship/main/data/public/master_dataset.csv) is an **earlier, temporary release using the old monthly aggregation**. Separate [songs.csv](data/public/songs.csv) and [monthly_top100.csv](data/public/monthly_top100.csv) belong to that release too.

After genre inference and validation, we plan to publish `master_weekly.csv` and `master_monthly.csv`. Both will include Billboard information, MusicBrainz metadata, primary genre, genre confidence and 42 lyrical-content features. Only time resolution differs: every weekly chart versus each month's final chart.

Once frozen, we plan to plot measurements, create moving averages, compare genres, examine feature relationships, establish pre-COVID trends and test unusual changes in levels or slopes around/post COVID.

## Status

- [x] Billboard data
- [x] Weekly/monthly end-of-period methodology
- [x] MusicBrainz metadata
- [x] Lyrics acquisition
- [x] Four-model lyrical classifier panel
- [x] Genre classification — complete and audited
- [ ] Final weekly/monthly master datasets
- [ ] Historical/genre/post-COVID analysis
