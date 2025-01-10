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

# os.system('python getLineups.py')
# os.system('oddsScrape.py')
# os.system('python minutesScrape.py')
os.system('python simulations.py')

banned = [
    
]

df = pd.DataFrame(sh.get("B5:S154"))


df.columns = ['Name', 'Opp', "H/A", "Minutes", '2PA', '2P%', '3PA', '3P%', 'FTA', 'FT%', "Mean", "Line",
              'OverOdds', 'UnderOdds', '%Above', '%Below', 'minOverOdds', 'minUnderOdds']

df.replace('#N/A', np.nan, inplace=True)
df.replace("#DIV/0!", np.nan, inplace=True)
calcData = df.dropna()

def adjustOdds(odds):
    odds = odds.replace('−', '-').replace('+', '').strip()
    if int(odds) > 0:
        return int(odds) - 100
    else:
        return int(odds) + 100
    
def reverseAdjustOdds(odds):
    if int(odds) > 0:
        return int(odds) + 100
    else:
        return int(odds) - 100

calcData['minOverOdds'] = calcData['minOverOdds'].apply(adjustOdds)
calcData["minUnderOdds"] = calcData['minUnderOdds'].apply(adjustOdds)
calcData['OverOdds'] = calcData['OverOdds'].apply(adjustOdds)
calcData['UnderOdds'] = calcData['UnderOdds'].apply(adjustOdds)

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
plays["OddsO/U"] = np.where(plays['Bet'] == "Over", plays["OverOdds"], plays["UnderOdds"])
plays["OddsO/U"] = plays["OddsO/U"].apply(reverseAdjustOdds)
plays = plays[~plays["Opp"].isin(banned)]
outputData = plays[["Name", "Bet", "Line", "OddsO/U", "%Above", "%Below"]]

todaysPlays = [outputData.columns.values.tolist()] + outputData.values.tolist()

sh = sheet.worksheet("Plays")
sh.batch_clear(["B2:H151"])
sh.update(range_name="B2", values=todaysPlays)

print(calcData[["Name", "Bet", "%Above", "%Below"]])

