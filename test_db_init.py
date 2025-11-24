import sqlite3
import os
from database import inicializar_tabelas_v2, get_connection, DB_NAME

# Use a temporary database for testing
TEST_DB = 'test_db_init.db'

# Override DB_NAME in database module (monkey patching for test)
import database
database.DB_NAME = TEST_DB

def test_initialization():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    
    print("Initializing tables...")
    # First run init_db to create base tables (mocking what app.py does)
    # But since init_db calls inicializar_tabelas_v2, we can just call init_db if we want full test
    # However, init_db is not imported. Let's just call inicializar_tabelas_v2 after creating base financeiro
    
    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    # Create base financeiro table as it would be in V1
    c.execute('''
        CREATE TABLE financeiro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            tipo TEXT,
            categoria TEXT,
            descricao TEXT,
            valor REAL,
            responsavel TEXT,
            status_pagamento TEXT,
            vencimento TEXT
        )
    ''')
    conn.commit()
    conn.close()
    
    print("Running inicializar_tabelas_v2...")
    inicializar_tabelas_v2()
    
    print("Verifying columns...")
    conn = sqlite3.connect(TEST_DB)
    c = conn.cursor()
    c.execute("PRAGMA table_info(financeiro)")
    columns = [col[1] for col in c.fetchall()]
    print(f"Columns: {columns}")
    
    required = ['id_parceiro', 'percentual_parceria']
    missing = [col for col in required if col not in columns]
    
    conn.close()
    
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    if missing:
        print(f"FAILED: Missing columns {missing}")
        exit(1)
    else:
        print("SUCCESS: All columns present.")
        exit(0)

if __name__ == "__main__":
    test_initialization()
