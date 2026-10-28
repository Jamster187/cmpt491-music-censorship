"""Fetch only the pinned, licensed dictionary/model assets used by this campaign."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from enrichment_common import LOCAL, MUSIC, fetch, sha, write_json

CMU_REVISION='74790861f652b15e4ac49015a90074ad62a27690'
MODEL_REVISION='1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
MODEL_FILES=['config.json','model.safetensors','tokenizer_config.json','special_tokens_map.json',
             'tokenizer.json','vocab.txt','sentence_bert_config.json','README.md']


def assets(download=False):
    manifest_path=MUSIC/'asset_manifest.json'
    previous=json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    rows=[]
    for name in ['cmudict.dict','LICENSE']:
        local_name='cmudict.LICENSE' if name=='LICENSE' else name
        path=LOCAL/'sources'/local_name
        url=f'https://raw.githubusercontent.com/cmusphinx/cmudict/{CMU_REVISION}/{name}'
        if download and not path.exists():fetch(url,path)
        if not path.exists():raise FileNotFoundError(path)
        rows.append({'path':str(path.relative_to(LOCAL)),'source_url':url,'sha256':sha(path),
                     'license':'CMUdict BSD-style license; see retained LICENSE','version':CMU_REVISION})
    directory=LOCAL/'models/all-MiniLM-L6-v2'
    if download and any(not (directory/f).exists() for f in MODEL_FILES):
        from huggingface_hub import snapshot_download
        snapshot_download('sentence-transformers/all-MiniLM-L6-v2',revision=MODEL_REVISION,
                          local_dir=directory,allow_patterns=MODEL_FILES)
    for name in MODEL_FILES:
        path=directory/name
        if not path.exists():raise FileNotFoundError(path)
        rows.append({'path':str(path.relative_to(LOCAL)),'source_url':f'https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2/resolve/{MODEL_REVISION}/{name}',
                     'sha256':sha(path),'license':'Apache-2.0; model card retained','version':MODEL_REVISION})
    result={'assets':rows,'spacy_model':'en_core_web_sm==3.8.0','spacy_model_license':'MIT',
        'spacy_model_url':'https://github.com/explosion/spacy-models/releases/tag/en_core_web_sm-3.8.0',
        'wordfreq_version':'3.1.1','wordfreq_source':'https://github.com/rspeer/wordfreq','wordfreq_license':'Apache-2.0 software; included data may be CC BY-SA 4.0, preserve source attribution',
        'retrieval_campaign_date':'2026-10-28','source_bytes_pinned':True}
    if previous and result!=previous:raise ValueError('Pinned research asset differs; create a new version')
    write_json(manifest_path,result);print('Pinned assets verified:',len(rows),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--download',action='store_true');a=p.parse_args();assets(a.download)
