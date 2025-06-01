from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from bs4 import BeautifulSoup
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import unicodedata, re, time, os, json, sqlite3, gspread


#Google Sheets initialize
load_dotenv()
googleJSON = os.getenv('GOOGLE_CLOUD_SERVICE_ACCOUNT')
googleAccount = json.loads(googleJSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(googleAccount, scopes=scopes)
client = gspread.authorize(creds)
SheetID = os.getenv("Sheet_ID")
sheet = client.open_by_url(f'https://docs.google.com/spreadsheets/d/{SheetID}/edit#gid=478985565')

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

dataBase = sqlite3.connect('nba_ids.db')
base = dataBase.cursor()
base.execute('''CREATE TABLE IF NOT EXISTS ids_data
             (teamName TEXT, teamID TEXT, playerName TEXT, playerID TEXT)''')
dataBase.commit()

repeats = [regularize_name(" ".join((ws.title).split("_"))) for ws in sheet.worksheets()]



options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--blink-settings=imagesEnabled=false')

driver = webdriver.Chrome(options=options)
url = "https://www.pbpstats.com/on-off/nba/team?Season=2024-25&SeasonType=Regular%2BSeason&TeamId=1610612737&PlayerId=201988"
driver.get(url)
wait = WebDriverWait(driver, 10)

teams = wait.until(EC.presence_of_all_elements_located((By.XPATH, '(//div[@class="multiselect"])[3]//ul[@class="multiselect__content"]//li[@class="multiselect__element"]//span[@class="multiselect__option"]//span')))
print(len(teams))

for i in range(1, 30):
    if i > 0:
        team = teams[i - 1]
        driver.execute_script("arguments[0].scrollIntoView();", team)
        driver.execute_script("arguments[0].click();", team)
        time.sleep(2)

    currentURL = driver.current_url
    teamID = currentURL.split('TeamId=')[1].split('&')[0]

    playerDropdown = wait.until(EC.element_to_be_clickable((By.XPATH, '(//div[@class="multiselect"])[4]')))

    driver.execute_script("arguments[0].click();", playerDropdown)
    time.sleep(2)

    players = wait.until(EC.presence_of_all_elements_located((By.XPATH, '(//div[@class="multiselect"])[4]//ul[@class="multiselect__content"]//li[@class="multiselect__element"]//span[@class="multiselect__option"]//span')))
    
    print(len(players))
    for pi in range(len(players) + 1):
        if pi > 0:
            player = players[pi - 1]
            driver.execute_script("arguments[0].scrollIntoView();", player)
            driver.execute_script("arguments[0].click();", player)
            time.sleep(1)

        button = wait.until(EC.element_to_be_clickable((By.XPATH, '//button[text()="Get Stats"]')))
        driver.execute_script("arguments[0].click();", button)
        time.sleep(3)

        currentURL = driver.current_url
        playerID = currentURL.split('PlayerId=')[1]
        time.sleep(1)

        dropdownNames = wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'multiselect__single')))
        teamName = dropdownNames[1].text
        playerName = dropdownNames[2].text

        base.execute("SELECT * FROM ids_data WHERE teamID = ? AND playerID = ?", (teamID, playerID))
        result = base.fetchone()
        
        base.execute("INSERT INTO ids_data (teamName, teamID, playerName, playerID) VALUES (?, ?, ?, ?)",
                        (teamName, teamID, playerName, playerID))
        dataBase.commit()

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
        sheetName = regularize_name(playerName)
        print(sheetName)
        if sheetName not in repeats:
            nextSheet = sheet.add_worksheet(title=sheetName, rows="120", cols="30")

            nextSheet.batch_update([{
                                    'range': 'A1',
                                    'values': [[teamName]]  # team abbrev.
                                },
                                {
                                    'range': 'B2',
                                    'values': data_list  # dataframe
                                }])
        else:
            nextSheet = sheet.worksheet(sheetName)

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
