import sqlite3
import pandas as pd

try:
    conn = sqlite3.connect('dados_escritorio.db')
    cursor = conn.cursor()
    
    print("=== ESTRUTURA DA TABELA AGENDA ===")
    try:
        cursor.execute("PRAGMA table_info(agenda)")
        columns = cursor.fetchall()
        if not columns:
            print("Tabela 'agenda' não existe.")
        else:
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
    except Exception as e:
        print(f"Erro ao ler tabela: {e}")
        
    conn.close()
except Exception as e:
    print(f"Erro de conexão: {e}")
