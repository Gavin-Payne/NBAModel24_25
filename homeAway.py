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
base.execute('''CREATE TABLE IF NOT EXISTS homeAway
             (playerName TEXT, twoPointHome TEXT, twoPointAway TEXT, threePointHome TEXT, 
             threePointAway TEXT, FTHome TEXT, FTAway TEXT, gamesPlayedHome TEXT, gamesPlayedAway TEXT)''')
dataBase.commit()

for sheetName in sheets[:2]:
    sh = sheet.worksheet(sheetName)
    df = pd.DataFrame(sh.get("I3:AE120"))
    df.columns = ['Location', 'Opp', 'Result', 'GS', 'MP', 'FG', 'FGA', 'FG%', 
                    '3P', '3PA', '3P%', 'FT', 'FTA', 'FT%', 'ORB', 'DRB', 'TRB', 
                    'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS']
    print(df)
    
    

