"""Freeze 300 song identities without reading genre decisions or classifier scores."""
import csv
import hashlib
import json
import re
from genre_evidence import ROOT,OUT,PERIODS,ro,period

ANCHORS=[
('I Fall To Pieces','Patsy Cline'),('Respect','Aretha Franklin'),('Hey Jude','The Beatles'),("Can't Help Falling In Love",'Elvis Presley'),("I Can't Stop Loving You",'Ray Charles'),('The Christmas Song','Nat King Cole'),('Folsom Prison Blues','Johnny Cash'),('Hello, Dolly','Louis Armstrong'),('Like A Rolling Stone','Bob Dylan'),('I Heard It Through The Grapevine','Marvin Gaye'),
('I Feel Love','Donna Summer'),("Stayin' Alive",'Bee Gees'),("Let's Stay Together",'Al Green'),("Knockin' On Heaven's Door",'Bob Dylan'),('Jolene','Dolly Parton'),('Paranoid','Black Sabbath'),('Bohemian Rhapsody','Queen'),('Feels So Good','Chuck Mangione'),("Rapper's Delight",'Sugarhill'),
('Billie Jean','Michael Jackson'),('Purple Rain','Prince'),('Walk This Way','Run'),('Never Gonna Give You Up','Rick Astley'),("Livin' On A Prayer",'Bon Jovi'),('Fast Car','Tracy Chapman'),('Red Red Wine','UB40'),('Conga','Miami Sound Machine'),('I Wanna Dance With Somebody','Whitney Houston'),
('Enter Sandman','Metallica'),('Smells Like Teen Spirit','Nirvana'),('Waterfalls','TLC'),('Doo Wop','Lauryn Hill'),('Macarena','Los Del Rio'),('Achy Breaky Heart','Billy Ray Cyrus'),("Livin' La Vida Loca",'Ricky Martin'),('My Heart Will Go On','Celine Dion'),('Santeria','Sublime'),
('Looking For You','Kirk Franklin'),('I Can Only Imagine','MercyMe'),("Hips Don't Lie",'Shakira'),('How You Remind Me','Nickelback'),('In The End','Linkin Park'),("Don't Know Why",'Norah Jones'),('Gold Digger','Kanye West'),('Crazy In Love','Beyonce'),
('Gangnam Style','PSY'),('Shake It Off','Taylor Swift'),('Blinding Lights','The Weeknd'),('We Found Love','Rihanna'),('Get Lucky','Daft Punk'),('You Say','Lauren Daigle'),('I Like It','Cardi B'),('One Dance','Drake'),('Redbone','Childish Gambino'),
('Dynamite','BTS'),('Ice Cream','BLACKPINK'),('Calm Down','Rema'),('Water','Tyla'),('Last Last','Burna Boy'),('Essence','Wizkid'),('Free Mind','Tems'),('Moscow Mule','Bad Bunny'),("'Til You Can't",'Cody Johnson'),('Good 4 U','Olivia Rodrigo')]
SEED='cmpt491-genre-pilot-v1'


def key(song):return hashlib.sha256((SEED+song['song_id']).encode()).hexdigest()
def complex_credit(artist):return bool(re.search(r'\b(?:feat\.?|featuring|with)\b| & | X |,',artist,re.I))


def select(songs):
    selected={};missing=[];anchor_counts={p:0 for _,_,p in PERIODS}
    for title,artist in ANCHORS:
        candidates=[s for s in songs if title.casefold() in s['title'].casefold() and artist.casefold() in s['artist'].casefold()]
        if not candidates:missing.append([title,artist]);continue
        s=min(candidates,key=lambda s:(-s['weekly_rows'],s['song_id']))
        if anchor_counts[s['period']]>=10:continue
        if s['song_id'] not in selected:
            selected[s['song_id']]=dict(s,sample_role='challenge',sample_stratum='predeclared_identity');anchor_counts[s['period']]+=1
    for i,(_,_,p) in enumerate(PERIODS):
        quota=43 if i<6 else 42
        groups={}
        for s in songs:
            if s['period']==p and s['song_id'] not in selected:
                group=('high' if s['best_rank']<=25 else 'lower')+('_complex' if complex_credit(s['artist']) else '_simple')
                groups.setdefault(group,[]).append(s)
        for group in groups:groups[group].sort(key=key)
        while sum(s['period']==p for s in selected.values())<quota:
            progress=False
            for group in sorted(groups):
                if not groups[group] or sum(s['period']==p for s in selected.values())>=quota:continue
                s=groups[group].pop(0);selected[s['song_id']]=dict(s,sample_role='stratified_hash',sample_stratum=group);progress=True
            if not progress:raise ValueError('Insufficient stratum population')
    return sorted(selected.values(),key=lambda s:(s['period'],s['song_id'])),missing


def build():
    final=set(json.loads((ROOT/'data/processed/month_end_catchup/population.json').read_text())['new_population'])
    c=ro(ROOT/'data/processed/research.db');c.row_factory=__import__('sqlite3').Row
    songs=[dict(r,period=period(r['first_chart_date'][:4])) for r in c.execute('SELECT song_id,title,artist,first_chart_date,best_chart_rank best_rank,chart_observation_count weekly_rows FROM songs') if r['song_id'] in final];c.close()
    selected,missing=select(songs)
    if len(selected)!=300 or len({s['song_id'] for s in selected})!=300:raise ValueError('Wrong sample population')
    path=ROOT/'reports/genre/sample.csv';path.parent.mkdir(parents=True,exist_ok=True)
    import io
    buffer=io.StringIO();w=csv.DictWriter(buffer,fieldnames=list(selected[0]),lineterminator='\n');w.writeheader();w.writerows(selected)
    if path.exists() and path.read_text()!=buffer.getvalue():raise ValueError('Frozen sample differs')
    path.write_text(buffer.getvalue())
    (OUT/'sample_design.json').write_text(json.dumps(dict(seed=SEED,anchors=ANCHORS,unavailable_anchors=missing,period_quotas=[43]*6+[42],sample_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),population=28041),ensure_ascii=False,indent=2)+'\n')
    print('Sample frozen',len(selected),'challenge',sum(s['sample_role']=='challenge' for s in selected),'unavailable anchors',missing)

if __name__=='__main__':build()
