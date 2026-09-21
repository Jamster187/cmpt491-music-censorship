"""Independent public-release reconciliation and deterministic, text-free report."""
import csv
import hashlib
import io
import json
import math
import sqlite3
from collections import Counter
from pathlib import Path
from public_dataset import ROOT,PUBLIC,BASE_MASTER_COLUMNS,MASTER_COLUMNS,CLASSIFIER_COLUMNS,sha
from public_classifier_features import DATABASE,EXCEPTIONS

# Public acquisition-only master published before this authorized feature join.
ORIGINAL_MASTER_SHA256='4a18d97d4f117c4f6ce261ad4d035233e5401952b09dcd2e4e377bacf5a0df24'


def build():
    manifest=json.loads((PUBLIC/'manifest.json').read_text())
    for name,entry in manifest['files'].items():
        if sha(PUBLIC/name)!=entry['sha256'] or (PUBLIC/name).stat().st_size!=entry['bytes']:raise ValueError('Public manifest mismatch')
    if sha(DATABASE)!=manifest['classifier']['database_sha256']:raise ValueError('Classifier database changed')
    with sqlite3.connect(DATABASE.resolve().as_uri()+'?mode=ro',uri=True) as c:
        expected={r[0]:tuple(r[1:]) for r in c.execute('SELECT song_id,'+','.join(CLASSIFIER_COLUMNS)+' FROM song_results')}
    months=Counter();rows=Counter();songs={key:set() for key in ('any','all','partial','none')};keys=set();numeric=0
    legacy=hashlib.sha256();buf=io.StringIO(newline='');writer=csv.writer(buf,lineterminator='\n')
    def hash_original(values):
        buf.seek(0);buf.truncate(0);writer.writerow(values);legacy.update(buf.getvalue().encode('utf-8'))
    hash_original(BASE_MASTER_COLUMNS)
    with (PUBLIC/'master_dataset.csv').open(newline='',encoding='utf-8') as f:
        reader=csv.DictReader(f)
        if reader.fieldnames!=list(MASTER_COLUMNS):raise ValueError('Incorrect public columns')
        for row in reader:
            sid=row['song_id'];key=(row['month'],row['monthly_rank'])
            if key in keys:raise ValueError('Duplicate monthly row')
            keys.add(key);months[row['month']]+=1
            hash_original([row[col] for col in BASE_MASTER_COLUMNS])
            actual=tuple(None if row[col]=='' else float(row[col]) for col in CLASSIFIER_COLUMNS)
            if any(v is not None and (not math.isfinite(v) or not 0<=v<=1) for v in actual):raise ValueError('Invalid public score')
            if actual!=expected.get(sid,(None,)*42):raise ValueError('Classifier join/value mismatch')
            if (row['lyrics_available']=='1')!=(sid in expected):raise ValueError('Lyric availability mismatch')
            count=sum(v is not None for v in actual);numeric+=count
            if count:
                rows['any']+=1;songs['any'].add(sid)
            category='all' if count==42 else 'none' if count==0 else 'partial'
            rows[category]+=1;songs[category].add(sid)
            if category=='partial' and ((sid,'lyriclens') not in EXCEPTIONS or actual[:4]!=(None,)*4 or count!=38):raise ValueError('Undocumented public missingness')
    if legacy.hexdigest()!=ORIGINAL_MASTER_SHA256:raise ValueError('Original 31 columns/row order changed')
    if len(keys)!=81800 or len(months)!=818 or set(months.values())!={100}:raise ValueError('Monthly population changed')
    if set(expected)!=songs['any'] or len(expected)!=19372 or songs['partial']!={sid for sid,model in EXCEPTIONS}:raise ValueError('Song population mismatch')
    size=(PUBLIC/'master_dataset.csv').stat().st_size
    data={'version':manifest['version'],'rows':len(keys),'months':len(months),'rows_per_month':100,'columns':len(MASTER_COLUMNS),'classifier_columns':list(CLASSIFIER_COLUMNS),'bytes':size,
          'availability':{key:{'observations':rows[key],'songs':len(songs[key])} for key in songs},'populated_classifier_cells':numeric,
          'original_31_columns_sha256':legacy.hexdigest(),'master_sha256':sha(PUBLIC/'master_dataset.csv'),'classifier_database_sha256':manifest['classifier']['database_sha256'],
          'accepted_missingness':manifest['classifier']['accepted_missingness']}
    (ROOT/'reports/classifier_public_release.json').write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
    lines=['# Public classifier feature release','',
           '**COMPLETE with documented model-specific missingness.** The user accepted both LyricLens preprocessing failures. No retries, lyric edits or inference changes were made. Historical failure records stay intact in the private classifier database; the public exporter applies the explicit accepted-missingness policy.','',
           f'The master contains **{len(keys):,} song-month observations**, **818 months × 100 rows**, and **73 columns**: the original 31 followed by the 42 model features. File size: **{size:,} bytes ({size/2**20:.2f} MiB)**.','',
           '| Classifier availability | Monthly observations | Unique songs |','|---|---:|---:|']
    labels={'any':'Any classifier data','all':'All 42 features','partial':'Other 38 features; four LyricLens values missing','none':'All 42 features missing (no usable lyrics)'}
    for key,label in labels.items():lines.append(f"| {label} | {rows[key]:,} | {len(songs[key]):,} |")
    lines+=['','“Any classifier data” includes the complete and partial groups; it is not an additional disjoint group. Blank cells mean NULL/missing, not zero. All 2,737,342 populated feature cells are finite and within [0,1].','',
            'The two partial records are “Chinese Checkers” by Booker T. & The MG\'s and “Snap Shot” by Slave, each appearing in one monthly basket. Their reason is `unsupported/empty-after-LyricLens-normalization`. All valid Detoxify, GoEmotions and Cardiff features remain populated. See the [accepted-missingness policy](../docs/classifier_accepted_missingness.json).','',
            '## Validation','',
            '- The original 31-column projection serializes to exactly the pre-join SHA-256: `'+legacy.hexdigest()+'`. Every original value, row and row order is preserved.',
            '- Every public feature value independently reconciles to the correct private classifier row through `song_id`. No extra or missing study observations; no duplicate monthly keys.',
            '- The deterministic exporter validates the full approved 19,372-song population, frozen model configuration/checkpoint metadata, complete balanced chunks, raw activations and token-weighted aggregates. Only the two explicitly named errors may yield missing model scores.',
            '- Two independently generated exports must match byte-for-byte before publication. `validate` regenerates and compares all public files and manifest checksums.',
            '- Normalized songs/monthly tables are unchanged. Source research/classifier databases and lyrics are not modified or distributed. No raw text, token IDs, local paths, caches or credentials are projected.',
            '- The feature list is explicit and namespaced; no CSI, MCR, hardness, consensus or combined outcome is exported. No historical/COVID analysis was performed.','',
            '## Rebuild','',
            '```sh','python3 src/public_dataset.py build','python3 src/public_dataset.py validate','python3 src/public_classifier_report.py','python3 -m unittest discover -s tests -v','```','',
            'Rebuilding requires the retained local research and classifier databases. Downloads do not require these private inputs. The model-derived features are not ground-truth content measurements. Exact columns and source checksums are in [manifest.json](../data/public/manifest.json) and [the release evidence](classifier_public_release.json).','',
            'The reviewed master exceeds GitHub’s 50 MiB warning threshold but is below its 100 MiB hard limit. It is committed directly to retain the requested simple raw CSV download and full numerical precision; no LFS is introduced. [GitHub size limits](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github).']
    (ROOT/'reports/classifier_public_release.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({k:v for k,v in data.items() if k!='classifier_columns'},indent=2))

if __name__=='__main__':build()
