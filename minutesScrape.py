from selenium import webdriver
from bs4 import BeautifulSoup
import re
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

def normalizeNames(name):
    name = '_'.join(re.findall(r"[\w']+", name))
    name = name.split("_")
    if name[-1] == "Jr":
        name = name[:-1]
    name = "_".join(name)
    return name

df["PLAYER"] = df['PLAYER'].apply(normalizeNames)
df = [df.columns.values.tolist()] + df.values.tolist()
sh.clear()
sh.update("B2", df)
