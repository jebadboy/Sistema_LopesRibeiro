import sys
import os
import sqlite3
import pandas as pd

# Caminho do banco
DB_PATH = 'dados_escritorio.db'

def check_table():
    print("--- Verificando Tabela transacoes_bancarias ---")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='transacoes_bancarias'")
    if not cursor.fetchone():
        print("[FAIL] ERRO: Tabela NAO existe!")
        return False
        
    print("[OK] Tabela encontrada.")
    
    # Check columns
    cursor.execute("PRAGMA table_info(transacoes_bancarias)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Colunas encontradas: {columns}")
    
    required = ['tipo_origem', 'conta_origem', 'transaction_id']
    missing = [c for c in required if c not in columns]
    
    if missing:
        print(f"[FAIL] ERRO: Colunas faltando: {missing}")
        return False
        
    print("[OK] Todas as colunas necessarias estao presentes.")
    return True

if __name__ == "__main__":
    # Force init_db indirectally via import database (or simulate)
    # Since we can't easily import the app context without running it, 
    # we will rely on finding the table. 
    # If the app was run, it would trigger init_db.
    # To be safe, we can try to call init_db directly if we can import it.
    
    sys.path.append(os.getcwd())
    try:
        import database
        print("Inicializando banco...")
        database.init_db()
    except Exception as e:
        print(f"Erro ao inicializar banco: {e}")
        
    if check_table():
        print("\n✅ Verificação concluída com SUCESSO")
    else:
        print("\n❌ Verificação FALHOU")
