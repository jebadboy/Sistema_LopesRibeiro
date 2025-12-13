# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('data.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print("Tabelas encontradas:")
for t in tables:
    print(f"  - {t[0]}")
conn.close()
