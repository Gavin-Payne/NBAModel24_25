import sqlite3

dataBase = sqlite3.connect('nba_ids.db')
base = dataBase.cursor()

base.execute("DELETE FROM homeAway")
dataBase.commit()
dataBase.close()