import sqlite3
import os

DB_PATH = 'dados_escritorio.db'

def check_audit_logs():
    print("--- Verificando Tabela audit_logs ---")
    
    if not os.path.exists(DB_PATH):
        print(f"[FAIL] Banco de dados não encontrado: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_logs'")
    if not cursor.fetchone():
        print("[FAIL] Tabela audit_logs NAO existe!")
        return
        
    print("[OK] Tabela audit_logs encontrada.")
    
    # Check columns
    cursor.execute("PRAGMA table_info(audit_logs)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Colunas encontradas: {columns}")
    
    required = ['action', 'tabela', 'registro_id', 'campo', 'valor_anterior', 'valor_novo']
    missing = [c for c in required if c not in columns]
    
    if missing:
        print(f"[FAIL] Colunas faltando: {missing}")
        # Tentar corrigir? O script é só de verificação.
    else:
        print("[OK] Todas as colunas necessarias estao presentes.")

if __name__ == "__main__":
    check_audit_logs()
