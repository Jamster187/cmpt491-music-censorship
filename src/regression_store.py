"""Transactional compact results, deterministic rankings and strict resume identity."""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3

import numpy as np


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    if isinstance(value, np.ndarray):
        return clean(value.tolist())
    if isinstance(value, (np.integer, np.bool_)):
        return value.item()
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    return value


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(clean(value), indent=2, sort_keys=True, allow_nan=False) + "\n")
    temp.replace(path)


class Store:
    def __init__(self, path, identity, candidates, predictors):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        if self.db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Corrupt checkpoint database")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS candidates (id INTEGER PRIMARY KEY, k INTEGER NOT NULL,
                i1 INTEGER NOT NULL, i2 INTEGER, i3 INTEGER);
            CREATE TABLE IF NOT EXISTS scores (id INTEGER NOT NULL, fold INTEGER NOT NULL,
                r2 REAL, mae REAL NOT NULL, mse REAL NOT NULL, skill REAL,
                rank INTEGER NOT NULL, fallback INTEGER NOT NULL, PRIMARY KEY(id,fold));
            CREATE VIEW IF NOT EXISTS hierarchy AS
              WITH averages AS (SELECT c.*, CASE WHEN COUNT(s.r2)=3 THEN AVG(s.r2) END AS validation_r2, AVG(s.mae) AS validation_mae,
                AVG(s.mse) AS validation_mse, CASE WHEN COUNT(s.skill)=3 THEN AVG(s.skill) END AS validation_skill,
                MIN(s.skill) AS worst_period_skill, MAX(s.skill)-MIN(s.skill) AS period_skill_range,
                SUM(s.fallback) AS qr_svd_folds
                FROM candidates c JOIN scores s ON c.id=s.id GROUP BY c.id
                HAVING COUNT(*)=3)
              SELECT *, ROW_NUMBER() OVER (ORDER BY validation_skill DESC,k,id) AS validation_rank,
                ROW_NUMBER() OVER (PARTITION BY k ORDER BY validation_skill DESC,id) AS rank_within_k
              FROM averages;
        """)
        saved = self.get("identity")
        if saved is not None and saved != clean(identity):
            self.close()
            raise ValueError("Resume identity mismatch: data, code, specification or candidate sample changed")
        indices = {p: i for i, p in enumerate(predictors)}
        rows = [(i, len(c), *([indices[p] for p in c]+[None]*(3-len(c)))) for i, c in candidates]
        if saved is None:
            with self.db:
                self.put("identity", identity)
                self.put("predictors", predictors)
                self.db.executemany("INSERT INTO candidates VALUES (?,?,?,?,?)", rows)
        elif [tuple(r) for r in self.db.execute("SELECT * FROM candidates ORDER BY id")] != rows:
            self.close()
            raise ValueError("Checkpoint candidate catalog mismatch")

    def get(self, key):
        row = self.db.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, key, value):
        self.db.execute("INSERT OR REPLACE INTO metadata VALUES (?,?)",
                        (key, json.dumps(clean(value), sort_keys=True, allow_nan=False)))

    def completed(self, fold):
        return {r[0] for r in self.db.execute("SELECT id FROM scores WHERE fold=?", (fold,))}

    def save(self, fold, candidates, result, metadata, timing, stratum_key=None, stratum_info=None):
        rows = [(i, fold, result["r2"][j], result["mae"][j], result["mse"][j],
                 result["skill"][j], result["rank"][j], result["fallback"][j])
                for j, (i, _) in enumerate(candidates)]
        # Metrics and progress commit together. An interrupted transaction is
        # rerun; a committed batch is never fitted again on resume.
        with self.db:
            self.db.executemany("INSERT INTO scores VALUES (?,?,?,?,?,?,?,?)", clean(rows))
            self.put("fold_"+str(fold), metadata)
            totals = self.get("timing") or {}
            for key, value in timing.items():
                totals[key] = totals.get(key, 0) + value
            self.put("timing", totals)
            if stratum_key:
                old = self.get(stratum_key) or dict(stratum_info)
                for name, value in timing.items():
                    old[name] = old.get(name, 0) + value
                self.put(stratum_key, old)

    def rows(self, k=None, limit=None):
        query = "SELECT * FROM hierarchy"
        params = []
        if k is not None:
            query += " WHERE k=?"
            params.append(k)
        query += " ORDER BY validation_rank"
        if limit is not None:
            query += " LIMIT ?"
            params.append(limit)
        predictors = self.get("predictors")
        folds = [self.get("fold_"+str(f)) for f in range(3)]
        baseline_mse = np.mean([f["baseline"]["mse"] for f in folds])
        for row in self.db.execute(query, params):
            r = dict(row)
            r["predictors"] = [predictors[r.pop(key)] for key in ("i1", "i2", "i3") if r[key] is not None]
            r.pop("i2", None); r.pop("i3", None)
            r["validation_rmse"] = r["validation_mse"]**.5
            bases = [f["baseline"]["r2"] for f in folds]
            r["baseline_r2"] = np.mean(bases) if all(b is not None for b in bases) else None
            r["baseline_mae"] = np.mean([f["baseline"]["baseline_mae"] for f in folds])
            r["baseline_rmse"] = baseline_mse**.5
            r["n_validation"] = sum(f["n_validation"] for f in folds)
            r["validation_songs"] = sum(f["validation_songs"] for f in folds)
            r["n_train_by_period"] = [f["n_train"] for f in folds]
            r["period_metrics"] = [dict(x) for x in self.db.execute(
                "SELECT fold,r2,mae,mse,skill,rank FROM scores WHERE id=? ORDER BY fold", (r["id"],))]
            yield clean(r)

    def complete(self):
        n = self.db.execute("SELECT COUNT(*) FROM candidates").fetchone()[0]
        return all(len(self.completed(f)) == n for f in range(3))

    def stability(self, selected_id):
        predictors = self.get("predictors")
        output = []
        for fold in range(3):
            rows = self.db.execute("""SELECT c.*,s.skill,s.r2,s.mae,s.mse,
                ROW_NUMBER() OVER (ORDER BY s.skill DESC,c.k,c.id) AS period_rank
                FROM scores s JOIN candidates c ON s.id=c.id WHERE s.fold=?
                ORDER BY period_rank""", (fold,)).fetchall()
            winner = dict(rows[0])
            chosen = next(dict(r) for r in rows if r["id"] == selected_id)
            output.append(dict(fold=fold, best_predictors=[predictors[winner[key]] for key in
                ("i1", "i2", "i3") if winner[key] is not None], best_skill=winner["skill"],
                selected_period_rank=chosen["period_rank"], selected_skill=chosen["skill"],
                selected_r2=chosen["r2"], candidates=len(rows)))
        return output

    def close(self):
        self.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
