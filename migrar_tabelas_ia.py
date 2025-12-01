"""
Script para adicionar tabelas de IA ao banco de dados
"""
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_NAME = 'dados_escritorio.db'

def adicionar_tabelas_ia():
    """Adiciona tabelas de IA ao banco de dados"""
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        # Tabela de Histórico de IA
        logger.info("Criando tabela ai_historico...")
        c.execute('''
            CREATE TABLE IF NOT EXISTS ai_historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL,
                tipo TEXT CHECK(tipo IN ('chat', 'analise', 'sugestao')) NOT NULL,
                input TEXT,
                output TEXT,
                data_hora TEXT DEFAULT CURRENT_TIMESTAMP,
                processo_id INTEGER,
                FOREIGN KEY (processo_id) REFERENCES processos(id)
            )
        ''')
        
        # Tabela de Cache de IA
        logger.info("Criando tabela ai_cache...")
        c.execute('''
            CREATE TABLE IF NOT EXISTS ai_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hash_input TEXT UNIQUE NOT NULL,
                resposta TEXT NOT NULL,
                data_criacao TEXT DEFAULT CURRENT_TIMESTAMP,
                validade INTEGER DEFAULT 7
            )
        ''')
        
        conn.commit()
        logger.info("✅ Tabelas de IA criadas com sucesso!")
        
        # Verificar se foram criadas
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'ai_%'")
        tabelas = c.fetchall()
        logger.info(f"Tabelas AI encontradas: {tabelas}")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro ao criar tabelas de IA: {e}")
        return False

if __name__ == "__main__":
    sucesso = adicionar_tabelas_ia()
    if sucesso:
        print("\n✅ Script concluído com sucesso!")
        print("As tabelas 'ai_historico' e 'ai_cache' foram criadas.")
    else:
        print("\n❌ Falha ao executar script.")
