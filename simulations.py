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
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects

load_dotenv()
googleJSON = os.getenv('GOOGLE_CLOUD_SERVICE_ACCOUNT')
googleAccount = json.loads(googleJSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(googleAccount, scopes=scopes)
client = gspread.authorize(creds)
SheetID = os.getenv("Sheet_ID")
sheet = client.open_by_url(f'https://docs.google.com/spreadsheets/d/{SheetID}/edit#gid=478985565')

twitterKey = os.getenv("TWITTER_KEY")
twitterSecretKey = os.getenv("TWITTER_SECRET_KEY")
twitterAccessToken = os.getenv("TWITTER_ACCESS_TOKEN")
twitterSecretAccessToken = os.getenv("TWITTER_SECRET_ACCESS_TOKEN")
twitterBearerToken = os.getenv("TWITTER_BEARER_TOKEN")

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
    
    
        graphData = []
        
        postPlayer = "Jeremy_Sochan"
        if row["Name"] == postPlayer:
            graphData = simPoints
        
        if graphData:
            fig, ax = plt.subplots(figsize=(10, 6))
            n, bins, patches = ax.hist(graphData, bins=30, alpha=0.85, color='#00c0ff', edgecolor='#00eaff', linewidth=1.2)
            highlight_value = 0
            for patch, left_side in zip(patches, bins[:-1]):
                if left_side <= highlight_value < left_side + (bins[1] - bins[0]):
                    patch.set_facecolor('orange')
            ax.set_facecolor('#1a1a1a')
            plt.style.use('dark_background')
            title = plt.title(f'Simulation Points Distribution for {" ".join(postPlayer.split("_"))}', fontsize=16, color="#F2F0EF", fontweight='bold')
            title.set_path_effects([path_effects.Stroke(linewidth=3, foreground='black'), path_effects.Normal()])
            plt.xlabel('Simulated Points', fontsize=14, color='lightgrey')
            plt.ylabel('Frequency', fontsize=14, color='lightgrey')
            plt.axvline(x=np.mean(graphData), color='red', linestyle='--', linewidth=3.5, label=f'Mean = {np.mean(graphData):.2f}')
            plt.axvline(x=row["Line"], color='green', linestyle='--', linewidth=3.5, label=f'Line = {row["Line"]}')
            plt.tick_params(axis='x', colors='lightgrey')
            plt.tick_params(axis='y', colors='lightgrey')
            plt.legend(facecolor='black', edgecolor='lightgrey', fontsize=12)
            plt.savefig(os.path.join("playerVisuals", f'{postPlayer}_Simulation_Distribution.png'), dpi=300, bbox_inches='tight')
            
            
    simulation_results = pd.DataFrame(results)
    return simulation_results

sheetName = "Calculations"
sh = sheet.worksheet(sheetName)
simdf = monteCarlo(sheetName)
insertFrame = simdf[["%Above", '%Below']]
insertFrame = [insertFrame.columns.values.tolist()] + insertFrame.values.tolist()
sh.batch_clear(["P4:Q154"])
sh.update(range_name="P4", values=insertFrame)
