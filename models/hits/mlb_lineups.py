import re
import requests

import pandas as pd

from datetime import datetime
from bs4 import BeautifulSoup

class BasesLineups():
    
    def soup_setup(self, url):
        
        response = requests.get(url)
        print(response)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        return soup
    
    def team_cleanup(self, tm):
        team_names = {'Yankees':'NYY', 'Red Sox':'BOS', 'Blue Jays':'TOR', 
                      'Orioles':'BAL', 'Rays':'TBR', 'Twins':'MIN', 'Cleveland':'CLE',
                      'White Sox':'CHW', 'Royals':'KCR', 'Tigers':'DET', 'Angels':'LAA',
                      'Astros':'HOU', 'Athletics':'OAK', 'Mariners':'SEA',
                      'Rangers':'TEX', 'Mets':'NYM', 'Braves':'ATL', 'Phillies':'PHI',
                      'Marlins':'MIA', 'Nationals':'WSN', 'Cubs':'CHC', 'Cardinals':'STL',
                      'Pirates':'PIT', 'Brewers':'MIL', 'Reds':'CIN', 'Padres':'SDP',
                      'Dodgers':'LAD', 'Rockies':'COL', 'Diamondbacks':'ARI', 'Giants':'SFG'}
        if tm in team_names:
            clean_team = team_names[tm]
            return clean_team
        else:
            print(f"Invalid Team Name: {tm}")
            return tm
        
        
    def get_lineups(self, date):
        lineup_soup = self.soup_setup(f"https://www.fangraphs.com/livescoreboard.aspx?date={date}")
        
        games = {}
        name_soup = lineup_soup.findAll('td')
        for i in name_soup:
            if re.search('^[A-Za-z ]+ @ ', i.text):
                game_name = re.findall('[A-Za-z ]* @ [A-Za-z ]*', i.text)
                away_team = self.team_cleanup(re.findall('^[A-Za-z ]*', i.text)[0].rstrip())
                home_team = self.team_cleanup(re.findall('@ [A-Za-z ]*', i.text)[0].replace("@ ", "").rstrip())
                away_sp = re.findall('SP: [A-Za-z. -]+', i.text)[0].replace('SP: ', '').replace('SP', '')
                home_sp = re.findall('[a-z.]SP: [A-Za-z. -]+', i.text)[0]
                home_sp = re.sub('[a-z.]SP: ', '', home_sp)
                home_sp = re.sub('OP. [A-Za-z. -]+', '', home_sp)
                players = re.findall('\d\. [A-Za-z-. ]+ \(\w{1,2}\)', i.text)
                home_lineup, away_lineup = {}, {}
                counter = 0
                for player in players:
                    bo = re.findall('\d', player)[0]
                    name = re.sub('\d\. ', '', player)
                    name = re.sub('\(\w{1,2}\)', '', name).rstrip()
                    position = re.findall('\(\w{1,2}\)', player)[0].replace('(', '').replace(')', '')
                    if counter < 9:
                        away_lineup[bo] = {'player':name, 'position':position}
                    else:
                        home_lineup[bo] = {'player':name, 'position':position}
                    counter += 1
                
                if game_name[0] in games:
                    game_name[0] = f"{game_name[0]} Gm 2"
                games[game_name[0]] = {'away_team':away_team,
                                       'home_team':home_team,
                                       'away_sp':away_sp,
                                       'home_sp':home_sp,
                                       'away_lineup':away_lineup,
                                       'home_lineup':home_lineup}
            
        return games