import sqlite3
from tabulate import tabulate

dataBase = sqlite3.connect('nba_ids.db')
base = dataBase.cursor()
name = "Jarred_Vanderbilt"

query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{name}On';"
base.execute(query)
if base.fetchone():
    data_query = f"SELECT * FROM {name}On;"
    base.execute(data_query)
    rows = base.fetchall()
    columns = [description[0] for description in base.description]
    print(f"Data from table '{name}On':\n")
    print(tabulate(rows, headers=columns, tablefmt="fancy_grid"))
else:
    print(f"Table '{name}On' does not exist.")

dataBase.close()
