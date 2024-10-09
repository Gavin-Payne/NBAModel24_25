import sqlite3

dataBase = sqlite3.connect('nba_ids.db')
base = dataBase.cursor()
base.execute("SELECT * FROM ids_data")
rows = base.fetchall()

for row in rows:
    print(row)

dataBase.close()
