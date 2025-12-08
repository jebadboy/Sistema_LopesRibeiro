import sqlite3
import logging

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = 'dados_escritorio.db'

def migrar_banco():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar se a coluna já existe
        cursor.execute("PRAGMA table_info(clientes)")
        colunas = [info[1] for info in cursor.fetchall()]
        
        if 'data_nascimento' not in colunas:
            logger.info("Adicionando coluna 'data_nascimento' à tabela 'clientes'...")
            cursor.execute("ALTER TABLE clientes ADD COLUMN data_nascimento TEXT")
            conn.commit()
            logger.info("Coluna adicionada com sucesso!")
        else:
            logger.info("A coluna 'data_nascimento' já existe.")
            
    except Exception as e:
        logger.error(f"Erro na migração: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrar_banco()
