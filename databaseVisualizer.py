import requests
from bs4 import BeautifulSoup
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import os
import json
import random
import sqlite3

load_dotenv()
googleJSON = os.getenv('GOOGLE_CLOUD_SERVICE_ACCOUNT')
googleAccount = json.loads(googleJSON)
scopes = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_info(googleAccount, scopes=scopes)
client = gspread.authorize(creds)
SheetID = os.getenv("Sheet_ID")
sheet = client.open_by_url(f'https://docs.google.com/spreadsheets/d/{SheetID}/edit#gid=478985565')

def fetchData(dbName, query):
    dataBase = sqlite3.connect(dbName)
    cursor = dataBase.cursor()
    cursor.execute(query)
    data = cursor.fetchall() 
    dataBase.close()
    return data

db = 'nba_ids.db'
query = 'SELECT * FROM homeAwayPlayer;'
sheetInsert = "homeAwayPlayer"


sh = sheet.worksheet(sheetInsert)
data = fetchData(db, query)
sh.update("B2", data)

