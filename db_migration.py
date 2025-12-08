"""Script para adicionar melhorias ao banco de dados"""
import sqlite3

conn = sqlite3.connect(r'H:\Meu Drive\automatizacao\Sistema_LopesRibeiro\data.db')
cursor = conn.cursor()

print("=== Aplicando melhorias no banco ===\n")

# 1. Adicionar coluna assunto em processos
try:
    cursor.execute("ALTER TABLE processos ADD COLUMN assunto TEXT")
    conn.commit()
    print("Coluna 'assunto' adicionada")
except Exception as e:
    print(f"Coluna 'assunto' já existe: {e}")

# 2. Criar tabela partes_processo
try:
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS partes_processo (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_processo INTEGER NOT NULL,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL,
            cpf_cnpj TEXT,
            data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (id_processo) REFERENCES processos(id) ON DELETE CASCADE
        )
    ''')
    conn.commit()
    print("Tabela 'partes_processo' criada")
except Exception as e:
    print(f"Erro: {e}")

conn.close()
print("\nMigracoes concluidas!")
