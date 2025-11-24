import sqlite3
import sys

db_path = r'H:\Meu Drive\automatizacao\Sistema_LopesRibeiro\dados_escritorio.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Listar tabelas
    print("=== TABELAS EXISTENTES ===")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    for table in tables:
        print(f"  - {table}")
    
    print("\n=== ESTRUTURA DA TABELA FINANCEIRO ===")
    cursor.execute("PRAGMA table_info(financeiro)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]} ({col[2]}) - PK:{col[5]} - NotNull:{col[3]} - Default:{col[4]}")
    
    print("\n=== ESTRUTURA DA TABELA CLIENTES ===")
    cursor.execute("PRAGMA table_info(clientes)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]} ({col[2]}) - PK:{col[5]} - NotNull:{col[3]} - Default:{col[4]}")
    
    conn.close()
    print("\n✅ Análise concluída!")
    
except Exception as e:
    print(f"❌ Erro: {e}")
    sys.exit(1)
