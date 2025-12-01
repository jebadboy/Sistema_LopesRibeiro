import database as db
import sqlite3

try:
    print("Inicializando tabelas...")
    db.inicializar_tabelas_v2()
    
    conn = db.get_connection()
    c = conn.cursor()
    
    tabelas_esperadas = ['agenda', 'documentos_processo', 'parcelamentos', 'modelos_proposta', 'configuracoes']
    
    print("\nVerificando tabelas:")
    for tabela in tabelas_esperadas:
        c.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tabela}'")
        if c.fetchone():
            print(f"✅ Tabela '{tabela}' existe.")
        else:
            print(f"❌ Tabela '{tabela}' NÃO existe.")
            
    print("\nVerificando colunas em 'clientes':")
    c.execute("PRAGMA table_info(clientes)")
    colunas = [col[1] for col in c.fetchall()]
    if 'link_procuracao' in colunas:
        print("✅ Coluna 'link_procuracao' existe em 'clientes'.")
    else:
        print("❌ Coluna 'link_procuracao' NÃO existe em 'clientes'.")
        
    if 'link_hipossuficiencia' in colunas:
        print("✅ Coluna 'link_hipossuficiencia' existe em 'clientes'.")
    else:
        print("❌ Coluna 'link_hipossuficiencia' NÃO existe em 'clientes'.")

    conn.close()
    
except Exception as e:
    print(f"Erro durante a verificação: {e}")
