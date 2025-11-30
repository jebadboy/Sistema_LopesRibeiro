import sqlite3
import secrets
import logging

# Configuração de log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_NAME = 'dados_escritorio.db'

def migrar_token_publico():
    """
    Adiciona a coluna 'token_acesso' na tabela 'processos' se não existir.
    Gera tokens iniciais para processos existentes que não tenham.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        # 1. Verificar se a coluna já existe
        c.execute("PRAGMA table_info(processos)")
        colunas = [col[1] for col in c.fetchall()]
        
        if 'token_acesso' not in colunas:
            logger.info("Coluna 'token_acesso' não encontrada. Adicionando...")
            c.execute("ALTER TABLE processos ADD COLUMN token_acesso TEXT")
            conn.commit()
            logger.info("Coluna 'token_acesso' adicionada com sucesso.")
        else:
            logger.info("Coluna 'token_acesso' já existe.")
            
        # 2. Gerar tokens para processos que estão sem (NULL ou vazio)
        logger.info("Verificando processos sem token...")
        c.execute("SELECT id FROM processos WHERE token_acesso IS NULL OR token_acesso = ''")
        processos_sem_token = c.fetchall()
        
        if processos_sem_token:
            logger.info(f"Encontrados {len(processos_sem_token)} processos sem token. Gerando...")
            for (proc_id,) in processos_sem_token:
                # Gera um token seguro de 12 caracteres (ex: a8j29k1mzxp3)
                novo_token = secrets.token_urlsafe(8) 
                c.execute("UPDATE processos SET token_acesso = ? WHERE id = ?", (novo_token, proc_id))
            
            conn.commit()
            logger.info("Tokens gerados para todos os processos existentes.")
        else:
            logger.info("Todos os processos já possuem token.")
            
    except Exception as e:
        logger.error(f"Erro durante a migração: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    migrar_token_publico()
