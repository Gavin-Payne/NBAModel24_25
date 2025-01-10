from selenium import webdriver
from bs4 import BeautifulSoup
import re
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os
import json
import unicodedata

load_dotenv()
googleJSON = os.getenv('GOOGLE_CLOUD_SERVICE_ACCOUNT')
googleAccount = json.loads(googleJSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(googleAccount, scopes=scopes)
client = gspread.authorize(creds)
SheetID = os.getenv("Sheet_ID")
sheet = client.open_by_url(f'https://docs.google.com/spreadsheets/d/{SheetID}/edit#gid=478985565')

exceptions = {"Taurean_Waller_Prince": "Taurean_Prince"}

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
    if name in exceptions: name = exceptions[name]
    return name

sh = sheet.worksheet("minutesProjections")


driver = webdriver.Chrome()

driver.get('https://www.sportsline.com/nba/expert-projections/simulation/')

source = driver.page_source
soup = BeautifulSoup(source, 'html.parser')
table = soup.find('table', class_='sc-36594fa2-7')

headers = [header.text.strip() for header in table.find_all('th')]
rows = table.find('tbody').find_all('tr')
data = []
for row in rows:
    cells = row.find_all('td')
    data.append([cell.text.strip() for cell in cells])
df = pd.DataFrame(data, columns=headers)
df.to_csv('output.csv', index=False)
driver.quit()

df["PLAYER"] = df['PLAYER'].apply(regularize_name)
df = [df.columns.values.tolist()] + df.values.tolist()
sh.clear()
sh.update("B2", df)
