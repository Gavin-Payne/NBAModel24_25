import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os
import json
import sqlite3
import time

load_dotenv()
googleJSON = os.getenv('GOOGLE_CLOUD_SERVICE_ACCOUNT')
googleAccount = json.loads(googleJSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(googleAccount, scopes=scopes)
client = gspread.authorize(creds)
SheetID = os.getenv("Sheet_ID")
sheet = client.open_by_url(f'https://docs.google.com/spreadsheets/d/{SheetID}/edit#gid=478985565')
sheets = [i.title for i in sheet.worksheets()[12:]]


dataBase = sqlite3.connect('nba_ids.db')
base = dataBase.cursor()
base.execute('''CREATE TABLE IF NOT EXISTS homeAwayPlayer
             (playerName TEXT, minutesHome REAL, minutesAway REAL, twoPointHome REAL, twoPointAway REAL, threePointHome REAL, 
             threePointAway REAL, FTHome REAL, FTAway REAL, gamesPlayedHome INTEGER, gamesPlayedAway INTEGER,
             twPAA INTEGER, twPAH INTEGER, thPAA INTEGER, thPAH INTEGER, FTAA INTEGER, FTAH INTEGER)''')
dataBase.commit()

for sheetName in sheets:
    time.sleep(2)
    sh = sheet.worksheet(sheetName)
    
    data = sh.get("I3:AE120")
    
    if not data:
        print(f"No data found for sheet: {sheetName}")
        continue
    
    df = pd.DataFrame(data)
    
    if df.empty:
        print(f"Empty DataFrame for sheet: {sheetName}")
        continue
    
    df.columns = ['Location', 'Opp', 'Result', 'GS', 'MP', 'FG', 'FGA', 'FG%', 
                    '3P', '3PA', '3P%', 'FT', 'FTA', 'FT%', 'ORB', 'DRB', 'TRB', 
                    'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS']
    
    df.replace({'0000000': None, '': None, 'N/A': None}, inplace=True)
    
    df['minutes'] = df['MP'].apply(lambda x: int(x.split(':')[0]) + int(x.split(':')[1]) / 60)

    
    df["FG"] = pd.to_numeric(df["FG"])
    df["3P"] = pd.to_numeric(df["3P"])
    df["FGA"] = pd.to_numeric(df["FGA"])
    df["3PA"] = pd.to_numeric(df["3PA"])
    df["FT"] = pd.to_numeric(df["FT"])
    df["FTA"] = pd.to_numeric(df["FTA"])
    df["3P%"] = pd.to_numeric(df["3P%"])
    df["FT%"] = pd.to_numeric(df["FT%"])
    
    df["2P"] = df["FG"] - df["3P"]
    df["2PA"] = df["FGA"] - df["3PA"]
    df["2P%"] = df["2P"] / df["2PA"]
    
    AwayDf = df[df['Location'] == '@']
    HomeDf = df[df['Location'] != '@']
    
    base.execute("SELECT * FROM homeAwayPlayer WHERE playerName = ?", (sheetName,))
    result = base.fetchone()
    
    if result is None:
        base.execute("INSERT INTO homeAwayPlayer (playerName, minutesHome, minutesAway, twoPointHome, twoPointAway, threePointHome, threePointAway, FTHome, FTAway, gamesPlayedHome, gamesPlayedAway, twPAA, twPAH , thPAA, thPAH, FTAA, FTAH) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                     (sheetName,
                      HomeDf["minutes"].sum()/len(HomeDf.index),
                      AwayDf["minutes"].sum()/len(AwayDf.index),
                      HomeDf["2P"].sum()/HomeDf["2PA"].sum(), 
                      AwayDf["2P"].sum()/AwayDf["2PA"].sum(), 
                      HomeDf["3P"].sum()/HomeDf["3PA"].sum(), 
                      AwayDf["3P"].sum()/AwayDf["3PA"].sum(), 
                      HomeDf["FT"].sum()/HomeDf["FTA"].sum(), 
                      AwayDf["FT"].sum()/AwayDf["FTA"].sum(), 
                      len(HomeDf.index), 
                      len(AwayDf.index),
                      int(HomeDf["2PA"].sum()),
                      int(AwayDf["2PA"].sum()),
                      int(HomeDf["3PA"].sum()),
                      int(AwayDf["3PA"].sum()),
                      int(HomeDf["FTA"].sum()),
                      int(AwayDf["FTA"].sum())))
        dataBase.commit()

    print(sheetName)
    

