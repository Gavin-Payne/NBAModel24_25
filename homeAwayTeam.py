import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os
import json
import sqlite3
import time
from datetime import datetime
import numpy as np

load_dotenv()
googleJSON = os.getenv('GOOGLE_CLOUD_SERVICE_ACCOUNT')
googleAccount = json.loads(googleJSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(googleAccount, scopes=scopes)
client = gspread.authorize(creds)
SheetID = os.getenv("Sheet_ID")
sheet = client.open_by_url(f'https://docs.google.com/spreadsheets/d/{SheetID}/edit#gid=478985565')
sheets = [i.title for i in sheet.worksheets()[20:]]

today = datetime.today()
counter = 19

dataBase = sqlite3.connect('nba_ids.db')
base = dataBase.cursor()
base.execute('''CREATE TABLE IF NOT EXISTS homeAwayTeam
             (teamName TEXT, twoPoint INTEGER, twoPointAtt INTEGER, twoPointPercent REAL, threePoint INTEGER, 
             threePointAtt INTEGER, threePointPercent REAL, FT INTEGER, FTAtt INTEGER, FTPercent REAL, ORB INTEGER,
             DRB INTEGER, TRB INTEGER, AST INTEGER, STL INTEGER, BLK INTEGER, TOV INTEGER, PF INTEGER, PTS INTEGER)''')
dataBase.commit()

hm = {}

for sheetName in sheets:
    counter += 1
    time.sleep(2)
    sh = sheet.worksheet(sheetName)
    
    date, data = sh.batch_get(["G3", "I3:AE120"])
    
    if not data:
        print(f"No data found for sheet: {sheetName}")
        continue
    
    date = date[0][0]
    date = datetime.strptime(date, "%Y-%m-%d")
    minDate = datetime(2024, 7, 1)
    thisSeason = date > minDate
    if not thisSeason:
        print(f"{sheetName} hasn't played this season")
        continue
    
    df = pd.DataFrame(data)
    
    if df.empty:
        print(f"Empty DataFrame for sheet: {sheetName}")
        continue
    
    df.columns = ['Location', 'Opp', 'MP', '2P', '2PA', '2P%', 
                    '3P', '3PA', '3P%', 'FT', 'FTA', 'FT%', 'ORB', 'DRB', 'TRB', 
                    'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS']
    
    df.replace({'0000000': None, '': None, 'N/A': None}, inplace=True)
    
    for col in df.columns[3:]:
        
        df[col] = pd.to_numeric(df[col])
    
    df["2P"] = df["2P"] - df["3P"]
    df["2PA"] = df["2PA"] - df["3PA"]
    df["2P%"] = df["2P"] / df["2PA"]
    
    AwayDf = df[df['Location'] == '@']
    HomeDf = df[df['Location'] != '@']
    for i in range(AwayDf.shape[0]):
        hm[f'home{AwayDf.iloc[i,1]}'] = hm.get(f'home{AwayDf.iloc[i,1]}', [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        data = hm[f'home{AwayDf.iloc[i,1]}']
        for j in range(len(data)):
            data[j] += AwayDf.iloc[i, 3 + j]
            
    for i in range(HomeDf.shape[0]):
        hm[f'away{HomeDf.iloc[i,1]}'] = hm.get(f'away{HomeDf.iloc[i,1]}', [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
        data = hm[f'away{HomeDf.iloc[i,1]}']
        for j in range(len(data)):
            data[j] += HomeDf.iloc[i, 3 + j]
    print(sheetName, counter)
            
teamData = []            
for team, s in hm.items():
    base.execute("INSERT INTO homeAwayTeam (teamName, twoPoint, twoPointAtt, twoPointPercent, threePoint, threePointAtt, threePointPercent, FT, FTAtt, FTPercent, ORB, DRB, TRB, AST, STL, BLK, TOV, PF, PTS) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (team, s[0], s[1], s[2], s[3], s[4], s[5], s[6], s[7], s[8], s[9], s[10], s[11], s[12], s[13], s[14], s[15], s[16], s[17]))
    dataBase.commit()
    row = [team] + [
        int(val) if isinstance(val, (int, np.int64)) else
        (float(val) if not np.isnan(val) and not np.isinf(val) else None)
        for val in s
    ]
    teamData.append(row)

sh = sheet.worksheet("homeAwayTeam")
sh.update(range_name="B2", values=teamData)