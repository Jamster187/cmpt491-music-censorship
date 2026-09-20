"""Do not mistake a stopped/partial acquisition for a completed corpus."""
import json
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import lyrics_completion_check as completion


class CompletionTests(unittest.TestCase):
    def database(self,statuses):
        c=sqlite3.connect(':memory:')
        c.executescript('CREATE TABLE production_assets(song_id TEXT PRIMARY KEY); CREATE TABLE production_results(song_id TEXT PRIMARY KEY,payload TEXT); CREATE TABLE production_runs(state TEXT);')
        c.executemany('INSERT INTO production_assets VALUES (?)',[('a',),('b',)])
        c.executemany('INSERT INTO production_results VALUES (?,?)',[(sid,json.dumps({'status':status})) for sid,status in statuses.items()])
        return c

    def test_partial_population_cannot_be_reported_complete(self):
        c=self.database({'a':'accepted'})
        with patch.object(completion.production,'connect',return_value=c),patch.object(completion.production,'POPULATION',2):
            with self.assertRaisesRegex(ValueError,'Unprocessed'):completion.check()

    def test_unknown_disposition_cannot_count_as_completion(self):
        c=self.database({'a':'accepted','b':'unknown'})
        with patch.object(completion.production,'connect',return_value=c),patch.object(completion.production,'POPULATION',2):
            with self.assertRaisesRegex(ValueError,'Unknown dispositions'):completion.check()

    def test_running_worker_cannot_be_reported_complete(self):
        c=self.database({'a':'accepted','b':'not_found'});c.execute("INSERT INTO production_runs VALUES ('running')")
        with patch.object(completion.production,'connect',return_value=c),patch.object(completion.production,'POPULATION',2):
            with self.assertRaisesRegex(ValueError,'still active'):completion.check()
