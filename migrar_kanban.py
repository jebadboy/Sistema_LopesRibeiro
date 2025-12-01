import sqlite3

def migrar():
    print("Iniciando migração para V2.0 (Kanban)...")
    conn = sqlite3.connect('dados_escritorio.db')
    c = conn.cursor()
    
    try:
        # Tentar adicionar a coluna fase_processual
        print("Adicionando coluna 'fase_processual' na tabela 'processos'...")
        c.execute("ALTER TABLE processos ADD COLUMN fase_processual TEXT DEFAULT 'A Ajuizar'")
        print("Coluna adicionada com sucesso!")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("Coluna 'fase_processual' já existe.")
        else:
            print(f"Erro ao adicionar coluna: {e}")
            
    conn.commit()
    conn.close()
    print("Migração concluída.")

if __name__ == "__main__":
    migrar()
