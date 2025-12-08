import database as db
import database_adapter as adapter

def migrar():
    print("Iniciando atualização para adicionar campos de Hipossuficiência...")
    
    colunas_novas = [
        ("nacionalidade", "TEXT"),
        ("rg", "TEXT"),
        ("orgao_emissor", "TEXT")
    ]
    
    with adapter.get_connection() as conn:
        cursor = conn.cursor()
        
        # Verificar colunas existentes
        cursor.execute("PRAGMA table_info(clientes)")
        colunas_existentes = [row['name'] for row in cursor.fetchall()]
        
        for nome_col, tipo_col in colunas_novas:
            if nome_col not in colunas_existentes:
                print(f"Adicionando coluna: {nome_col}...")
                try:
                    alter_query = f"ALTER TABLE clientes ADD COLUMN {nome_col} {tipo_col}"
                    cursor.execute(alter_query)
                    print(f"[OK] Coluna {nome_col} adicionada.")
                except Exception as e:
                    print(f"[ERRO] Falha ao adicionar {nome_col}: {e}")
            else:
                print(f"[SKIP] Coluna {nome_col} já existe.")
        
        conn.commit()
    
    print("Atualização concluída!")

if __name__ == "__main__":
    migrar()
