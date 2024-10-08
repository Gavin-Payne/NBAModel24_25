import sqlite3

# Connect to the SQLite database
conn = sqlite3.connect('nba_ids.db')
c = conn.cursor()

# Query all data from the table
c.execute("SELECT * FROM ids_data")

# Fetch all rows
rows = c.fetchall()

# Display the data
for row in rows:
    print(row)

# Close the connection
conn.close()
