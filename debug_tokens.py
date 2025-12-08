import sqlite3

conn = sqlite3.connect(r'H:\Meu Drive\automatizacao\Sistema_LopesRibeiro\data.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Verificar tokens gerados
cursor.execute("SELECT * FROM tokens_publicos ORDER BY data_criacao DESC LIMIT 5")
tokens = cursor.fetchall()

print("=== TOKENS NO BANCO ===")
if tokens:
    for t in tokens:
        print(f"\nID: {t['id']}")
        print(f"Token (primeiros 20 chars): {t['token'][:20]}...")
        print(f"ID Processo: {t['id_processo']}")
        print(f"Data Criacao: {t['data_criacao']}")
        print(f"Data Expiracao: {t['data_expiracao']}")
        print(f"Ativo: {t['ativo']}")
        print(f"Acessos: {t['acessos']}")
else:
    print("Nenhum token encontrado!")

# Verificar se processo existe
print("\n\n=== PROCESSOS NO BANCO ===")
cursor.execute("SELECT id, cliente_nome, acao FROM processos LIMIT 5")
processos = cursor.fetchall()

if processos:
    for p in processos:
        print(f"ID: {p['id']} | Cliente: {p['cliente_nome']} | Acao: {p['acao']}")
else:
    print("Nenhum processo encontrado!")

conn.close()
