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


#Google Sheets initialize
load_dotenv()
googleJSON = os.getenv('GOOGLE_CLOUD_SERVICE_ACCOUNT')
googleAccount = json.loads(googleJSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(googleAccount, scopes=scopes)
client = gspread.authorize(creds)
SheetID = os.getenv("Sheet_ID")
sheet = client.open_by_url(f'https://docs.google.com/spreadsheets/d/{SheetID}/edit#gid=478985565')


#Connect to the database that contains the information for players I have already scraped
dataBase = sqlite3.connect('nba_ids.db')
base = dataBase.cursor()
base.execute('''CREATE TABLE IF NOT EXISTS ids_data
             (teamName TEXT, teamID TEXT, playerName TEXT, playerID TEXT)''')
dataBase.commit()

#Open link and wait for it to load
driver = webdriver.Chrome()
url = "https://www.pbpstats.com/on-off/nba/team?Season=2023-24&SeasonType=Regular%2BSeason&TeamId=1610612762&PlayerId=201599"
driver.get(url)
wait = WebDriverWait(driver, 10)

for i in range(30):
    dropdown = wait.until(EC.element_to_be_clickable((By.XPATH, '(//div[@class="multiselect"])[3]')))

    driver.execute_script("arguments[0].click();", dropdown)
    time.sleep(2)

    teams = wait.until(EC.presence_of_all_elements_located((By.XPATH, '(//div[@class="multiselect"])[3]//ul[@class="multiselect__content"]//li[@class="multiselect__element"]//span[@class="multiselect__option"]//span')))
    team = teams[i]

    driver.execute_script("arguments[0].scrollIntoView();", team)
    driver.execute_script("arguments[0].click();", team)
    time.sleep(2)

    currentURL = driver.current_url
    teamID = currentURL.split('TeamId=')[1].split('&')[0]

    # Open the player dropdown (fourth dropdown)
    playerDropdown = wait.until(EC.element_to_be_clickable((By.XPATH, '(//div[@class="multiselect"])[4]')))

    driver.execute_script("arguments[0].click();", playerDropdown)
    time.sleep(2)

    # Get player options
    players = wait.until(EC.presence_of_element_located((By.XPATH, '(//div[@class="multiselect__content-wrapper"])[4]')))
    players = players.find_elements(By.TAG_NAME, 'span')

    for player in players:
        driver.execute_script("arguments[0].scrollIntoView();", player)
        driver.execute_script("arguments[0].click();", player)
        time.sleep(1)

        # Click the "Get Stats" button
        button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Get Stats"]')))
        driver.execute_script("arguments[0].click();", button)
        time.sleep(3)

        currentURL = driver.currentURL
        playerID = currentURL.split('PlayerId=')[1]
        time.sleep(1)

        # Get labels for database and spreadsheet
        dropdownNames = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'multiselect__single')))
        teamName = dropdownNames[1].text
        playerName = dropdownNames[2].text

        # Check if the player is in the database
        base.execute("SELECT * FROM ids_data WHERE teamID = ? AND playerID = ?", (teamID, playerID))
        result = base.fetchone()
        
        # If they aren't, add them to the database and google sheet
        if result is None:
            base.execute("INSERT INTO ids_data (teamName, teamID, playerName, playerID) VALUES (?, ?, ?, ?)",
                            (teamName, teamID, playerName, playerID))
            dataBase.commit()

            # Add new spreadsheet with table data
            webData = BeautifulSoup(driver.page_source, 'html.parser')
            table = webData.find('table')
            data = []
            headers = [th.text.strip() for th in table.find_all('th')]
            for row in table.find_all('tr')[1:]:
                columns = row.find_all('td')
                data.append([col.text.strip() for col in columns])

            df = pd.DataFrame(data, columns=headers)
            df.columns = ['Stat', "Stat value with player", "Stat value without player", "Difference"]
            data_list = [df.columns.values.tolist()] + df.values.tolist()
            sheetName = playerName.replace(" ", "_")
            if sheetName not in [ws.title for ws in sheet.worksheets()]:
                nextSheet = sheet.add_worksheet(title=sheetName, rows="120", cols="30")

                nextSheet.batch_update([{
                                        'range': 'A1',
                                        'values': [[teamName]]  # team abbrev.
                                    },
                                    {
                                        'range': 'B2',
                                        'values': data_list  # dataframe
                                    }])


driver.quit()
dataBase.close()
