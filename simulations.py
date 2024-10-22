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
    
    # Convert columns to numeric, invalid parsing will be set as NaN
    df[['2PA', '2P%', '3PA', '3P%', 'FTA', 'FT%', 'Mean', 'Line']] = df[['2PA', '2P%', '3PA', '3P%', 'FTA', 'FT%', 'Mean', 'Line']].apply(pd.to_numeric, errors='coerce')
    
    results = []

    # Iterate through rows
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
        
        # Convert relevant values to integers or floats
        twoPA, dectwoPA = row['2PA'] // 1, row['2PA']  - row['2PA'] // 1
        twoPercent = float(row['2P%'])
        threePA, decthreePA = row['3PA'] // 1, row['3PA'] - row['3PA'] // 1
        threePercent = float(row['3P%'])
        fta, decFTA = row['FTA'] // 1, row['FTA'] - row['FTA'] // 1
        ftPercent = float(row['FT%'])

        simPoints = []
        
        # Perform 10,000 simulations for each player
        for _ in range(10000):
            two_p_makes = np.random.binomial(n=twoPA, p=twoPercent) + (dectwoPA if random.randint(0, 10000) <= twoPercent * 10000 else 0)
            three_p_makes = np.random.binomial(n=threePA, p=threePercent) + (decthreePA if random.randint(0, 10000) <= threePercent * 10000 else 0)
            ft_makes = np.random.binomial(n=fta, p=ftPercent) + (decFTA if random.randint(0, 10000) <= ftPercent * 10000 else 0)
            # Calculate total points in this simulation
            total_points = (2 * two_p_makes) + (3 * three_p_makes) + (1 * ft_makes)
            simPoints.append(total_points)

        line = row['Line']
        above_line_count = sum(np.array(simPoints) > line)
        above_line_prob = above_line_count / 10000
        
        results.append({
            'Name': row['Name'],
            'Mean Simulated Points': np.mean(simPoints),
            'Line': row['Line'],  
            '%Above' : above_line_prob,
            "%Below" : 1- above_line_prob
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
