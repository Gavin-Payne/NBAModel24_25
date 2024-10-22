import requests
from bs4 import BeautifulSoup
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os
import json
import random
import sqlite3
import numpy as np

load_dotenv()
googleJSON = os.getenv('GOOGLE_CLOUD_SERVICE_ACCOUNT')
googleAccount = json.loads(googleJSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(googleAccount, scopes=scopes)
client = gspread.authorize(creds)
SheetID = os.getenv("Sheet_ID")
sheet = client.open_by_url(f'https://docs.google.com/spreadsheets/d/{SheetID}/edit#gid=478985565')
sh = sheet.worksheet("Calculations")

df = pd.DataFrame(sh.get("B5:S154"))

df.columns = ['Name', 'Opp', "H/A", "Minutes", '2PA', '2P%', '3PA', '3P%', 'FTA', 'FT%', "Mean", "Line",
              'OverOdds', 'UnderOdds', '%Above', '%Below', 'minOverOdds', 'minUnderOdds']

df.replace('#N/A', np.nan, inplace=True)
df.replace("#DIV/0!", np.nan, inplace=True)
calcData = df.dropna()

def adjust_odds(odds):
    odds = odds.replace('−', '-').replace('+', '').strip()
    if int(odds) > 0:
        return int(odds) - 100
    else:
        return int(odds) + 100

calcData['minOverOdds'] = calcData['minOverOdds'].apply(adjust_odds)
calcData["minUnderOdds"] = calcData['minUnderOdds'].apply(adjust_odds)
calcData['OverOdds'] = calcData['OverOdds'].apply(adjust_odds)
calcData['UnderOdds'] = calcData['UnderOdds'].apply(adjust_odds)

playable = []

for index, row in calcData.iterrows():
    mO, mU, O, U = row["minOverOdds"], row["minUnderOdds"], row['OverOdds'], row["UnderOdds"]
    temp = None
    if mO - O < -50:
        temp = "Over"
    elif mU - U < -50:
        temp = "Under"
    playable.append(temp)
    
calcData['Bet'] = playable
calcData = calcData.reindex(range(calcData.index.max()+1))
calcData.fillna("", inplace=True)

insertData = [[bet] for bet in calcData['Bet']]

sh.batch_clear(["T5:T"])
sh.update(range_name="T5", values=insertData)

plays = calcData[calcData['Bet'] != ""]
outputData = plays[["Name", "Bet", "%Above", "%Below"]]

todaysPlays = [outputData.columns.values.tolist()] + outputData.values.tolist()

sh = sheet.worksheet("Plays")
sh.batch_clear(["B2:H151"])
sh.update("B2", todaysPlays)

print(calcData[["Name", "Bet", "%Above", "%Below"]])

