import sys
import os

# Adiciona raiz ao path
sys.path.append(os.getcwd())

def run_fix_and_verify():
    print("--- Inicializando Banco de Dados (Trigger Migração) ---")
    try:
        import database
        database.init_db()
        print("[OK] init_db executado.")
    except Exception as e:
        print(f"[FAIL] Erro no init_db: {e}")
        return

    print("\n--- Verificando Tabela audit_logs ---")
    import sqlite3
    DB_PATH = 'dados_escritorio.db'
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check columns
    cursor.execute("PRAGMA table_info(audit_logs)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Colunas encontradas: {columns}")
    
    required = ['tabela', 'registro_id', 'campo', 'valor_anterior', 'valor_novo']
    missing = [c for c in required if c not in columns]
    
    if missing:
        print(f"[FAIL] Ainda faltando colunas: {missing}")
    else:
        print("[OK] Todas as colunas necessarias presentes!")

if __name__ == "__main__":
    run_fix_and_verify()
