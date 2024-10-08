import sqlite3

conn = sqlite3.connect('nba_ids.db')
c = conn.cursor()

c.execute("DELETE FROM ids_data")
conn.commit()
conn.close()