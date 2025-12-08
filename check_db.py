import sqlite3

conn = sqlite3.connect(r'H:\Meu Drive\automatizacao\Sistema_LopesRibeiro\data.db')
cursor = conn.cursor()

# Ver colunas da tabela processos
cursor.execute('PRAGMA table_info(processos)')
colunas = cursor.fetchall()

print("=== Colunas da tabela processos ===")
for col in colunas:
    print(f"{col[1]} - {col[2]}")

# Verificar se existe tabela partes_processo
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='partes_processo'")
exists = cursor.fetchone()
print(f"\nTabela partes_processo existe: {'SIM' if exists else 'NÃO'}")

conn.close()
print("\n✅ Verificação concluída")
