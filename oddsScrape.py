from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from bs4 import BeautifulSoup
import time
import os
import json
import sqlite3
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import re


#Google Sheets initialize
load_dotenv()
googleJSON = os.getenv('GOOGLE_CLOUD_SERVICE_ACCOUNT')
googleAccount = json.loads(googleJSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(googleAccount, scopes=scopes)
client = gspread.authorize(creds)
SheetID = os.getenv("Sheet_ID")
sheet = client.open_by_url(f'https://docs.google.com/spreadsheets/d/{SheetID}/edit#gid=478985565')

df = pd.DataFrame(columns=["Name", 'Over', 'Over Odds', 'Under', 'Under Odds'])

#Open link and wait for it to load
driver = webdriver.Chrome()
urls = ["https://sportsbook.draftkings.com/leagues/basketball/nba?category=player-points&subcategory=points-o%2Fu",
        "https://sportsbook.draftkings.com/leagues/basketball/nba?category=player-rebounds&subcategory=rebounds-o%2Fu",
        "https://sportsbook.draftkings.com/leagues/basketball/nba?category=player-assists&subcategory=assists-o%2Fu"]
shs = ["pointOdds", "reboundOdds", "assistOdds"]

for i in range(len(urls)):
    
    df = pd.DataFrame(columns=df.columns)
    driver.get(urls[i])
    sh = sheet.worksheet(shs[i])
    
    wait = WebDriverWait(driver, 10)

    # Wait for page to load fully
    time.sleep(5)

    rows = driver.find_elements(By.XPATH, "//tbody[@class='sportsbook-table__body']/tr")

    for row in rows:
        try:
            player = row.find_element(By.XPATH, ".//span[@class='sportsbook-row-name']").text
            over_line = row.find_element(By.XPATH, ".//td[1]//span[@class='sportsbook-outcome-cell__line']").text
            over_odds = row.find_element(By.XPATH, ".//td[1]//span[contains(@class, 'sportsbook-odds')]").text
            under_line = row.find_element(By.XPATH, ".//td[2]//span[@class='sportsbook-outcome-cell__line']").text
            under_odds = row.find_element(By.XPATH, ".//td[2]//span[contains(@class, 'sportsbook-odds')]").text
            
            Name = '_'.join(re.findall(r"[\w']+", player))
            
            new_row = pd.Series({"Name": Name, 'Over': over_line, 
                    'Over Odds': over_odds, 'Under': under_line, 'Under Odds': under_odds})
            
            df = pd.concat([df, new_row.to_frame().T], ignore_index=True)

        except Exception as e:
            print(f"Error extracting data for row: {e}")

    insertTable = [df.columns.values.tolist()] + df.values.tolist()
    sh.clear()
    sh.batch_update([{
                        'range': 'B2',
                        'values': insertTable # team abbrev.
                        }])
# Close the browser
driver.quit()