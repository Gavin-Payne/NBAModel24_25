import sqlite3

dataBase = sqlite3.connect('nba_ids.db')
base = dataBase.cursor()
name = "Miles_Bridges"
base.execute(f"SELECT * FROM {name}OnOff")
rows = base.fetchall()

for row in rows:
    print(row)

dataBase.close()
