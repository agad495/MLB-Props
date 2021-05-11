# MLB-Props
MLB prop betting models.

## Use:

### Hitting Model:
```python
import statistics

from dksb_mlb import ScrapeDKBases
from baseball_props import PropBases
from ev_calculator import ev_calc
from mlb_lineups import BasesLineups
from pybaseball import playerid_lookup
from datetime import datetime

import pandas as pd

dk = ScrapeDKBases()
games = dk.mlb_games()
hit_props = dk.mlb_props()
hit_props['over_preds'] = 0
hit_props['under_preds'] = 0
hit_props['opp_pitcher'] = ''
hit_props['team'] = ''
hit_props['opp'] = ''
hit_props['bo'] = 0
hit_props['bid'] = 0
hit_props['pid'] = 0

bl = BasesLineups()
lineups = bl.get_lineups(datetime.today().strftime('%Y-%m-%d'))

for i in lineups:
    if lineups[i]['away_lineup'] and lineups[i]['home_lineup']:
        for j in lineups[i]['away_lineup']:
            hit_props['opp_pitcher'].where(hit_props['player']!=lineups[i]['away_lineup'][j]['player'].lower(), 
                                           lineups[i]['home_sp'].lower(), inplace=True)
            hit_props['team'].where(hit_props['player']!=lineups[i]['away_lineup'][j]['player'].lower(), 
                                           lineups[i]['away_team'], inplace=True)
            hit_props['opp'].where(hit_props['player']!=lineups[i]['away_lineup'][j]['player'].lower(), 
                                           lineups[i]['home_team'], inplace=True)
            hit_props['bo'].where(hit_props['player']!=lineups[i]['away_lineup'][j]['player'].lower(), 
                                           int(j), inplace=True)
        for j in lineups[i]['home_lineup']:
            hit_props['opp_pitcher'].where(hit_props['player']!=lineups[i]['home_lineup'][j]['player'].lower(), 
                                           lineups[i]['away_sp'].lower(), inplace=True)
            hit_props['team'].where(hit_props['player']!=lineups[i]['home_lineup'][j]['player'].lower(), 
                                           lineups[i]['home_team'], inplace=True)
            hit_props['opp'].where(hit_props['player']!=lineups[i]['home_lineup'][j]['player'].lower(), 
                                           lineups[i]['away_team'], inplace=True)
            hit_props['bo'].where(hit_props['player']!=lineups[i]['home_lineup'][j]['player'].lower(), 

bp = PropBases("mlb_statcast_logs.pkl", "../", "../", games, get_new_statcast=True)

batter_cleanup = {'jose abreu': 'josé abreu',
                  'miguel sanó': 'miguel sano',
                  'jose iglesias': 'josé iglesias',
                  'yandy diaz': 'yandy díaz'}
for name in batter_cleanup:
    hit_props['player'].where(hit_props['player']!=name, batter_cleanup[name], inplace=True)

#Save batter ids to dictionary so we only need to run this once per player per day
bid = {}
for hitter in hit_props['player']:
    if hitter not in bid:
        print(hitter)
        first_name = hitter.split()[0]
        last_name = hitter.split()[1]
        if first_name == 'j.p.':
            first_name = 'j. p.'
        elif first_name == 'j.t.':
            first_name = 'j. t.'
        elif first_name == 'j.d.':
            first_name = 'j. d.'
            
        bid_indy = playerid_lookup(last_name, first_name)
        bid[hitter] = bid_indy
for i in bid:
    if len(bid[i]) == 1:
        hit_props['bid'].where(hit_props['player']!=i, bid[i].loc[0,'key_mlbam'], inplace=True)
    elif len(bid[i]) == 0:
        continue
    else:
        print("Choose the index corresponding to the desired player:")
        print(bid[i])
        desired_index = input("Index: ")
        hit_props['bid'].where(hit_props['player']!=i, bid[i].loc[int(desired_index),'key_mlbam'], inplace=True)
    
#Same for pitchers
pid = {}
for pitcher in hit_props['opp_pitcher'].unique():
    if (pitcher not in pid) & (pitcher != ''):
        print(pitcher)
        first_name = pitcher.split()[0]
        last_name = pitcher.split()[1]
        if first_name == 'j.p.':
            first_name = 'j. p.'
        elif first_name == 'j.t.':
            first_name = 'j. t.'
        elif first_name == 'j.d.':
            first_name = 'j. d.'
        
        pid_indy = playerid_lookup(last_name, first_name)
        pid[pitcher] = pid_indy
for i in pid:
    if len(pid[i]) == 1:
        hit_props['pid'].where(hit_props['opp_pitcher']!=i, pid[i].loc[0,'key_mlbam'], inplace=True)
    elif len(pid[i]) == 0:
        continue
    else:
        print("Choose the index corresponding to the desired player:")
        print(pid[i])
        desired_index = input("Index: ")
        hit_props['pid'].where(hit_props['opp_pitcher']!=i, pid[i].loc[int(desired_index),'key_mlbam'], inplace=True)

oo = []
uo = []
for player, pitcher, bt, pt, bo in zip(hit_props['bid'], hit_props['pid'], 
                                       hit_props['team'], hit_props['opp'], hit_props['bo']):
    if pitcher and bt and pt:
        print("\r", player, end="")
            
        one_batter = bp.hit_odds(batter=player,
                                 pitcher=pitcher,
                                 bt=bt,
                                 pt=pt,
                                 xbo=bo)
        oo.append(one_batter['over_pct'])
        uo.append(one_batter['under_pct'])
    else:
        oo.append(0)
        uo.append(0)
hit_props['over_preds'] = oo
hit_props['under_preds'] = uo

over_ev, under_ev = [], []
for oo, op, uo, up in zip(hit_props['over_odds'], hit_props['over_preds'],
                          hit_props['under_odds'], hit_props['under_preds']):
    over_ev.append(ev_calc(oo, op))
    under_ev.append(ev_calc(uo, up))
hit_props['over_ev'] = over_ev
hit_props['under_ev'] = under_ev
```
The hit_props dataframe then contains an estimate EV of a 1 unit bet to the over or a 1 unit bet to the under.

At this time, the model only calculates whether or not a hitter will get 1+ hits in a game. Support for lines greater than 0.5 is being worked on.
