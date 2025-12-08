import database as db

print("Inicializando banco de dados...")
db.init_db()
print("Banco inicializado com sucesso!")

# Verificar se tabela foi criada
import sqlite3
conn = sqlite3.connect('data.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tabelas = [t[0] for t in cursor.fetchall()]

print(f"\nTabelas criadas: {tabelas}")
conn.close()
