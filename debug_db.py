import database as db
import pandas as pd
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_database():
    print("--- Starting Database Debug ---")
    
    # 1. Check Connection
    try:
        print("Checking connection...")
        # Assuming init_db checks connection or we can try a simple query
        db.init_db()
        print("init_db() executed successfully.")
    except Exception as e:
        print(f"ERROR in init_db(): {e}")
        return

    # 2. Check Tables
    tables = ["usuarios", "clientes", "processos", "financeiro", "agenda"]
    for table in tables:
        try:
            print(f"Checking table '{table}'...")
            df = db.sql_get(table)
            print(f"Table '{table}' read successfully. Rows: {len(df)}")
            print(f"Columns: {list(df.columns)}")
        except Exception as e:
            print(f"ERROR reading table '{table}': {e}")

    # 3. Test Insert/Update (Rollback if possible, or use test data)
    # We won't do actual writes to avoid messing up data, unless we use a transaction that we roll back.
    # But db module might auto-commit.
    # Let's just rely on read for now.

    print("--- Database Debug Finished ---")

if __name__ == "__main__":
    debug_database()
