"""Read-only validation of the financial research publication; stdlib only."""
from __future__ import annotations

import collections
import csv
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(name: str) -> list[dict[str, str]]:
    with (HERE / name).open(newline='', encoding='utf-8') as stream:
        rows = list(csv.DictReader(stream))
    assert rows, f'Empty inventory: {name}'
    assert all(None not in r and None not in r.values() for r in rows), name
    return rows


def unique(rows: list[dict[str, str]], key: str) -> set[str]:
    values = [r[key] for r in rows]
    assert len(set(values)) == len(values), f'Duplicate {key}'
    assert all(values), key
    return set(values)


def main() -> None:
    manifest = json.loads((HERE / 'publication_manifest.json').read_text())
    actual_files = {p.name for p in HERE.iterdir() if p.is_file()}
    assert actual_files == set(manifest['files']) | {'publication_manifest.json'}, 'File catalog mismatch'
    for name, expected in manifest['files'].items():
        assert digest(HERE / name) == expected, f'Changed publication: {name}'
    for name, expected in manifest['protected_baseline_sha256'].items():
        assert digest(ROOT / name) == expected, f'Changed protected baseline: {name}'

    inputs = read('indicator_inventory.csv')
    sources = read('source_inventory.csv')
    derived = read('derived_indicators.csv')
    coverage = read('historical_coverage.csv')
    feasibility = read('feasibility_matrix.csv')
    checks = read('source_checks.csv')
    local = read('existing_local_series.csv')
    counts = json.loads((HERE / 'counts.json').read_text())
    ids = unique(inputs, 'indicator_id')
    cols = unique(inputs, 'proposed_column_name')
    source_ids = unique(sources, 'source_id')
    unique(derived, 'derived_id')
    unique(derived, 'proposed_column_name')
    assert unique(coverage, 'indicator_id') == ids
    assert unique(feasibility, 'indicator_id') == ids
    assert {r['source_id'] for r in inputs} <= source_ids
    assert all(re.fullmatch(r'[a-z][a-z0-9_]*', c) for c in cols)
    required = {'indicator_name', 'description', 'category', 'units', 'frequency',
                'geography', 'historical_start', 'historical_end', 'source_provider',
                'exact_source_url', 'dataset_or_series_identifier', 'acquisition_method',
                'api_requirements', 'cost', 'licensing', 'redistribution_restrictions',
                'missingness', 'revision_vintage_availability', 'publication_lag',
                'recommended_transformations', 'redundancy_group',
                'suitability_for_music_comparison', 'verification_status'}
    for row in inputs:
        assert required <= row.keys()
        assert all(row[k].strip() for k in required), row['indicator_id']
        assert urlparse(row['exact_source_url']).scheme in {'https', 'http'}
        assert row['historical_completeness_verified'] == 'NO'
    for row in derived:
        assert set(row['source_dependencies'].split(';')) <= cols, row['derived_id']
        assert row['computed'] == 'NO'
        assert row['independent_underlying_source'] == 'NO'
    assert all(r['observation_values_saved'] == 'NO' for r in checks)
    assert all(r['full_1958_2026_observation_completeness'] == 'UNVERIFIED' for r in coverage)
    for row in feasibility:
        for field, value in row.items():
            if field.endswith('_rank'):
                assert value == 'UNRANKED' or int(value) > 0
    ranked = sorted(int(r['overall_recommended_rank']) for r in feasibility if r['overall_recommended_rank'] != 'UNRANKED')
    assert ranked == list(range(1, 26))
    calc = dict(raw_candidate_rows=len(inputs),
                underlying_redundancy_groups=len({r['redundancy_group'] for r in inputs}),
                derived_definition_rows=len(derived),
                derived_non_alias_families=sum(r['definition_status'] != 'ALIAS_ONLY' for r in derived),
                source_records=len(sources),
                live_primary_documentation_verified_sources=sum(s['live_documentation_status'] == 'PRIMARY_PAGE_READ' for s in sources),
                primary_indexed_sources=sum(s['verification_status'].startswith('PRIMARY_INDEXED') for s in sources),
                reported_starts_reaching_1958=sum(r['coverage_class'] == 'REPORTED_START_REACHES_1958' for r in coverage),
                reported_partial_histories=sum(r['coverage_class'] == 'REPORTED_PARTIAL_HISTORY' for r in coverage),
                unknown_starts=sum(r['coverage_class'] == 'START_UNKNOWN' for r in coverage),
                full_history_completeness_verified=0,
                cost_classes=dict(collections.Counter(r['cost'] for r in inputs)),
                category_counts=dict(collections.Counter(r['category'] for r in inputs)),
                existing_local_series_reviewed=len(local),
                documentation_checks=len(checks),
                live_primary_page_checks=sum(r['verification_status'] == 'PRIMARY_PAGE_READ' for r in checks))
    assert calc == counts, 'Inventory/count mismatch'
    assert len(cols) == counts['reported_starts_reaching_1958'] + counts['reported_partial_histories'] + counts['unknown_starts']
    local_links = 0
    for doc in HERE.glob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)', doc.read_text()):
            if urlparse(target).scheme or target.startswith('#'):
                continue
            target = unquote(target.split('#', 1)[0])
            assert (doc.parent / target).exists(), f'Broken link: {doc.name}: {target}'
            local_links += 1
    print(json.dumps({'status': 'PASS', 'publication_files_hashed': len(manifest['files']),
                      'protected_baselines_unchanged': len(manifest['protected_baseline_sha256']),
                      'candidate_inputs': len(inputs), 'source_records': len(sources),
                      'derived_rows': len(derived), 'top_recommendations': len(ranked),
                      'local_markdown_links_checked': local_links,
                      'source_observations_inventoried_or_downloaded_by_this_script': 0}, indent=2))


if __name__ == '__main__':
    main()
