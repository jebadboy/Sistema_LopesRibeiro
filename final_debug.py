import sqlite3

conn = sqlite3.connect(r'H:\Meu Drive\automatizacao\Sistema_LopesRibeiro\data.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Listar processos
cursor.execute("SELECT id, cliente_nome, acao FROM processos")
processos = cursor.fetchall()

print("=== PROCESSOS NO BANCO ===")
if processos:
    for p in processos:
        print(f"ID: {p['id']} | Cliente: {p['cliente_nome']} | Ação: {p['acao']}")
else:
    print("NENHUM PROCESSO!")

# Listar tokens
cursor.execute("SELECT id, token, id_processo FROM tokens_publicos")
tokens = cursor.fetchall()

print("\n=== TOKENS GERADOS ===")
if tokens:
    for t in tokens:
        print(f"Token ID {t['id']} -> Processo ID {t['id_processo']} | Token: ...{t['token'][-10:]}")
else:
    print("NENHUM TOKEN!")

conn.close()
