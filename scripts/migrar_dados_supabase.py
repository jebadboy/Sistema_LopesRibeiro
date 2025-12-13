"""
Script de Migração de Dados: SQLite -> Supabase/PostgreSQL
Sistema Jurídico Lopes & Ribeiro

Uso:
1. Configure DATABASE_URL no .streamlit/secrets.toml
2. Execute: python scripts/migrar_dados_supabase.py
"""

import os
import sys
import sqlite3
import logging

# Adicionar diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Tentar importar psycopg2
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    logger.error("❌ psycopg2 não instalado. Execute: pip install psycopg2-binary")
    sys.exit(1)

# Connection string do Supabase
DATABASE_URL = os.getenv('DATABASE_URL')

# Se não tiver no ambiente, tentar ler do secrets
if not DATABASE_URL:
    try:
        import tomli
        with open('.streamlit/secrets.toml', 'rb') as f:
            secrets = tomli.load(f)
            DATABASE_URL = secrets.get('DATABASE_URL')
    except:
        pass

if not DATABASE_URL:
    # Fallback: connection string hardcoded (remova em produção!)
    DATABASE_URL = "postgresql://postgres:CLMcQT6ymaUoO86E@db.hjcqknzxxedtswevstug.supabase.co:5432/postgres"
    logger.warning("⚠️ Usando DATABASE_URL do script. Configure no secrets.toml para produção!")

# Arquivo SQLite local
SQLITE_DB = "dados_escritorio.db"

# Tabelas a migrar (em ordem de dependência)
TABELAS = [
    'usuarios',
    'clientes',
    'processos',
    'financeiro',
    'andamentos',
    'parcelas',
    'agenda',
    'config',
    'cliente_timeline',
    'documentos_drive',
    'modelos_proposta',
    'config_aniversarios',
    'ai_historico',
    'audit_logs',
    'partes_processo',
    'modelos_documentos',
    'tokens_publicos',
    'notificacoes',
    'alertas_email',
    'rate_limit_events',
    'transacoes_bancarias',
]


def get_sqlite_connection():
    """Conecta ao SQLite local"""
    if not os.path.exists(SQLITE_DB):
        logger.error(f"❌ Arquivo {SQLITE_DB} não encontrado!")
        sys.exit(1)
    
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    return conn


def get_postgres_connection():
    """Conecta ao PostgreSQL/Supabase"""
    return psycopg2.connect(DATABASE_URL)


def get_table_columns(cursor, table_name, is_postgres=False):
    """Retorna colunas de uma tabela"""
    if is_postgres:
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = %s ORDER BY ordinal_position
        """, (table_name,))
        return [row[0] for row in cursor.fetchall()]
    else:
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [row[1] for row in cursor.fetchall()]


def migrate_table(table_name, sqlite_conn, pg_conn):
    """Migra uma tabela do SQLite para PostgreSQL"""
    sqlite_cursor = sqlite_conn.cursor()
    pg_cursor = pg_conn.cursor()
    
    try:
        # Verificar se tabela existe no SQLite
        sqlite_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        if not sqlite_cursor.fetchone():
            logger.info(f"⏭️  {table_name}: Tabela não existe no SQLite, pulando...")
            return 0
        
        # Obter colunas do SQLite
        sqlite_cols = get_table_columns(sqlite_cursor, table_name, is_postgres=False)
        
        # Obter colunas do PostgreSQL
        pg_cols = get_table_columns(pg_cursor, table_name, is_postgres=True)
        
        if not pg_cols:
            logger.warning(f"⚠️  {table_name}: Tabela não existe no PostgreSQL, pule!")
            return 0
        
        # Colunas comuns (sem 'id' para evitar conflito de SERIAL)
        common_cols = [col for col in sqlite_cols if col in pg_cols and col != 'id']
        
        if not common_cols:
            logger.warning(f"⚠️  {table_name}: Sem colunas comuns para migrar")
            return 0
        
        # Buscar dados do SQLite
        sqlite_cursor.execute(f"SELECT * FROM {table_name}")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            logger.info(f"⏭️  {table_name}: Tabela vazia, pulando...")
            return 0
        
        # Inserir no PostgreSQL
        migrated = 0
        for row in rows:
            # Montar dicionário com valores
            row_dict = dict(zip(sqlite_cols, row))
            
            # Filtrar apenas colunas comuns
            values = [row_dict.get(col) for col in common_cols]
            
            # Montar INSERT
            cols_str = ', '.join(common_cols)
            placeholders = ', '.join(['%s'] * len(common_cols))
            insert_sql = f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            
            try:
                pg_cursor.execute(insert_sql, values)
                migrated += 1
            except Exception as e:
                logger.debug(f"    Erro ao inserir: {e}")
        
        pg_conn.commit()
        logger.info(f"✅ {table_name}: {migrated}/{len(rows)} registros migrados")
        return migrated
        
    except Exception as e:
        logger.error(f"❌ {table_name}: Erro na migração - {e}")
        pg_conn.rollback()
        return 0


def test_connection():
    """Testa conexão com PostgreSQL"""
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        logger.info("✅ Conexão com Supabase OK!")
        return True
    except Exception as e:
        logger.error(f"❌ Falha na conexão: {e}")
        return False


def main():
    """Executa a migração completa"""
    print("=" * 50)
    print("MIGRACAO SQLite -> Supabase/PostgreSQL")
    print("=" * 50)
    print()
    
    # Testar conexão
    if not test_connection():
        return
    
    # Conectar
    sqlite_conn = get_sqlite_connection()
    pg_conn = get_postgres_connection()
    
    total_migrated = 0
    
    print()
    print("Iniciando migração das tabelas...")
    print("-" * 50)
    
    for table in TABELAS:
        count = migrate_table(table, sqlite_conn, pg_conn)
        total_migrated += count
    
    print("-" * 50)
    print("\n[OK] MIGRACAO CONCLUIDA!")
    print(f"   Total de registros migrados: {total_migrated}")
    print()
    print("[!] PROXIMOS PASSOS:")
    print("   1. Configure DATABASE_URL no .streamlit/secrets.toml")
    print("   2. Reinicie o Streamlit")
    print("   3. Teste o sistema")
    
    sqlite_conn.close()
    pg_conn.close()


if __name__ == "__main__":
    main()
