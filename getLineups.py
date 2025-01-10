import requests
from bs4 import BeautifulSoup
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os
import json
import unicodedata
import re


def regularize_name(name):
    name = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('utf-8')
    name = re.sub(r"[’'`]", "", name)
    name = re.sub(r"[-]", " ", name)
    name = re.sub(r"[^a-zA-Z\s]", "", name)
    name_parts = name.split()
    suffixes = {"jr", "sr", "ii", "iii", "iv", "v"}
    
    # Remove suffix if present
    if name_parts and name_parts[-1].lower() in suffixes:
        name_parts.pop()
    
    # Capitalize each name part properly
    name_parts = [part.capitalize() for part in name_parts]
    name = "_".join(name_parts)
    
    return name

def exceptions(team):
    if team == "CHA":
        return "CHO"
    elif team == "PHX":
        return "PHO"
    elif team == "BKN":
        return "BRK"
    else:
        return team

load_dotenv()
googleJSON = os.getenv('GOOGLE_CLOUD_SERVICE_ACCOUNT')
googleAccount = json.loads(googleJSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(googleAccount, scopes=scopes)
client = gspread.authorize(creds)
SheetID = os.getenv("Sheet_ID")
sheet = client.open_by_url(f'https://docs.google.com/spreadsheets/d/{SheetID}/edit#gid=478985565')
sh = sheet.worksheet("Lineups")

url = "https://www.rotowire.com/basketball/nba-lineups.php"

response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")

games = soup.find_all("div", class_="lineup__main")
teamNames = soup.find_all("div", class_="lineup__abbr")

lineups = []
baseURL = "https://www.rotowire.com"

for i, section in enumerate(games):
    visitName = "..."
    homeName = "!!!"
    if i * 2 + 1 < len(teamNames):
        visitName = teamNames[i*2].text
        homeName = teamNames[i*2+1].text

    visitingTeam = section.find("ul", class_="lineup__list is-visit")
    homeTeam = section.find("ul", class_="lineup__list is-home")

    if visitingTeam is None or homeTeam is None:
        continue

    def extract_team_data(team_section):
        positions = {'PG': '', 'SG': '', 'SF': '', 'PF': '', 'C': ''}
        players = team_section.find_all("li", class_="lineup__player")
        for player in players:
            position = player.find("div", class_="lineup__pos").get_text(strip=True)
            pLink = player.find("a")
            pUrl = baseURL + pLink['href']
            pName = " ".join([j.capitalize() for j in pUrl.split("/")[-1].split("-")[0:-1]])
            print(pName)
            pName = regularize_name(pName)
            if position in positions and positions[position] == "":
                positions[position] = pName
        return list(positions.values())

    visitingPlayers = extract_team_data(visitingTeam)
    print(visitingPlayers)
    homePlayers = extract_team_data(homeTeam)

    lineups.append([visitName] + visitingPlayers)
    lineups.append([homeName] + homePlayers)

df = pd.DataFrame(lineups, columns=['Team', 'PG', 'SG', 'SF', 'PF', 'C'])
df["Team"] = df["Team"].apply(exceptions)

values = [df.columns.values.tolist()] + df.values.tolist()

sh.batch_clear(["B2:F31"])
sh.update(range_name="A1", values=values)

print(df)
