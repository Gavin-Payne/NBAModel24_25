import requests
from bs4 import BeautifulSoup
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os
import json

load_dotenv()
googleJSON = os.getenv('GOOGLE_CLOUD_SERVICE_ACCOUNT')
googleAccount = json.loads(googleJSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(googleAccount, scopes=scopes)
client = gspread.authorize(creds)
SheetID = os.getenv("Sheet_ID")
sheet = client.open_by_url(f'https://docs.google.com/spreadsheets/d/{SheetID}/edit#gid=478985565')
sh = sheet.worksheet("Lineups")

# URL of the page to scrape
url = "https://www.rotowire.com/basketball/nba-lineups.php"

# Send a GET request to fetch the raw HTML content
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")

# Find the section containing the starting lineups
lineup_sections = soup.find_all("div", class_="lineup__main")
teamNames = soup.find_all("div", class_="lineup__abbr")

# Extract the data
lineups = []
base_url = "https://www.rotowire.com"  # Base URL to append to relative player links

for i, section in enumerate(lineup_sections):
    # Find visiting and home team abbreviations
    visit_team_abbr = "..."
    home_team_abbr = "!!!"
    if i * 2 + 1 < len(teamNames):
        visit_team_abbr = teamNames[i*2].text
        home_team_abbr = teamNames[i*2+1].text

    # Find visiting and home team lineups
    visit_team = section.find("ul", class_="lineup__list is-visit")
    home_team = section.find("ul", class_="lineup__list is-home")

    # Check if visiting and home teams were found
    if visit_team is None or home_team is None:
        continue

    # Function to extract player names from a team section
    def extract_team_data(team_section):
        positions = {'PG': '', 'SG': '', 'SF': '', 'PF': '', 'C': ''}
        player_items = team_section.find_all("li", class_="lineup__player")
        for player_item in player_items:
            position = player_item.find("div", class_="lineup__pos").get_text(strip=True)
            player_link = player_item.find("a")
            player_url = base_url + player_link['href']
            player_name = "_".join([j.capitalize() for j in player_url.split("/")[-1].split("-")[0:-1]])
            if position in positions:  # Store only if position is valid
                positions[position] = player_name
        return list(positions.values())

    # Extract players for both teams
    visiting_team_players = extract_team_data(visit_team)
    home_team_players = extract_team_data(home_team)

    # Append the lineups with team abbreviations
    lineups.append([visit_team_abbr] + visiting_team_players)
    lineups.append([home_team_abbr] + home_team_players)

# Convert the lineups into a DataFrame
df = pd.DataFrame(lineups, columns=['Team', 'PG', 'SG', 'SF', 'PF', 'C'])

# Update the Google Sheet with the new format
values = [df.columns.values.tolist()] + df.values.tolist()
sh.update("A1", values)

# Output the DataFrame
print(df)
