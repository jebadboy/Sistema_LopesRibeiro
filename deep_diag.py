import sqlite3
from datetime import datetime
import pandas as pd

conn = sqlite3.connect(r'H:\Meu Drive\automatizacao\Sistema_LopesRibeiro\data.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=== DIAGNÓSTICO COMPLETO ===\n")

# 1. Verificar Tabela Processos
print("1. PROCESSOS:")
df_proc = pd.read_sql("SELECT id, cliente_nome, numero, id_cliente FROM processos", conn)
print(df_proc if not df_proc.empty else "NENHUM PROCESSO ENCONTRADO")
print("-" * 30)

# 2. Verificar Tabela Tokens
print("2. TOKENS PÚBLICOS:")
df_tokens = pd.read_sql("SELECT id, token, id_processo, data_expiracao, ativo FROM tokens_publicos", conn)
print(df_tokens if not df_tokens.empty else "NENHUM TOKEN ENCONTRADO")
print("-" * 30)

# 3. Testar o JOIN (Query usada na ficha do cliente)
print("3. TESTE DE JOIN (Ficha do Cliente):")
try:
    query = """
    SELECT t.token, p.cliente_nome 
    FROM tokens_publicos t
    JOIN processos p ON t.id_processo = p.id
    """
    df_join = pd.read_sql(query, conn)
    print(df_join if not df_join.empty else "JOIN FALHOU: IDs não correspondem ou tabelas vazias")
except Exception as e:
    print(f"ERRO NO JOIN: {e}")
print("-" * 30)

# 4. Verificar Tipos de Dados dos IDs
print("4. TIPOS DE DADOS:")
cursor.execute("PRAGMA table_info(processos)")
print(f"ID Processo (Schema): {[c['type'] for c in cursor.fetchall() if c['name'] == 'id']}")

cursor.execute("PRAGMA table_info(tokens_publicos)")
print(f"ID Processo FK (Schema): {[c['type'] for c in cursor.fetchall() if c['name'] == 'id_processo']}")

conn.close()
