"""Read-only cleanup checks: immutable artifacts, navigation, paths and Git hygiene."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'docs/repository_cleanup_manifest.json'
HISTORICAL_MARKDOWN={'archive/old_methodology/repository_readme_before_cleanup.md',
                     'data/public/legacy_classifier_v2/README.md'}
OPTIONAL_PLAIN={'analysis/moving_averages/data/monthly_classifier_overall.csv',
                'analysis/moving_averages/data/monthly_classifier_by_genre.csv'}


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):
            digest.update(block)
    return digest.hexdigest()


def markdown_files():
    result=[ROOT/'README.md',ROOT/'AGENTS.md']
    for name in ['analysis','archive','docs','reports','src','data/public']:
        result.extend((ROOT/name).rglob('*.md'))
    return [p for p in result if str(p.relative_to(ROOT)) not in HISTORICAL_MARKDOWN]


def broken_links():
    failures=[];count=0
    for path in markdown_files():
        for target in re.findall(r'\]\(([^)\s]+)\)',path.read_text()):
            if re.match(r'[a-z]+://|#|mailto:',target):
                continue
            count+=1
            if not (path.parent/target.split('#')[0]).exists():
                failures.append((str(path.relative_to(ROOT)),target))
    return failures,count


def stale_paths(manifest):
    aliases=manifest.get('compatibility_aliases',{})
    old=[p for p in set(manifest['moves']) | set(manifest['directory_moves'])
         if '/' in p and not any(p==a or p.startswith(a+'/') for a in aliases)]
    pattern=re.compile(r'(?<![\w/])(?:'+ '|'.join(re.escape(p) for p in sorted(old,key=len,reverse=True))+r')(?=[/\s`\x27\x22)#]|$)')
    failures=[]
    for path in list((ROOT/'src').glob('*.py'))+list((ROOT/'tests').glob('*.py'))+markdown_files():
        for match in pattern.finditer(path.read_text()):
            failures.append((str(path.relative_to(ROOT)),match.group()))
    return failures


def validate():
    manifest=json.loads(MANIFEST.read_text());checked=0
    for name,expected in manifest['immutable_artifact_sha256'].items():
        p=ROOT/name
        if name in OPTIONAL_PLAIN and not p.exists():
            continue
        if not p.exists() or sha(p)!=expected:
            raise ValueError('Immutable data/result changed: '+name)
        checked+=1
    release=json.loads((ROOT/'data/public/manifest.json').read_text())
    for name,digest in dict(release['pipeline_sha256'],**release['genre']['frozen_files']).items():
        if sha(ROOT/name)!=digest:
            raise ValueError('Frozen release implementation changed: '+name)
    links,n=broken_links()
    if links:raise ValueError('Broken Markdown links: '+repr(links))
    stale=stale_paths(manifest)
    if stale:raise ValueError('Stale active paths: '+repr(stale))
    tracked=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    private_prefixes=('data/lyrics/','data/processed/','data/cache/','data/experiments/','.venv/')
    private_suffixes=('.db','.sqlite','.sqlite3','.safetensors','.ckpt','.pt','.pth','.log','.pem','.key')
    bad=[p for p in tracked if p.startswith(private_prefixes) or p.endswith(private_suffixes)
         or Path(p).name=='.env']
    if bad:raise ValueError('Private files tracked: '+repr(bad))
    for p in ['data/lyrics/probe.txt','data/processed/probe.db','data/cache/probe.json',
              'data/experiments/probe.bin','.venv/probe','archive/probe.db','archive/.env']+sorted(OPTIONAL_PLAIN):
        if subprocess.run(['git','check-ignore','--quiet',p],cwd=ROOT).returncode:
            raise ValueError('Private/generated path no longer ignored: '+p)
    for alias,target in manifest.get('compatibility_aliases',{}).items():
        p=ROOT/alias
        if not p.is_symlink() or p.resolve()!=(ROOT/target).resolve():
            raise ValueError('Frozen compatibility alias changed: '+alias)
    return dict(immutable_artifacts_checked=checked,local_markdown_links_checked=n,
                stale_active_paths=0,private_tracked_files=0,frozen_release_hashes='PASS')


if __name__=='__main__':
    print(json.dumps(validate(),sort_keys=True,indent=2))
