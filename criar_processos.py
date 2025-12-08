import sqlite3

conn = sqlite3.connect(r'H:\Meu Drive\automatizacao\Sistema_LopesRibeiro\data.db')
cursor = conn.cursor()

print("Criando tabela processos...")

cursor.execute('''
    CREATE TABLE IF NOT EXISTS processos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT,
        cliente_nome TEXT,
        area TEXT,
        acao TEXT,
        vara TEXT,
        status TEXT DEFAULT 'Ativo',
        proximo_prazo TEXT,
        responsavel TEXT,
        status_processo TEXT,
        parceiro_nome TEXT,
        parceiro_percentual REAL,
        pasta_drive_link TEXT,
        tipo_honorario TEXT,
        fase_processual TEXT,
        id_cliente INTEGER,
        valor_causa REAL,
        data_distribuicao TEXT,
        link_drive TEXT,
        obs TEXT,
        assunto TEXT
    )
''')

conn.commit()

# Verificar
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='processos'")
if cursor.fetchone():
    print("Tabela processos criada com sucesso!")
else:
    print("Erro ao criar tabela")

conn.close()
