
import database as db
import sqlite3
import pandas as pd

def verify_migration():
    print("Initializing database...")
    # This should trigger the migration
    db.init_db()
    
    print("Checking 'andamentos' columns...")
    try:
        df = db.sql_get_query("PRAGMA table_info(andamentos)")
        columns = df['name'].tolist()
        print(f"Columns found: {columns}")
        
        expected = ['hash_id', 'analise_ia', 'urgente', 'data_analise']
        missing = [col for col in expected if col not in columns]
        
        if not missing:
            print("SUCCESS: All new columns found!")
        else:
            print(f"FAILURE: Missing columns: {missing}")
            
    except Exception as e:
        print(f"Error verifying: {e}")

if __name__ == "__main__":
    verify_migration()
