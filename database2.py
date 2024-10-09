import requests
from bs4 import BeautifulSoup
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os
import json
import random

load_dotenv()
googleJSON = os.getenv('GOOGLE_CLOUD_SERVICE_ACCOUNT')
googleAccount = json.loads(googleJSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(googleAccount, scopes=scopes)
client = gspread.authorize(creds)
SheetID = os.getenv("Sheet_ID")
sheet = client.open_by_url(f'https://docs.google.com/spreadsheets/d/{SheetID}/edit#gid=478985565')
sh = sheet.worksheet("perGame")

ids = sh.get("AF499:AF737")
names = sh.get("C499:C737")
worksheets = sheet.worksheets()
worksheets = [ws.title for ws in worksheets]
used = ["None"]

agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Safari/605.1.15',
    'Mozilla/5.0 (Linux; Android 10; SM-G960F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Mobile Safari/537.36',
    'Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Mobile Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (iPad; CPU OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:64.0) Gecko/20100101 Firefox/64.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:78.0) Gecko/20100101 Firefox/78.0',
    'Mozilla/5.0 (Windows NT 6.3; Trident/7.0; AS; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:68.0) Gecko/20100101 Firefox/68.0',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:45.0) Gecko/20100101 Firefox/45.0',
] # Chat GPT generated agents OpenAI. (2024). ChatGPT [Large language model]. https://chatgpt.com

def scrape_game_log(playerId, attempt=1):
    url = f"https://www.basketball-reference.com/players/s/{playerId}/gamelog/2024"
    incog = {'User-Agent': random.choice(agents)}
    response = requests.get(url, headers=incog)
    
    if response.status_code != 200:
        if attempt < 5:  # Retry up to 5 times
            return scrape_game_log(playerId, attempt + 1)
        return None, None

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', {'id': 'pgl_basic'})
    
    if table is None:
        return None, None

    headers = [th.getText() for th in table.find('thead').findAll('th')]
    rows = table.find('tbody').findAll('tr')

    data = []
    for row in rows:
        if 'thead' in row.get('class', []):
            continue
        cells = [cell.getText() for cell in row.findAll(['td', 'th'])]
        data.append(cells)
    
    return headers, data

def updateSheet(header, data, sheetName):
    sh = sheet.worksheet(sheetName)
    df = pd.DataFrame(data, columns=header)
    df = df.apply(pd.to_numeric)
    df = df[pd.to_numeric(df.iloc[:, 1]).notna()]
    df = df.iloc[:, 4:-2]
    df.fillna(0, inplace=True)
    
    dataOutput = [df.columns.tolist()] + df.values.tolist()
    sh.update(range_name="H2", values=dataOutput)

for i in range(len(ids)):
    id = ids[i][0]
    name = names[i][0]
    if id not in used:
        if name in worksheets:
            used.append(id)
            header, data = scrape_game_log(id)
            if header and data:
                updateSheet(header, data, name)
