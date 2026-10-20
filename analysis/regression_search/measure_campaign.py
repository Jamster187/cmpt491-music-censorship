"""Measure an authorized command without changing the frozen search implementation."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/"src"))
import regression_search as run
import regression_spec as spec
from regression_store import write_json

FROZEN = "426fdf199ea5bbc170f2b6089d4ba4d1b51b1245"
CAMPAIGN = run.LOCAL/"campaign"


def verify_frozen():
    for name in run.CODE:
        expected = hashlib.sha256(subprocess.check_output(["git", "show", FROZEN+":"+name], cwd=ROOT)).hexdigest()
        if spec.original.sha(ROOT/name) != expected:
            raise ValueError("Frozen campaign implementation changed: "+name)
    saved = json.loads((run.PUBLIC/"specification/search_totals.json").read_text())
    for name, expected in saved["current_data_hashes"].items():
        if spec.original.sha(ROOT/name) != expected:
            raise ValueError("Approved dataset changed: "+name)
    plans = [t for t in spec.specs() if t["model_family"] == "regression"]
    if len(plans) != 59 or sum(spec.count(t,k) for t in plans for k in (1,2,3)) != 1998901:
        raise ValueError("Approved numerical search universe changed")
    return dict(frozen_implementation_commit=FROZEN, provenance=run.provenance(),
                input_sha256=saved["current_data_hashes"], configuration=spec.configuration())


def protected_files():
    names = subprocess.check_output(["git", "ls-files", "-z", "data", "analysis/milestone2",
        "analysis/moving_averages", "analysis/figure_manifest.json", "analysis/figure_audit.csv",
        "analysis/figure_audit.md"], cwd=ROOT).decode().split("\0")
    return {name: spec.original.sha(ROOT/name) for name in names if name}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["search", "finalize", "resume_probe"])
    args = parser.parse_args()
    before = verify_frozen()
    execution = CAMPAIGN/"execution"
    execution.mkdir(parents=True, exist_ok=True)
    baseline = execution/"protected_before.json"
    current = protected_files()
    if baseline.exists():
        if json.loads(baseline.read_text()) != current:
            raise ValueError("Protected data or existing analyses changed since campaign start")
    else:
        write_json(baseline, current)
    if args.phase == "finalize":
        command = [sys.executable, "src/regression_search.py", "finalize", "--evaluate-final-test"]
    else:
        command = [sys.executable, "src/regression_search.py", "campaign", "--execute-full", "--workers", "1"]
    attempt = len(list(execution.glob(args.phase+"_*.json"))) + 1
    output = execution/f"{args.phase}_{attempt:02d}.json"
    log = output.with_suffix(".log")
    record = dict(phase=args.phase, command=command, before=before,
                  started_utc=datetime.now(timezone.utc).isoformat(), status="running")
    write_json(output, record)
    started = time.perf_counter()
    usage_before = resource.getrusage(resource.RUSAGE_CHILDREN)
    with log.open("w") as stream:
        completed = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT)
    elapsed = time.perf_counter()-started
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    record.update(status="complete" if completed.returncode == 0 else "interrupted_or_failed",
        returncode=completed.returncode, finished_utc=datetime.now(timezone.utc).isoformat(),
        elapsed_seconds=elapsed,
        child_peak_rss_bytes=int(usage.ru_maxrss if platform.system()=="Darwin" else usage.ru_maxrss*1024),
        user_cpu_seconds=usage.ru_utime-usage_before.ru_utime,
        system_cpu_seconds=usage.ru_stime-usage_before.ru_stime,
        log_sha256=spec.original.sha(log), after=verify_frozen(),
        protected_files_unchanged=(protected_files() == current))
    write_json(output, record)
    print(json.dumps({k:record[k] for k in ["phase","status","returncode","elapsed_seconds",
        "child_peak_rss_bytes","protected_files_unchanged"]}, indent=2), flush=True)
    if not record["protected_files_unchanged"]:
        raise ValueError("Protected data or analyses changed")
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
