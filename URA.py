import sqlite3
import pandas as pd
import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os
import json
import random
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

dataBase = sqlite3.connect('nba_ids.db')
base = dataBase.cursor()

sh = sheet.worksheet("Calculations")
namesDf = pd.DataFrame(sh.get("B5:M154"))
namesDf.columns = ['Name', 'Opp', "H/A", "Minutes", '2PA', '2P%', '3PA', '3P%', 'FTA', 'FT%', "Mean", "Line"]

namesDf[['2PA', '2P%', '3PA', '3P%', 'FTA', 'FT%', 'Mean', 'Line']] = namesDf[['2PA', '2P%', '3PA', '3P%', 'FTA', 'FT%', 'Mean', 'Line']].apply(pd.to_numeric, errors='coerce')
namesDf = namesDf.loc[namesDf["Name"] != ""]
projPos = namesDf["Mean"].tolist()
teams = []

firstColumn, secondColumn, thirdColumn, usages = [], [], [], []
for i in range(len(namesDf) // 5):
    temp = []
    for j in range(i * 5, i * 5 + 5):
        temp.append(namesDf.loc[j, "Name"])
    teams.append(temp)
for ff, team in enumerate(teams):
    for fff, name in enumerate(team):
        if name == "PJ_Washington": name = "Pj_Washington"
        if name == "Alex_Sarr": name = "Alexandre_Sarr"
        query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{name}On';"
        base.execute(query)
        result1 = base.fetchone()
        query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{name}Off';"
        base.execute(query)
        result2 = base.fetchone()
        if result1 and result2:
            base.execute(f"SELECT * FROM {name}On")
            headers = [i[0] for i in base.description]
            rows = base.fetchall()
            players = [headers]
            for row in rows:
                players.append(list(row))
            Ondf = pd.DataFrame(players[1:], columns=players[0])
            Ondf.rename(columns={"Name": "Pos", "possessions": "Pts"}, inplace=True)
            Ondf.set_index("Player", inplace=True)

            base.execute(f"SELECT * FROM {name}On")
            headers = [i[0] for i in base.description]
            rows = base.fetchall()
            players = [headers]
            for row in rows:
                players.append(list(row))
            Offdf = pd.DataFrame(players[1:], columns=players[0])
            Offdf.rename(columns={"Name": "Pos", "possessions": "Pts"}, inplace=True)
            Offdf.set_index("Player", inplace=True)
            onPos, on2P, on3P, onFT, usagesTemp = [], [], [], [], []
            pPos, pUsage = int(Ondf.loc[name, "Pos"]), float(Ondf.loc[name, "Usage"])
            for col in ["TFGp", "ThFGp", "eFG", "TS"]:
                Ondf[col] = Ondf[col].str.rstrip('%').astype(float) / 100
                Offdf[col] = Offdf[col].str.rstrip('%').astype(float) / 100
            for teammate in team:
                if teammate != name:
                    query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{teammate}On';"
                    base.execute(query)
                    result1 = base.fetchone()
                    if not result1: continue
                    base.execute(f"SELECT * FROM {teammate}On")
                    headers = [i[0] for i in base.description]
                    rows = base.fetchall()
                    players = [headers]
                    for row in rows:
                        players.append(list(row))
                    tempOndf = pd.DataFrame(players[1:], columns=players[0])
                    tempOndf.rename(columns={"Name": "Pos", "possessions": "Pts"}, inplace=True)
                    tempOndf.set_index("Player", inplace=True)
                    
                    if name in tempOndf.index:
                        onPos.append(int(tempOndf.loc[name, "Pos"]))
                        on2P.append(float(tempOndf.loc[name, "FG2A"]))
                        on3P.append(float(tempOndf.loc[name, "FG3A"]))
                        onFT.append(float(tempOndf.loc[name, "FTM"]))
                        usagesTemp.append(float(tempOndf.loc[name, "Usage"]))
                        
            for t in Ondf.index:
                if t not in team:
                    query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{t}On';"
                    base.execute(query)
                    result1 = base.fetchone()
                    if not result1: continue
                    base.execute(f"SELECT * FROM {t}On")
                    headers = [i[0] for i in base.description]
                    rows = base.fetchall()
                    players = [headers]
                    for row in rows:
                        players.append(list(row))
                    tempOffdf = pd.DataFrame(players[1:], columns=players[0])
                    tempOffdf.rename(columns={"Name": "Pos", "possessions": "Pts"}, inplace=True)
                    tempOffdf.set_index("Player", inplace=True)
            tp = sum(onPos)
            if tp:
                tpapp, thpapp, ftmpp = sum(on2P) / tp, sum(on3P) / tp, sum(onFT) / tp
                posss = projPos[ff*5 + fff]
                firstColumn.append(tpapp * posss)
                secondColumn.append(thpapp * posss)
                thirdColumn.append(ftmpp * posss)
                usages.append(sum(usagesTemp) / 100 / len(usagesTemp))
            else:
                usages.append(-1)
                firstColumn.append(0)
                secondColumn.append(0)
                thirdColumn.append(0)
        else:
            firstColumn.append("N/A")
            secondColumn.append("N/A")
            thirdColumn.append("N/A")
            usages.append(-1)
            print(name)
            
firstColumn = [0 if str(x) == "N/A" or str(x) == "nan" else x for x in firstColumn]
secondColumn = [0 if str(x) == "N/A" or str(x) == "nan" else x for x in secondColumn]
thirdColumn = [0 if str(x) == "N/A" or str(x) == "nan" else x for x in thirdColumn]

for i in range(len(firstColumn) // 5):
    tu, c = 0, 0
    for j in range(i * 5, i * 5 + 5):
        hm = usages[j]
        if hm >= 0:
            tu += hm
            c += 1
    fac = {5:1, 4:.80, 3:.65}
    regFactor = tu / (fac[c] if fac.get(c) else 8)
    print(regFactor)
    if regFactor > 0:
        for j in range(i * 5, i * 5 + 5):
            if usages[j] >= 0:
                firstColumn[j] = firstColumn[j] / regFactor
                secondColumn[j] = secondColumn[j] / regFactor
                thirdColumn[j] = thirdColumn[j] / regFactor
            else:
                firstColumn[j] = "No data"
                secondColumn[j] = "No data"
                thirdColumn[j] = "No data"
                
sh.update(range_name="F5", values=[[x] for x in firstColumn]) 
sh.update(range_name="H5", values=[[x] for x in secondColumn])  
sh.update(range_name="J5", values=[[x] for x in thirdColumn])

