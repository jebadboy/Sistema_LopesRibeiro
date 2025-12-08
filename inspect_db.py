import database as db
import pandas as pd

def inspect_table():
    print("Inspecionando tabela ai_insights...")
    try:
        # Tenta pegar uma linha para ver as colunas
        df = db.sql_get_query("SELECT * FROM ai_insights LIMIT 1")
        if not df.empty:
            print("Colunas encontradas:", df.columns.tolist())
        else:
            print("Tabela existe mas está vazia. Verificando schema via PRAGMA...")
            # Fallback para SQLite
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(ai_insights)")
                columns = [row[1] for row in cursor.fetchall()]
                print("Colunas (PRAGMA):", columns)
                
    except Exception as e:
        print(f"Erro ao inspecionar tabela: {e}")

if __name__ == "__main__":
    inspect_table()
