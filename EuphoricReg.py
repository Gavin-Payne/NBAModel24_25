from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import pandas as pd
from bs4 import BeautifulSoup
import requests
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os
import json
import random
import sqlite3
import numpy as np
import re
import unicodedata
import time

load_dotenv()
googleJSON = os.getenv('GOOGLE_CLOUD_SERVICE_ACCOUNT')
googleAccount = json.loads(googleJSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(googleAccount, scopes=scopes)
client = gspread.authorize(creds)
SheetID = os.getenv("Sheet_ID")
sheet = client.open_by_url(f'https://docs.google.com/spreadsheets/d/{SheetID}/edit#gid=478985565')
sh = sheet.worksheet("Calculations")


def regularize_name(name):
    name = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('utf-8')
    name = re.sub(r"[’'`]", "", name)
    name = re.sub(r"[-]", " ", name)
    name = re.sub(r"[^a-zA-Z\s]", "", name)
    name = name.split()
    name = "_".join(name)
    
    return name

#Open link and wait for it to load
driver = webdriver.Chrome()
url = "https://www.pbpstats.com/possession-finder/nba"
driver.get(url)
wait = WebDriverWait(driver, 10)

dataBase = sqlite3.connect('nba_ids.db')
base = dataBase.cursor()

time.sleep(2)
button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Add Player Filter"]')))
driver.execute_script("arguments[0].click();", button)



for i in range(2, 30):
    nPlayers = wait.until(EC.presence_of_element_located((By.XPATH, '(//div[@class="multiselect__content-wrapper" and contains(., "1 of")])')))
    nPlayers = nPlayers.find_elements(By.TAG_NAME, 'span')
    driver.execute_script("arguments[0].click();", nPlayers[2])
    if i > 0:
        teams = wait.until(EC.element_to_be_clickable((By.XPATH, '(//div[@class="multiselect"])[3]')))
        driver.execute_script("arguments[0].click();", teams)
        time.sleep(2)

        teams = wait.until(EC.presence_of_all_elements_located((By.XPATH, '(//div[@class="multiselect"])[3]//ul[@class="multiselect__content"]//li[@class="multiselect__element"]//span[@class="multiselect__option"]//span')))
        team = teams[i]

        driver.execute_script("arguments[0].scrollIntoView();", team)
        driver.execute_script("arguments[0].click();", team)
        time.sleep(2)
    dropdowns = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "multiselect__content-wrapper")))
    playersDropdown = dropdowns[9]
    players = playersDropdown.find_elements(By.CSS_SELECTOR, "li.multiselect__element span.multiselect__option")
    for player in players:
        driver.execute_script("arguments[0].scrollIntoView(true);", player)
        name = player.find_element(By.TAG_NAME, "span")
        print(name.text.strip())
    for i in range(len(players)):
        try:
            players = playersDropdown.find_elements(By.CSS_SELECTOR, "li.multiselect__element span.multiselect__option")
            driver.execute_script("arguments[0].click();", players[i])
            pos = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Get Possessions"]')))
            driver.execute_script("arguments[0].click();", pos)
            remove_buttons = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "custom__remove")))
            if len(remove_buttons) > 2:
                remove_buttons[1].click()
            remove_buttons[1].click()
            try: 
                tables = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "vgt-wrap")))

                if len(tables) > 1: 
                    table = tables[1]

                    # Extract headers
                    headers = table.find_elements(By.CSS_SELECTOR, "thead th")
                    columns = [header.text.strip() for header in headers if header.text.strip()]  # Only non-empty headers
                    rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
                    data = []
                    for row in rows:
                        cells = row.find_elements(By.CSS_SELECTOR, "td")
                        data.append([cell.text.strip() for cell in cells])
                        
                    df = pd.DataFrame(data, columns=columns)
                    
                    name = players[i].find_element(By.TAG_NAME, "span")
                    name = regularize_name(name.text)
                    base.execute(f'''CREATE TABLE IF NOT EXISTS {name}OnOff
                                (Player TEXT, Name TEXT, possessions INTEGER, FG2M INTEGER, FG2A INTEGER, TFGp REAL,
                                FG3M INTEGER, FG3A INTEGER, ThFGp REAL, idcThFGp REAL, FTM INTEGER, AST2PTS INTEGER,
                                uAST2PTS INTEGER, AST3PTS INTEGER, uAST3PTS INTEGER, TPAp REAL, idcTPAp REAL,
                                ThPAp REAL, thPAr REAL, Qual REAL, eFG REAL, TS REAL, PUT INTEGER, FG2AB INTEGER,
                                FG2ABp REAL, FG3AB INTEGER, FG3ABp REAL, Usage Real)''')
                    dataBase.commit()
                    for _, row in df.iterrows():
                        base.execute(f'''
                            INSERT OR REPLACE INTO {name}OnOff (
                                Player, Name, possessions, FG2M, FG2A, TFGp, FG3M, FG3A, ThFGp, idcThFGp, FTM, AST2PTS,
                                uAST2PTS, AST3PTS, uAST3PTS, TPAp, idcTPAp, ThPAp, thPAr, Qual, eFG, TS, PUT, FG2AB,
                                FG2ABp, FG3AB, FG3ABp, Usage
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', tuple(row))
                    dataBase.commit()
                    print(name)
            except TimeoutException:
                print(f"No data for {players[i].text}")
                
        except StaleElementReferenceException:
            print(f"Stale element encountered for player at index {i}. Retrying...")
            
        