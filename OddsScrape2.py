import gspread
from google.oauth2.service_account import Credentials
import requests
import json
import os
from dotenv import load_dotenv
import unicodedata
import re
from collections import defaultdict

load_dotenv()

google_cloud_service_account_json = os.getenv('GOOGLE_CLOUD_SERVICE_ACCOUNT')

if google_cloud_service_account_json:
    google_cloud_service_account = json.loads(google_cloud_service_account_json)
else:
    raise ValueError("GOOGLE_CLOUD_SERVICE_ACCOUNT environment variable not set")

scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(google_cloud_service_account, scopes=scopes)
client = gspread.authorize(creds)

API_Key = os.getenv("API_Key")
Sheet_ID = os.getenv("Sheet_ID")

def regularize_name(name):
    name = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('utf-8')
    name = re.sub(r"[’'`]", "", name)
    name = re.sub(r"[-]", " ", name)
    name = re.sub(r"[^a-zA-Z\s]", "", name)
    name_parts = name.split()
    suffixes = {"jr", "sr", "ii", "iii", "iv", "v"}
    if name_parts and name_parts[-1].lower() in suffixes:
        name_parts.pop()
    name_parts = [part.capitalize() for part in name_parts]
    name = "_".join(name_parts)
    
    return name

def get_ids():
    response = requests.get(f'https://api.the-odds-api.com/v4/sports/basketball_nba/events?apiKey={API_Key}')
    return response.json()

game_ids = [game['id'] for game in get_ids()]

def get_odds(id, market):
    response = requests.get(f"https://api.the-odds-api.com/v4/sports/basketball_nba/events/{id}/odds?apiKey={API_Key}&regions=us2&markets={market}&oddsFormat=american")
    if response.status_code == 200:
        return response.json()
    else:
        print('Error:', response.status_code)
        return None

def flatten_data(data):
    flat_data = defaultdict(list)
    for bookmaker in data['bookmakers']:
        if bookmaker["key"] == 'fliff': 
            for market in bookmaker['markets']:
                for outcome in market['outcomes']:
                    name = regularize_name(outcome['description'])
                    flat_data[name].append(outcome['point'])
                    flat_data[name].append(outcome['price'])
    return flat_data

def update_worksheet(sheet_name, market):
    sheet = client.open_by_url(f'https://docs.google.com/spreadsheets/d/{Sheet_ID}/edit#gid=478985565').worksheet(sheet_name)
    sheet.batch_clear(["B3:F"]) 
    
    cumulative = []

    for game_id in game_ids:
        data = get_odds(game_id, market)
        if data:
            insertdata = flatten_data(data)
            flattened_data = [[n] + v for n, v in insertdata.items()] 
            cumulative.extend(flattened_data)

    if cumulative:
        sheet.update(range_name="B3", values=cumulative)

update_worksheet("pointOdds", "player_points_q1") 


