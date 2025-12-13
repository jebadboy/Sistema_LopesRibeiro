# -*- coding: utf-8 -*-
import sqlite3
import sys
import io

# Configura stdout para UTF-8 no Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def init_memory():
    db_path = 'data.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("🔧 INICIALIZANDO MEMÓRIA DA IA...")
    
    # 1. Tabela de Cache Estratégico (Single Shot)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_analises_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_processo INTEGER NOT NULL,
            analise_json TEXT NOT NULL,
            data_analise TEXT NOT NULL,
            UNIQUE(id_processo)
        )
    ''')
    print("✅ Tabela 'ai_analises_cache' verificada.")
    
    # 2. Tabela de Andamentos (Se não existir)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS andamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_processo INTEGER,
            data TEXT,
            descricao TEXT,
            tipo TEXT,
            hash_id TEXT UNIQUE,
            analise_ia TEXT,
            urgente INTEGER DEFAULT 0,
            data_analise TEXT,
            responsavel TEXT
        )
    ''')
    print("✅ Tabela 'andamentos' verificada.")
    
    # 3. Cache Geral de Requisições (Para evitar repetição de chamadas idênticas)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_cache (
            hash_input TEXT PRIMARY KEY,
            resposta TEXT,
            data_criacao TEXT,
            validade INTEGER
        )
    ''')
    print("✅ Tabela 'ai_cache' verificada.")
    
    conn.commit()
    conn.close()
    
    print("\n🚀 SISTEMA PRONTO PARA ECONOMIZAR COTA!")
    
    # Verificar criação
    print("\n📋 Confirmando tabelas no banco...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tabelas = [row[0] for row in cursor.fetchall()]
    conn.close()
    
    print(f"   Tabelas atuais: {tabelas}")

if __name__ == "__main__":
    init_memory()
