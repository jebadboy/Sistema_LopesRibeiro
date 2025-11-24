import sqlite3
import pandas as pd

DB_NAME = 'h:/Meu Drive/automatizacao/Sistema_LopesRibeiro/dados_escritorio.db'

def check_schema():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Check financeiro table
        cursor.execute("PRAGMA table_info(financeiro)")
        columns = [col[1] for col in cursor.fetchall()]
        print(f"Columns in 'financeiro': {columns}")
        
        missing_cols = []
        for col in ['percentual_parceria', 'id_parceiro']:
            if col not in columns:
                missing_cols.append(col)
        
        if missing_cols:
            print(f"MISSING COLUMNS in 'financeiro': {missing_cols}")
        else:
            print("All expected columns present in 'financeiro'.")

        conn.close()
    except Exception as e:
        print(f"Error checking schema: {e}")

if __name__ == "__main__":
    check_schema()
