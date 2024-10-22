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

def monteCarlo(sheetName):
    sh = sheet.worksheet(sheetName)
    df = pd.DataFrame(sh.get("B5:M154"))
    df.columns = ['Name', 'Opp', "H/A", "Minutes", '2PA', '2P%', '3PA', '3P%', 'FTA', 'FT%', "Mean", "Line"]
    
    df[['2PA', '2P%', '3PA', '3P%', 'FTA', 'FT%', 'Mean', 'Line']] = df[['2PA', '2P%', '3PA', '3P%', 'FTA', 'FT%', 'Mean', 'Line']].apply(pd.to_numeric, errors='coerce')
    
    results = []

    for index, row in df.iterrows():
        if row.isna().any():
            if row['Name']:
                results.append({
                'Name': row['Name'],
                'Mean Simulated Points': 0,
                'Line': 0,  
                '%Above' : .5,
                "%Below" : .5
                            })
            continue
        
        twoPA, dectwoPA = row['2PA'] // 1, row['2PA']  - row['2PA'] // 1
        twoPercent = float(row['2P%'])
        threePA, decthreePA = row['3PA'] // 1, row['3PA'] - row['3PA'] // 1
        threePercent = float(row['3P%'])
        fta, decFTA = row['FTA'] // 1, row['FTA'] - row['FTA'] // 1
        ftPercent = float(row['FT%'])

        simPoints = []
        
        # 10k simmies for each player
        for _ in range(10000):
            tPointMakes = np.random.binomial(n=twoPA, p=twoPercent) + (dectwoPA if random.randint(0, 10000) <= twoPercent * 10000 else 0)
            thPointMakes = np.random.binomial(n=threePA, p=threePercent) + (decthreePA if random.randint(0, 10000) <= threePercent * 10000 else 0)
            ftMakes = np.random.binomial(n=fta, p=ftPercent) + (decFTA if random.randint(0, 10000) <= ftPercent * 10000 else 0)
            points = (2 * tPointMakes) + (3 * thPointMakes) + (1 * ftMakes)
            simPoints.append(points)

        line = row['Line']
        countAbove = sum(np.array(simPoints) > line)
        percentAbove = countAbove / 10000
        
        results.append({
            'Name': row['Name'],
            'Mean Simulated Points': np.mean(simPoints),
            'Line': row['Line'],  
            '%Above' : percentAbove,
            "%Below" : 1- percentAbove
        })
    
    simulation_results = pd.DataFrame(results)
    
    return simulation_results

sheetName = "Calculations"
sh = sheet.worksheet(sheetName)
simdf = monteCarlo(sheetName)
insertFrame = simdf[["%Above", '%Below']]
insertFrame = [insertFrame.columns.values.tolist()] + insertFrame.values.tolist()
sh.batch_clear(["P4:Q154"])
sh.update("P4", insertFrame)
