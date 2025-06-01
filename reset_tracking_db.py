import sqlite3
import os

def reset_tracking_database():
    """
    Reset the database tracking tables to allow for complete re-scraping
    without skipping any previously processed entries.
    """
    print("Starting database reset process...")
    
    try:
        # Connect to the database
        db_path = 'nba_ids.db'
        
        # Check if the database exists
        if not os.path.exists(db_path):
            print(f"Database file {db_path} not found. Nothing to reset.")
            return False
            
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get counts before reset for reporting
        cursor.execute("SELECT COUNT(*) FROM processed_players")
        players_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM processing_state")
        state_count = cursor.fetchone()[0]
        
        # Reset the tracking tables
        cursor.execute("DELETE FROM processed_players")
        cursor.execute("DELETE FROM processing_state")
        
        # Commit changes
        conn.commit()
        
        print(f"Successfully reset database tracking:")
        print(f"- Removed {players_count} entries from processed_players table")
        print(f"- Removed {state_count} entries from processing_state table")
        print("The next scraping run will process all players from the beginning.")
        
        # Close connection
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"SQLite error occurred: {e}")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

if __name__ == "__main__":
    reset_tracking_database()