from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
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
from datetime import datetime, timedelta
import gc


load_dotenv()
googleJSON = os.getenv('GOOGLE_CLOUD_SERVICE_ACCOUNT')
googleAccount = json.loads(googleJSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(googleAccount, scopes=scopes)
client = gspread.authorize(creds)
SheetID = os.getenv("Sheet_ID")
sheet = client.open_by_url(f'https://docs.google.com/spreadsheets/d/{SheetID}/edit#gid=478985565')
sh = sheet.worksheet("Calculations")

# Set up database connection
dataBase = sqlite3.connect('nba_ids.db')
base = dataBase.cursor()

# Create tracking tables if they don't exist
base.execute('''CREATE TABLE IF NOT EXISTS processed_players
            (team_index INTEGER, player_name TEXT, 
            processed_timestamp TEXT, PRIMARY KEY (team_index, player_name))''')
base.execute('''CREATE TABLE IF NOT EXISTS processing_state
            (team_index INTEGER PRIMARY KEY, last_player_index INTEGER,
            timestamp TEXT)''')
dataBase.commit()

def regularize_name(name):
    name = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode('utf-8')
    name = re.sub(r"[''`]", "", name)
    name = re.sub(r"[-]", " ", name)
    name = re.sub(r"[^a-zA-Z\s]", "", name)
    name_parts = name.split()
    suffixes = {"jr", "sr", "ii", "iii", "iv", "v"}
    if name_parts and name_parts[-1].lower() in suffixes:
        name_parts.pop()
    name_parts = [part.capitalize() for part in name_parts]
    name = "_".join(name_parts)
    
    return name

# Utility functions for tracking progress
def get_processed_players(team_index):
    """Get list of already processed players for a team"""
    try:
        base.execute("SELECT player_name FROM processed_players WHERE team_index = ?", (team_index,))
        results = base.fetchall()
        return {result[0] for result in results}
    except Exception as e:
        print(f"Error getting processed players: {str(e)}")
        return set()

def mark_player_as_processed(team_index, player_name):
    """Mark a player as successfully processed"""
    try:
        timestamp = datetime.now().isoformat()
        base.execute('''INSERT OR REPLACE INTO processed_players
                    (team_index, player_name, processed_timestamp) VALUES (?, ?, ?)''',
                    (team_index, player_name, timestamp))
        dataBase.commit()
    except Exception as e:
        print(f"Error marking player as processed: {str(e)}")

def mark_processing_state(team_index, last_index):
    """Save current processing state"""
    try:
        timestamp = datetime.now().isoformat()
        base.execute('''INSERT OR REPLACE INTO processing_state
                    (team_index, last_player_index, timestamp) VALUES (?, ?, ?)''',
                    (team_index, last_index, timestamp))
        dataBase.commit()
    except Exception as e:
        print(f"Error marking processing state: {str(e)}")

def get_last_player_index(team_index):
    """Get the last processed player index for resuming"""
    try:
        base.execute("SELECT last_player_index FROM processing_state WHERE team_index = ?", (team_index,))
        result = base.fetchone()
        if result:
            return result[0]
        return None
    except Exception as e:
        print(f"Error getting last player index: {str(e)}")
        return None

def create_driver():
    """Create a new driver with optimized memory settings"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--blink-settings=imagesEnabled=false')
    # Additional memory optimization flags
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-default-apps')
    options.add_argument('--mute-audio')
    options.add_argument('--aggressive-cache-discard')
    options.add_argument('--disable-application-cache')
    options.add_argument('--disable-offline-load-stale-cache')
    options.add_argument('--disk-cache-size=0')
    options.add_argument('--media-cache-size=0')
    options.add_argument('--memory-cache-size=16384')  # Limit memory cache
    options.add_argument('--js-flags=--max-old-space-size=1024')  # Limit JS heap
    return webdriver.Chrome(options=options)

# Initialize driver
driver = create_driver()
url = "https://www.pbpstats.com/possession-finder/nba"
driver.get(url)
wait = WebDriverWait(driver, 10)

def restart_browser_session():
    """Restart the browser to free memory while keeping variables"""
    global driver, wait
    
    # Clean up old driver
    driver.quit()
    
    # Force garbage collection
    gc.collect()
    
    # Wait a moment to ensure resources are freed
    time.sleep(3)
    
    # Create new driver with same settings
    driver = create_driver()
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    
    # Set up initial page
    time.sleep(2)
    button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Add Player Filter"]')))
    driver.execute_script("arguments[0].click();", button)
    button2 = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Add Date Filter"]')))
    driver.execute_script("arguments[0].click();", button2)
    
    # Set date range
    getDateRange(yestermonth, yesterday, today)
    
    print("Browser restarted to free memory")

time.sleep(2)
button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Add Player Filter"]')))
driver.execute_script("arguments[0].click();", button)
button2 = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Add Date Filter"]')))
driver.execute_script("arguments[0].click();", button2)

today = datetime.today()
lowerBoundDate = today - timedelta(days=40)
yesterday = lowerBoundDate.day
yestermonth = ((today.year * 12 + today.month) - (lowerBoundDate.year * 12 + lowerBoundDate.month))

def getDateRange(yestermonth, yesterday, today):
    d1 = wait.until(EC.element_to_be_clickable((By.XPATH, '(//div[@class="vdp-datepicker"])')))
    d1.click()
    bb = wait.until(EC.element_to_be_clickable((By.XPATH, '(//span[@class="prev"])')))
    for i in range(yestermonth):
        bb.click()

    db = wait.until(EC.element_to_be_clickable((By.XPATH, f'(//span[contains(@class, "cell day") and contains(., "{yesterday}")])')))
    db.click()

    d2 = wait.until(EC.element_to_be_clickable((By.XPATH, '(//div[@class="vdp-datepicker"])[2]')))
    d2.click()
    db2 = wait.until(EC.element_to_be_clickable((By.XPATH, f'(//span[contains(@class, "cell day today")])')))
    db2.click()
    
getDateRange(yestermonth, yesterday, today)

teams = wait.until(EC.presence_of_all_elements_located((By.XPATH, '(//div[@class="multiselect"])[3]//ul[@class="multiselect__content"]//li[@class="multiselect__element"]//span[@class="multiselect__option"]//span')))
print(len(teams))

# Main loop - Process teams
try:
    for team_idx in range(0, 30):
        # Get the last processed player index for this team
        last_player_idx = get_last_player_index(team_idx)
        processed_players = get_processed_players(team_idx)
        
        # Select team
        if team_idx > 0:
            team = teams[team_idx - 1]
            driver.execute_script("arguments[0].scrollIntoView();", team)
            driver.execute_script("arguments[0].click();", team)
            time.sleep(2)
            
        # Set up player selection
        nPlayers = wait.until(EC.presence_of_element_located((By.XPATH, '(//div[@class="multiselect__content-wrapper" and contains(., "1 of")])')))
        nPlayers = nPlayers.find_elements(By.TAG_NAME, 'span')
        driver.execute_script("arguments[0].click();", nPlayers[2])
        dropdowns = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "multiselect__content-wrapper"))
        )
        dd = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "multiselect__select")))
        dd[9].click()
        playersDropdown = dropdowns[9]
        
        # Get list of players
        players = playersDropdown.find_elements(By.TAG_NAME, "li")[:-2]
        
        # Determine the start index (for resuming)
        start_idx = last_player_idx if last_player_idx is not None else len(players) - 1
        print(f"Processing team {team_idx}, starting at player index {start_idx}")
        
        # Counter for batch processing to manage memory
        player_counter = 0
        batch_size = 10
        
        # Process players
        for i in range(start_idx, -1, -1):
            try:
                # Get player name and check if already processed
                player_name = players[i].get_attribute("textContent").strip()
                normalized_name = regularize_name(player_name)
                
                if normalized_name in processed_players:
                    print(f"Skipping already processed player: {normalized_name}")
                    continue
                
                # Process player
                name = player_name
                players[i].click()
                pos = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Get Possessions"]')))
                driver.execute_script("arguments[0].click();", pos)
                rbs = WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "custom__remove")))
                if len(rbs) > 2:
                    rbs[1].click()
                rbs[1].click()
                
                # Memory optimization - clear cookies after each player 
                driver.delete_all_cookies()
                
                try: 
                    tables = WebDriverWait(driver, 20).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "vgt-wrap")))
                    if len(tables) > 1: 
                        table = tables[1]
                        headers = table.find_elements(By.CSS_SELECTOR, "thead th")
                        columns = [header.text.strip() for header in headers if header.text.strip()]
                        rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
                        data = []
                        for row in rows:
                            cells = row.find_elements(By.CSS_SELECTOR, "td")
                            data.append([cell.text.strip() for cell in cells])
                            
                        df = pd.DataFrame(data, columns=columns)
                        df['Name\nSort table by Name in ascending order'] = df['Name\nSort table by Name in ascending order'].apply(regularize_name)
                        name = regularize_name(name)
                        base.execute(f"DROP TABLE IF EXISTS {name}On")
                        base.execute(f'''CREATE TABLE IF NOT EXISTS {name}On
                                    (Player TEXT, Name TEXT, possessions INTEGER, FG2M INTEGER, FG2A INTEGER, TFGp REAL,
                                    FG3M INTEGER, FG3A INTEGER, ThFGp REAL, idcThFGp REAL, FTM INTEGER, AST2PTS INTEGER,
                                    uAST2PTS INTEGER, AST3PTS INTEGER, uAST3PTS INTEGER, TPAp REAL, idcTPAp REAL,
                                    ThPAp REAL, thPAr REAL, Qual REAL, eFG REAL, TS REAL, PUT INTEGER, FG2AB INTEGER,
                                    FG2ABp REAL, FG3AB INTEGER, FG3ABp REAL, Usage Real)''')
                        dataBase.commit()
                        for _, row in df.iterrows():
                            base.execute(f'''
                                INSERT OR REPLACE INTO {name}On (
                                    Player, Name, possessions, FG2M, FG2A, TFGp, FG3M, FG3A, ThFGp, idcThFGp, FTM, AST2PTS,
                                    uAST2PTS, AST3PTS, uAST3PTS, TPAp, idcTPAp, ThPAp, thPAr, Qual, eFG, TS, PUT, FG2AB,
                                    FG2ABp, FG3AB, FG3ABp, Usage
                                )
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', tuple(row))
                        dataBase.commit()
                        print(name)
                        
                        # Mark player as processed
                        mark_player_as_processed(team_idx, name)
                except TimeoutException:
                    print(f"No data for {players[i].get_attribute('textContent')}")
                except WebDriverException:
                    print(f"Error encountered: {players[i].get_attribute('textContent')}. Retrying...")
                
                # Save current progress
                mark_processing_state(team_idx, i)
                
                # Increment counter and check if we need to restart browser
                player_counter += 1
                if player_counter >= batch_size:
                    # Force garbage collection
                    gc.collect()
                    
                    # Restart browser to free memory
                    restart_browser_session()
                    
                    # Need to reselect team after restart
                    teams = wait.until(EC.presence_of_all_elements_located((By.XPATH, '(//div[@class="multiselect"])[3]//ul[@class="multiselect__content"]//li[@class="multiselect__element"]//span[@class="multiselect__option"]//span')))
                    team = teams[team_idx - 1]
                    driver.execute_script("arguments[0].scrollIntoView();", team)
                    driver.execute_script("arguments[0].click();", team)
                    time.sleep(2)
                    
                    # Reset player selection
                    nPlayers = wait.until(EC.presence_of_element_located((By.XPATH, '(//div[@class="multiselect__content-wrapper" and contains(., "1 of")])')))
                    nPlayers = nPlayers.find_elements(By.TAG_NAME, 'span')
                    driver.execute_script("arguments[0].click();", nPlayers[2])
                    dropdowns = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CLASS_NAME, "multiselect__content-wrapper"))
                    )
                    dd = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.CLASS_NAME, "multiselect__select")))
                    dd[9].click()
                    playersDropdown = dropdowns[9]
                    players = playersDropdown.find_elements(By.TAG_NAME, "li")[:-2]
                    player_counter = 0
            
            except StaleElementReferenceException:
                print(f"Stale element encountered for player at index {i}. Retrying...")
                
                # Restart browser to fix stale elements
                restart_browser_session()
                
                # Reselect team
                teams = wait.until(EC.presence_of_all_elements_located((By.XPATH, '(//div[@class="multiselect"])[3]//ul[@class="multiselect__content"]//li[@class="multiselect__element"]//span[@class="multiselect__option"]//span')))
                team = teams[team_idx - 1]
                driver.execute_script("arguments[0].scrollIntoView();", team)
                driver.execute_script("arguments[0].click();", team)
                time.sleep(2)
                
                # Reset player selection
                nPlayers = wait.until(EC.presence_of_element_located((By.XPATH, '(//div[@class="multiselect__content-wrapper" and contains(., "1 of")])')))
                nPlayers = nPlayers.find_elements(By.TAG_NAME, 'span')
                driver.execute_script("arguments[0].click();", nPlayers[2])
                dropdowns = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "multiselect__content-wrapper"))
                )
                dd = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "multiselect__select")))
                dd[9].click()
                playersDropdown = dropdowns[9]
                players = playersDropdown.find_elements(By.TAG_NAME, "li")[:-2]
        
except Exception as e:
    print(f"Error: {str(e)}")
finally:
    # Close the driver in all cases
    try:
        driver.quit()
    except:
        pass
    
    print("Script finished")


