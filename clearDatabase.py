import sqlite3

dataBase = sqlite3.connect('nba_ids.db')
base = dataBase.cursor()

base.execute("DELETE FROM ids_data")
dataBase.commit()
dataBase.close()