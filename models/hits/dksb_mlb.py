import requests
import re

import pandas as pd

from datetime import datetime
from bs4 import BeautifulSoup

class ScrapeDKBases():
    def soup_setup(self, url):
        
        response = requests.get(url)
        print(response)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        return soup
    
    def team_cleanup(self, tm_name):
        """
        Takes an MLB team name from DraftKings and converts it to FanGraphs' format.
        """
        annoying = {'WAS Nationals':'WSN', 'CHI White Sox':'CHW', 'CHI Cubs':'CHC'}
        names = tm_name.split()
        if tm_name in annoying:
            city = annoying[tm_name]
        elif len(names[0]) == 2:
            city = f'{names[0]}{names[1][0]}'
        else:
            city = names[0]
        
        return city
        
        
    def mlb_ws(self):
        """
        Scrapes current World Series odds.
        
        Returns
        -------
        lamarca : nested dictionaries in the form of
        {<team abbreviation>: {'odds':<odds>, 'date_time':<datetime object with the current date and time>}, ...}

        """
        soup_today = self.soup_setup(f"https://sportsbook.draftkings.com/leagues/baseball/2003?category=team-futures&subcategory=world-series-2021")
        
        teams = []
        team_soup = soup_today.findAll('span', {'class':'sportsbook-outcome-cell__label'})
        for i in team_soup:
            #Teams are listed on DK as <city abbreviation> <team nickname> so 
            #we want to format team abbreviations to match FanGraphs' convention:
            city = self.team_cleanup(i.text)
            #Once the abbrevations are cleaned up, add them to a list:
            teams.append(city)
        
        odds = []
        odds_soup = soup_today.findAll('span', {'class':'sportsbook-odds american default-color'})
        for i in odds_soup:
            odd = i.text
            odd = int(odd.replace('+', ''))
            #Once odds have been cleaned up, convert them to percentages (easier to understand and/or plot):
            if odd > 0:
                pct = round(1 / ((odd/100) + 1), 4)
            else:
                pct = round(1 - (1 / ((-1*odd/100) + 1)), 4)
            #Add percentages to a list:
            odds.append(pct)
        
        #Add team abbreviations, odds and the current date and time to nested dictionaries:
        lamarca = {}
        #Of course, World Series winners probably aren't celebrating with $14 
        #bottles of lamarca but it's some damn good prosecco.
        for i in range(len(teams)):
            lamarca[teams[i]] = {'odds':odds[i], 'date_time':datetime.now()}
            
        return lamarca
        
    def mlb_games(self):
        """
        Scrapes current MLB game odds.

        Returns
        -------
        tequila : nested dictionaries in the form of
        {<team abbreviation>: {'moneyline':<odds>, 'opponent':<opponent team abbreviation>, 'home':<1 if home, 0 if away>}, ...}.

        """
        games = pd.read_html("https://sportsbook.draftkings.com/leagues/baseball/2003?category=game-lines-&subcategory=game")
        #Games sometimes come in different dataframes for some reason...
        all_games = pd.DataFrame()
        for i in range(len(games)):
            games[i].columns = ['Team', 'runline', 'total', 'moneyline']
            all_games = all_games.append(games[i])
        #Gotta format those team names!
        all_games['Team'] = all_games['Team'].str.replace("\d+:\d{2}[PA]M", "")
        tm_names = []
        for i in all_games['Team'].str.split():
            if i[0] in ['NY', 'LA', 'TB', 'SF', 'SD', 'KC']:
                tm = i[0] + i[1][0]
            elif i[0] == 'CHI':
                if i[1] == 'White':
                    tm = 'CHW'
                else:
                    tm = 'CHC'
            elif i[0] == 'WAS':
                tm = 'WSN'
            else:
                tm = i[0]
            tm_names.append(tm)        
        all_games['Team'] = tm_names
        #Totals need to be pretty too!
        all_games['total'] = all_games['total'].str.replace("[+-]\d{3}", "")
        all_games['total'] = all_games['total'].str.replace("[OU]\s", "")
        all_games['total'] = all_games['total'].astype(float)
                
        return all_games

    def mlb_rsw(self):
        
        soup_today = self.soup_setup(f"https://sportsbook.draftkings.com/leagues/baseball/2003?category=team-futures&subcategory=regular-season-wins")
        
        tm_names = {'LAA': 'Angels', 'HOU': 'Astros', 'OAK': 'Athletics', 'TOR': 'Blue Jays',
                    'ATL': 'Braves', 'MIL': 'Brewers', 'STL': 'Cardinals', 'CHC': 'Cubs',
                    'ARI': 'Diamondbacks', 'LAD': 'Dodgers', 'SFG': 'Giants',
                    'CLE': 'Indians', 'SEA': 'Mariners', 'MIA': 'Marlins', 'NYM': 'Mets',
                    'WSN': 'Nationals', 'BAL': 'Orioles', 'SDP': 'Padres', 'PHI': 'Phillies',
                    'PIT': 'Pirates', 'TEX': 'Rangers', 'TBR': 'Rays', 'BOS': 'Red Sox',
                    'CIN': 'Reds', 'COL': 'Rockies', 'KCR': 'Royals', 'DET': 'Tigers',
                    'MIN': 'Twins', 'CHW': 'White Sox', 'NYY': 'Yankees'}
        
        teams = []
        tm_raw = soup_today.findAll('a', {'class':'sportsbook-event-accordion__title'})
        for i in tm_raw:
            for x in tm_names:
                tm = re.findall(tm_names[x], i.text)
                if tm:
                    teams.append(x)
                    break        
        
        overs = []
        unders = []
        odds = []
        labels_raw = soup_today.findAll('span', {'class':'sportsbook-outcome-cell__label'})
        lines_raw = soup_today.findAll('span', {'class':'sportsbook-outcome-cell__line'})
        odds_raw = soup_today.findAll('span', {'class':'sportsbook-odds american default-color'})
        for label, line, price in zip(labels_raw, lines_raw, odds_raw):
            if label.text == 'Over':
                overs.append({'Wins':float(line.text), 'Odds':float(price.text)})
            else:
                unders.append({'Wins':float(line.text), 'Odds':float(price.text)})
        for x, y in zip(overs, unders):
            odds.append({'Over':x, 'Under':y})

        bourbon = {}
        for team, wins in zip(teams, odds):
            bourbon[team] = wins
        
        return bourbon
    
    def mlb_props(self):
        
        players = pd.read_html("https://sportsbook.draftkings.com/leagues/baseball/2003?category=player-props&subcategory=total-hits")
        all_players = pd.DataFrame()
        for i in range(len(players)):
            all_players = all_players.append(players[i])
        all_players.rename(columns={'PLAYER':'player', 'OVER':'over', 'UNDER':'under'}, inplace=True)
        
        all_players['over'] = all_players['over'].str.replace("Over ", "")
        all_players['under'] = all_players['under'].str.replace("Under ", "")
        
        all_players['over_odds'] = all_players['over'].str.replace("\d\.\d\+?", "")
        all_players['under_odds'] = all_players['under'].str.replace("\d\.\d\+?", "")
        
        all_players['over'] = all_players['over'].str.replace("[-+]\d{3}", "")
        all_players['under'] = all_players['under'].str.replace("[-+]\d{3}", "")
        
        all_players['player'] = all_players['player'].str.lower()
        
        for i in all_players.columns:
            if i != 'player':
                all_players[i] = all_players[i].astype(float)
                
        all_players.reset_index(drop=True, inplace=True)
        
        return all_players