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
    df = pd.DataFrame(sh.get("A5:M154"))
    df.columns = ["Usage", 'Name', 'Opp', "H/A", "Minutes", '2PA', '2P%', '3PA', '3P%', 'FTA', 'FT%', "Mean", "Line"]
    
    df[["Usage", '2PA', '2P%', '3PA', '3P%', 'FTA', 'FT%', 'Mean', 'Line']] = df[['Usage', '2PA', '2P%', '3PA', '3P%', 'FTA', 'FT%', 'Mean', 'Line']].apply(pd.to_numeric, errors='coerce')
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
        
        twoPA, dectwoPA = row['2PA'], row['2PA']  - row['2PA'] // 1
        twoPercent = float(row['2P%'])
        threePA, decthreePA = row['3PA'], row['3PA'] - row['3PA'] // 1
        threePercent = float(row['3P%'])
        fta, decFTA = row['FTA'] / float(row['FT%']), row['FTA'] / float(row['FT%']) - row['FTA'] / float(row['FT%']) // 1
        pos = round(row["Mean"], 0)
        ftPercent = float(row['FT%'])

        simPoints, track = [], []
        nsims = 10000
        # nsims simmies for each player
        for _ in range(nsims):
            twoPAu = np.random.binomial(n = pos, p=twoPA / pos)
            threePAu = np.random.binomial(n = pos, p=threePA / pos)
            ftau = np.random.binomial(n = pos, p= fta / pos)
            tPointMakes = np.random.binomial(n=twoPAu, p=twoPercent)
            thPointMakes = np.random.binomial(n=threePAu, p=threePercent)
            track.append(thPointMakes)
            ftMakes = np.random.binomial(n=ftau, p=ftPercent)
            points = (2 * tPointMakes) + (3 * thPointMakes) + (1 * ftMakes)
            simPoints.append(points)

        line = row['Line']
        countAbove = sum(np.array(simPoints) > line)
        percentAbove = countAbove / nsims
        
        results.append({
            'Name': row['Name'],
            'Mean Simulated Points': np.mean(simPoints),
            'Line': row['Line'],  
            '%Above' : percentAbove,
            "%Below" : 1- percentAbove
        })
    
    
        graphData = []
        
        postPlayer = "Paul_George"
        if row["Name"] == postPlayer:
            graphData = simPoints
            print(np.mean(track))
        
        if graphData:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Calculate the bin edges with a width of 1
            min_val = np.floor(min(graphData))
            max_val = np.ceil(max(graphData))
            bins = np.arange(min_val, max_val + 1, 1)  # Create bins with width of 1

            n, bins, patches = ax.hist(graphData, bins=bins, alpha=0.85, color='#8c54fc', edgecolor='#595959', linewidth=1.0)

            pivot = row["Line"]
            highlight_value = 0

            for patch, left_side in zip(patches, bins[:-1]):
                bar_mid = left_side + (bins[1] - bins[0]) / 2
                if percentAbove > 0.5:
                    if bar_mid <= pivot:
                        patch.set_facecolor('#FF4500')  # Muted red for below pivot
                    else:
                        patch.set_facecolor('#32CD32')  # Muted green for above pivot
                else:
                    if bar_mid >= pivot:
                        patch.set_facecolor('#FF4500')  # Muted red for above pivot
                    else:
                        patch.set_facecolor('#32CD32')  # Muted green for below pivot

            ax.set_facecolor('#1E1E1E')  # Dark gray background for dark theme
            plt.style.use('dark_background')  # Use the default dark style for Matplotlib

            title = plt.title(
                f'{" ".join(postPlayer.split("_"))}',
                fontsize=18,
                color="#FFFFFF",
                fontweight='bold',
                fontname='Arial'
            )
            title.set_path_effects([path_effects.Stroke(linewidth=1.5, foreground='#000000'),
                                    path_effects.Normal()])

            plt.xlabel('Points', fontsize=14, color='#E0E0E0', fontname='Arial')
            plt.ylabel('# Simulations', fontsize=14, color='#E0E0E0', fontname='Arial')

            plt.axvline(x=np.mean(graphData), color='#1E90FF', linestyle='--', linewidth=2.0, label=f'Mean = {np.mean(graphData):.2f}')
            plt.axvline(x=pivot, color='#FFD700', linestyle='-', linewidth=3.0, label=f'Line = {row["Line"]}')

            plt.tick_params(axis='x', colors='#D3D3D3')
            plt.tick_params(axis='y', colors='#D3D3D3')

            plt.legend(loc='upper left', facecolor='#333333', edgecolor='#666666', fontsize=12)

            # Save the figure
            plt.savefig(os.path.join("playerVisuals", f'{postPlayer}_Simulation_Distribution.png'))






            
            
    simulation_results = pd.DataFrame(results)
    return simulation_results

sheetName = "Calculations"
sh = sheet.worksheet(sheetName)
simdf = monteCarlo(sheetName)
insertFrame = simdf[["%Above", '%Below']]
insertFrame = [insertFrame.columns.values.tolist()] + insertFrame.values.tolist()
sh.batch_clear(["P4:Q154"])
sh.update(range_name="P4", values=insertFrame)
