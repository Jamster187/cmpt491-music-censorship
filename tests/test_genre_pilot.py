import sys
from pathlib import Path
import sqlite3
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from genre_pilot import collect
from genre_rules import assign,mapping

class GenrePilotTests(unittest.TestCase):
    def test_external_id_join_does_not_inherit_unlinked_candidate(self):
        c=sqlite3.connect(':memory:');c.row_factory=sqlite3.Row
        c.executescript('CREATE TABLE links(song_id,provider,level,entity_id); CREATE TABLE evidence(provider,level,entity_id,label,field,votes,reference,raw);')
        c.execute('INSERT INTO links VALUES (?,?,?,?)',('song','MusicBrainz','recording','accepted'))
        for eid,label in [('accepted','country'),('rejected','rap')]:
            c.execute('INSERT INTO evidence VALUES (?,?,?,?,?,?,?,?)',('MusicBrainz','recording',eid,label,'tags',1,'{}','{}'))
        self.assertEqual(assign(collect(c,'song'))['primary_genre'],'Country')
        self.assertEqual(collect(c,'unknown'),[])
        c.close()
    def test_afrobeat_is_not_afrobeats(self):
        self.assertEqual(mapping('afrobeat'),[])
        self.assertEqual(mapping('afrobeats'),['Afrobeats / African Pop'])
        self.assertEqual(len(mapping('amapiano')),2)

if __name__=='__main__':unittest.main()
