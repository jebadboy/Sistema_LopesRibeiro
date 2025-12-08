import sqlite3

conn = sqlite3.connect(r'H:\Meu Drive\automatizacao\Sistema_LopesRibeiro\data.db')
cursor = conn.cursor()

# Verificar se tabela tokens_publicos existe
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tokens_publicos'")
existe = cursor.fetchone()

print(f"Tabela tokens_publicos existe: {'SIM' if existe else 'NAO'}")

if not existe:
    print("\nCriando tabela tokens_publicos...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tokens_publicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            id_processo INTEGER NOT NULL,
            data_criacao DATETIME DEFAULT CURRENT_TIMESTAMP,
            data_expiracao DATETIME,
            ativo BOOLEAN DEFAULT 1,
            acessos INTEGER DEFAULT 0,
            ultimo_acesso DATETIME,
            FOREIGN KEY (id_processo) REFERENCES processos(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    print("Tabela criada com sucesso!")

conn.close()
