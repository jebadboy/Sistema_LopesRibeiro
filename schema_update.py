import sqlite3
import logging
import os

# Configuração de Log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Caminho absoluto para o banco de dados
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dados_escritorio.db')

def fix_processos_schema():
    """
    Adiciona a coluna id_cliente à tabela processos se ela não existir.
    """
    logger.info("Iniciando correção do schema da tabela 'processos'...")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar colunas existentes
        cursor.execute("PRAGMA table_info(processos)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # 1. Adicionar id_cliente
        if 'id_cliente' not in columns:
            logger.info("Adicionando coluna 'id_cliente'...")
            cursor.execute("ALTER TABLE processos ADD COLUMN id_cliente INTEGER REFERENCES clientes(id)")
        else:
            logger.info("Coluna 'id_cliente' já existe.")

        # 2. Adicionar outras colunas que podem estar faltando baseadas no database.py
        # database.py define: numero_processo, cliente, parte_contraria, vara, comarca, status, fase_processual, valor_causa, data_distribuicao, link_drive, obs, id_cliente
        
        # Mapeamento de colunas antigas para novas (se necessário renomear, mas SQLite não suporta rename column fácil em versões antigas, então vamos adicionar as novas)
        
        if 'valor_causa' not in columns:
            logger.info("Adicionando coluna 'valor_causa'...")
            cursor.execute("ALTER TABLE processos ADD COLUMN valor_causa REAL")
            
        if 'data_distribuicao' not in columns:
            logger.info("Adicionando coluna 'data_distribuicao'...")
            cursor.execute("ALTER TABLE processos ADD COLUMN data_distribuicao TEXT")
            
        if 'link_drive' not in columns and 'pasta_drive_link' in columns:
             # Se já tem pasta_drive_link, vamos considerar como link_drive ou criar link_drive e copiar?
             # Vamos criar link_drive para ficar compatível com o código novo
             logger.info("Adicionando coluna 'link_drive'...")
             cursor.execute("ALTER TABLE processos ADD COLUMN link_drive TEXT")
             cursor.execute("UPDATE processos SET link_drive = pasta_drive_link")
        elif 'link_drive' not in columns:
             cursor.execute("ALTER TABLE processos ADD COLUMN link_drive TEXT")

        if 'obs' not in columns:
             logger.info("Adicionando coluna 'obs'...")
             cursor.execute("ALTER TABLE processos ADD COLUMN obs TEXT")

        # Tentar preencher id_cliente baseado no nome do cliente (cliente_nome)
        if 'cliente_nome' in columns:
            logger.info("Tentando vincular id_cliente baseado em cliente_nome...")
            cursor.execute("""
                UPDATE processos 
                SET id_cliente = (SELECT id FROM clientes WHERE clientes.nome = processos.cliente_nome)
                WHERE id_cliente IS NULL
            """)
            changes = cursor.rowcount
            logger.info(f"Vinculados {changes} processos a clientes existentes.")

        conn.commit()
        logger.info("Schema da tabela 'processos' corrigido com sucesso.")
        
    except Exception as e:
        logger.error(f"Erro ao corrigir schema: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    fix_processos_schema()
