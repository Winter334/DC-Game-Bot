"""
Chips Compensation Script
Add 300 chips to all players to compensate for BUG testing
"""
import sqlite3
import os

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "games.db")

def add_chips_to_all_players(amount: int = 300):
    """Add chips to all players"""
    
    if not os.path.exists(DB_PATH):
        print(f"[ERROR] Database file not found: {DB_PATH}")
        return
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Get all players current balance
        cursor.execute("SELECT user_id, chips FROM players")
        players = cursor.fetchall()
        
        if not players:
            print("[ERROR] No players found")
            return
        
        print(f"[INFO] Found {len(players)} players")
        print("-" * 50)
        
        # Add chips to each player
        for player in players:
            old_chips = player["chips"]
            new_chips = old_chips + amount
            cursor.execute(
                "UPDATE players SET chips = ? WHERE user_id = ?",
                (new_chips, player["user_id"])
            )
            print(f"  Player {player['user_id']}: {old_chips} -> {new_chips} (+{amount})")
        
        # Commit changes
        conn.commit()
        
        print("-" * 50)
        print(f"[SUCCESS] Added {amount} chips to {len(players)} players!")
        
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 50)
    print("Chips Compensation Script")
    print("=" * 50)
    add_chips_to_all_players(300)