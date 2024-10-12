import sqlite3

dataBase = sqlite3.connect('nba_ids.db')
base = dataBase.cursor()

# "DELETE FROM homeAway" 
base.execute("DROP TABLE IF EXISTS homeAwayPlayer")
dataBase.commit()
dataBase.close()

