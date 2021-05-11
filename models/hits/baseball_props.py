import requests
import joblib

import pandas as pd
import numpy as np

from pybaseball import playerid_lookup, statcast
from bs4 import BeautifulSoup
from datetime import datetime

pd.set_option('max_columns', None)

class PropBases():
    
    def __init__(self, statcast_link, logs_path, odds_path, dk_games,
                 get_new_statcast=False):
        
        self.statbat_pa = pd.read_pickle(statcast_link).dropna(subset=['events'])
        if get_new_statcast:
            self.statbat = self.new_statcast(current_statcast=self.statbat_pa)
            self.statbat_pa = self.statbat_pa.append(self.statbat.dropna(subset=['events']))
            
        self.statbat_pa['estimated_ba_using_speedangle'].fillna(0, inplace=True)
        
        team_cleanup = {'CWS':'CHW', 'KC':'KCR', 'SD':'SDP', 'SF':'SFG', 'TB':'TBR', 'WSH':'WSN'}
        for team in team_cleanup:
            self.statbat_pa['home_team'].where(self.statbat_pa['home_team']!=team, team_cleanup[team], inplace=True)
            self.statbat_pa['away_team'].where(self.statbat_pa['away_team']!=team, team_cleanup[team], inplace=True)
        self.statbat_pa['pitching_team'] = np.where(self.statbat_pa['home_score']==self.statbat_pa['fld_score'],
                                       self.statbat_pa['home_team'], self.statbat_pa['away_team'])
        self.statbat_pa.sort_values(['pitching_team', 'game_date', 'inning'], inplace=True)
        self.statbat_pa.reset_index(drop=True, inplace=True)
        self.statbat_pa['pa_num_team'] = self.statbat_pa.groupby(['pitching_team'])['game_date'].rank(method='first', ascending=True)
        self.statbat_pa['team_xba_2500'] = self.statbat_pa.groupby(['pitching_team'])['estimated_ba_using_speedangle'].rolling(window=2500, min_periods=2500).mean().reset_index(drop=True)
        self.league_rolling = self.statbat_pa.groupby(['pitching_team']).agg({'team_xba_2500':'last'}) \
            .reset_index()
                    
        self.scaler = joblib.load("pa_scaler.sav")
        self.pa_model = joblib.load("pa_model.sav")
        
        self.mlb_games = dk_games     
        
        try:
            self.bid
        except:
            self.bid = {}
        
        
    def soup_setup(self, url):
        
        response = requests.get(url)
        print(response)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        return soup
    
    def get_dates(self, seasons=[2021]):
        months = {'January':'01', 'February':'02', 'March':'03', 'April':'04', 'May':'05',
                  'June':'06', 'July':'07', 'August':'08', 'September':'09', 'October':'10',
                  'November':'11', 'December':'12'}
        dates = []
        for j in seasons:
            soup20 = self.soup_setup(f"https://www.baseball-reference.com/leagues/MLB/{j}-schedule.shtml")
            headers = soup20.findAll("h3")
            for i in headers:
                try:
                    date_list = str(i).replace(r"<h3>", "").replace(r"</h3>", "").replace(",", "").split()
                    date_list[1] = months[date_list[1]]
                    if len(date_list[2]) == 1:
                        date_list[2] = f"0{date_list[2]}"
                except:
                    return dates
                dates.append(f"{date_list[3]}-{date_list[1]}-{date_list[2]}")
        
        return dates

    def new_statcast(self, current_statcast):
        latest = current_statcast['game_date'].max()
        dates = self.get_dates()
        
        statbat = pd.DataFrame()
        for date in dates:
            if date > datetime.strftime(latest, "%Y-%m-%d"):
                bat = statcast(date)
                print("\r", date, end="")
                statbat = statbat.append(bat)
                
        return statbat


    def rolling_statcast(self, pos, pid, stat_df):
        stat_df.sort_values([pos, 'game_date', 'inning'], inplace=True)
        stat_df.reset_index(drop=True, inplace=True)
        stat_df['pa_num'] = stat_df.groupby([pos])['game_date'].rank(method='first', ascending=True)
        stat_df['career_xba'] = stat_df.groupby([pos])['estimated_ba_using_speedangle'].rolling(window=1000, min_periods=0).mean().reset_index(drop=True)
        stat_df['250_xba'] = stat_df.groupby([pos])['estimated_ba_using_speedangle'].rolling(window=250, min_periods=250).mean().reset_index(drop=True)
        #We can use this 250 PA rolling average of xBA as batter strength
        xba_250_rolling = stat_df.dropna(subset=['250_xba'])
        if pos == 'batter':
            player_df = xba_250_rolling.query("batter == @pid").reset_index(drop=True)
        else:
            player_df = xba_250_rolling.query("pitcher == @pid").reset_index(drop=True)
            
        if len(player_df) > 0:
            player_odds = player_df.loc[len(player_df)-1, '250_xba']
        else:
            player_odds = 0
            
        return player_odds
            
    def hit_odds_work(self, bid, pid, team, bo, odds, total):
        batter_odds = self.rolling_statcast('batter', bid, self.statbat_pa)
        pitcher_odds = self.rolling_statcast('pitcher', pid, self.statbat_pa)
        tm_pitching = self.league_rolling.query("pitching_team == @team").reset_index().loc[0, 'team_xba_2500']
        
        total_odds = (batter_odds + ((pitcher_odds*0.75) + (tm_pitching*0.25))) / 2
        
        hitter = pd.DataFrame({'BO':[bo], 'team_ml':[odds], 'total':[total]}, index=[0])
        pa_pred = self.pa_model.predict(self.scaler.transform(hitter))[0]
        
        no_hits = (1-total_odds)**pa_pred
        if no_hits > 0.5:
            prop_odds = ((no_hits*100) / (1-no_hits)) * -1
        else:
            prop_odds = ((1/no_hits) - 1) * 100
        
        return {'line':0.5,'over_pct':round(1-no_hits,4),'over_odds':round(-1*prop_odds, 2),
                'under_pct':round(no_hits,4),'under_odds':round(prop_odds, 2)}
    
    def hit_odds(self, batter, pitcher, bt, pt, xbo):
        if type(batter) is list:
            try:
                batter_id = playerid_lookup(batter[1], batter[0])
                if len(batter_id) > 1:
                    print("Choose the index corresponding to the desired player:")
                    print(batter_id)
                    desired_index = input("Index: ")
                    batter_id = batter_id.loc[int(desired_index), 'key_mlbam']
                else:
                    batter_id = batter_id.loc[0, 'key_mlbam']
            except:
                print("Invalid batter name.")
                return
        else:
            batter_id = batter
            
        if type(pitcher) is list:
            try:
                pitcher_id = playerid_lookup(pitcher[1], pitcher[0]).loc[0, 'key_mlbam']
            except:
                print("Invalid pitcher name.")
                return
        else:
            pitcher_id = pitcher
        
        if type(xbo) is list:
            hit_options = {}
            for i in xbo:
                hitting = self.hit_odds_work(batter_id, pitcher_id, pt, i, 
                                             self.mlb_games.query("Team == @bt").reset_index().loc[0, 'moneyline'], 
                                             self.mlb_games.query("Team == @bt").reset_index().loc[0, 'total'])
                hit_options[i] = hitting  
            return hit_options
        
        else:
            hitting = self.hit_odds_work(batter_id, pitcher_id, pt, xbo, 
                                         self.mlb_games.query("Team == @bt").reset_index().loc[0, 'moneyline'], 
                                         self.mlb_games.query("Team == @bt").reset_index().loc[0, 'total'])
            return hitting
            
            
        
