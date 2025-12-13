"""
Database Adapter - Suporta SQLite (local) e PostgreSQL (produção)
Detecta automaticamente o ambiente e usa o banco apropriado
"""
import os
import sqlite3
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

# Detectar ambiente - Prioridade: env var -> streamlit secrets -> SQLite
DATABASE_URL = os.getenv('DATABASE_URL')

# Se não tiver no ambiente, tentar ler do Streamlit secrets
if not DATABASE_URL:
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and 'DATABASE_URL' in st.secrets:
            DATABASE_URL = st.secrets['DATABASE_URL']
            logger.info("📦 DATABASE_URL lido do Streamlit secrets")
    except:
        pass

USE_POSTGRES = DATABASE_URL is not None

if USE_POSTGRES:
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        logger.info("🐘 Usando PostgreSQL (Supabase)")
    except ImportError:
        logger.warning("⚠️ psycopg2 não instalado. Usando SQLite como fallback.")
        USE_POSTGRES = False
else:
    logger.info("🗄️  Usando SQLite (Desenvolvimento Local)")


class DatabaseAdapter:
    """Adaptador que abstrai SQLite e PostgreSQL"""
    
    def __init__(self):
        self.db_type = 'postgresql' if USE_POSTGRES else 'sqlite'
        self.db_name = 'dados_escritorio.db'  # Apenas para SQLite
    
    @contextmanager
    def get_connection(self):
        """Retorna conexão apropriada baseada no ambiente"""
        conn = None
        try:
            if USE_POSTGRES:
                # Conexão PostgreSQL
                conn = psycopg2.connect(DATABASE_URL)
                conn.cursor_factory = RealDictCursor
            else:
                # Conexão SQLite
                conn = sqlite3.connect(self.db_name)
                conn.row_factory = sqlite3.Row
            
            yield conn
            
            if not USE_POSTGRES:
                # SQLite precisa de commit manual
                conn.commit()
        
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Erro na conexão: {e}")
            raise
        
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query, params=None):
        """Executa query e retorna cursor"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if USE_POSTGRES:
                conn.commit()
            
            return cursor
    
    def fetch_all(self, query, params=None):
        """Executa query e retorna todos os resultados"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
    
    def fetch_one(self, query, params=None):
        """Executa query e retorna um resultado"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchone()
    
    def adapt_sql(self, sqlite_sql):
        """
        Adapta SQL do SQLite para PostgreSQL quando necessário
        
        Principais diferenças:
        - SQLite: AUTOINCREMENT -> PostgreSQL: SERIAL
        - SQLite: TEXT -> PostgreSQL: TEXT ou VARCHAR
        - SQLite: INTEGER -> PostgreSQL: INTEGER ou BIGINT
        """
        if not USE_POSTGRES:
            return sqlite_sql
        
        # Substituições para PostgreSQL
        pg_sql = sqlite_sql.replace('AUTOINCREMENT', '')
        pg_sql = pg_sql.replace('INTEGER PRIMARY KEY', 'SERIAL PRIMARY KEY')
        
        return pg_sql

# Singleton global
db_adapter = DatabaseAdapter()

def get_adapter():
    """Retorna instância do adaptador"""
    return db_adapter

# Função helper para compatibilidade
@contextmanager
def get_connection():
    """Wrapper para manter compatibilidade com código existente"""
    with db_adapter.get_connection() as conn:
        yield conn
