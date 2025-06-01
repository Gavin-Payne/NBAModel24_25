from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import pandas as pd
import re
import unicodedata
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os
import json

# Load environment variables
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

# Set up Selenium WebDriver
driver = webdriver.Chrome()
driver.get('https://www.nba.com/stats/players/traditional?LastNGames=3&Period=1&dir=A&sort=MIN')

wait = WebDriverWait(driver, 10)
dropdown = wait.until(EC.element_to_be_clickable((By.XPATH, "//select[@class='DropDown_select__4pIg9']")))
ActionChains(driver).move_to_element(dropdown).click().perform()

all_option = wait.until(EC.presence_of_element_located((By.XPATH, "//option[@value='-1']")))
all_option.click()

wait.until(EC.presence_of_element_located((By.XPATH, "//table[contains(@class, 'Crom_table__')]/tbody/tr")))

table = driver.find_element(By.XPATH, "//table[contains(@class, 'Crom_table__')]")
is_visible = driver.execute_script("return arguments[0].offsetParent !== null;", table)
if not is_visible:
    raise ValueError("The table is present but not visible!")

table_html = table.get_attribute('outerHTML')
soup = BeautifulSoup(table_html, 'html.parser')
table = soup.find('table')

headers = [header.text.strip() for header in table.find_all('th')]
rows = table.find('tbody').find_all('tr')
data = [[cell.text.strip() for cell in row.find_all('td')] for row in rows]

df = pd.DataFrame(data, columns=headers[:30])
df = df.set_index(df.columns[0])

driver.quit()

df["Player"] = df['Player'].apply(regularize_name)
df = [df.columns[:7].tolist()] + df.iloc[:, :7].values.tolist()
sh.clear()
sh.update(range_name="B2", values=df)

driver = webdriver.Chrome()
driver.get('https://www.nba.com/stats/players/traditional?LastNGames=3&Period=0&dir=A&sort=MIN')

wait = WebDriverWait(driver, 10)
dropdown = wait.until(EC.element_to_be_clickable((By.XPATH, "//select[@class='DropDown_select__4pIg9']")))
ActionChains(driver).move_to_element(dropdown).click().perform()

all_option = wait.until(EC.presence_of_element_located((By.XPATH, "//option[@value='-1']")))
all_option.click()

wait.until(EC.presence_of_element_located((By.XPATH, "//table[contains(@class, 'Crom_table__')]/tbody/tr")))

table = driver.find_element(By.XPATH, "//table[contains(@class, 'Crom_table__')]")
is_visible = driver.execute_script("return arguments[0].offsetParent !== null;", table)
if not is_visible:
    raise ValueError("The table is present but not visible!")

table_html = table.get_attribute('outerHTML')
soup = BeautifulSoup(table_html, 'html.parser')
table = soup.find('table')

headers = [header.text.strip() for header in table.find_all('th')]
rows = table.find('tbody').find_all('tr')
data = [[cell.text.strip() for cell in row.find_all('td')] for row in rows]

df = pd.DataFrame(data, columns=headers[:30])
df = df.set_index(df.columns[0])

driver.quit()

df["Player"] = df['Player'].apply(regularize_name)
df = [df.columns[:7].tolist()] + df.iloc[:, :7].values.tolist()
sh.update(range_name="J2", values=df)
