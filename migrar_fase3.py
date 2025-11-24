import sqlite3
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_NAME = 'dados_escritorio.db'

def migrar_fase3():
    """
    Executa a migração da Fase 3:
    1. Cria a tabela 'parcelamentos' se não existir.
    2. Adiciona colunas novas à tabela 'financeiro'.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    try:
        # 1. Criar tabela parcelamentos
        logger.info("Verificando tabela 'parcelamentos'...")
        c.execute('''
            CREATE TABLE IF NOT EXISTS parcelamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_lancamento_financeiro INTEGER NOT NULL,
                numero_parcela INTEGER,
                total_parcelas INTEGER,
                valor_parcela REAL,
                vencimento TEXT,
                status_parcela TEXT DEFAULT 'pendente',
                pago_em TEXT,
                FOREIGN KEY (id_lancamento_financeiro) REFERENCES financeiro(id)
            )
        ''')
        logger.info("Tabela 'parcelamentos' verificada/criada.")

        # 2. Adicionar colunas em 'financeiro'
        logger.info("Verificando colunas novas em 'financeiro'...")
        colunas_novas = [
            ("recorrencia", "INTEGER DEFAULT 0"), # Boolean 0/1
            ("id_parceiro", "INTEGER"),
            ("percentual_parceria", "REAL")
        ]
        
        # Obter colunas existentes
        c.execute("PRAGMA table_info(financeiro)")
        colunas_existentes = [col[1] for col in c.fetchall()]
        
        for nome_col, tipo_col in colunas_novas:
            if nome_col not in colunas_existentes:
                try:
                    c.execute(f"ALTER TABLE financeiro ADD COLUMN {nome_col} {tipo_col}")
                    logger.info(f"Coluna '{nome_col}' adicionada com sucesso.")
                except Exception as e:
                    logger.error(f"Erro ao adicionar coluna '{nome_col}': {e}")
            else:
                logger.info(f"Coluna '{nome_col}' já existe.")

        conn.commit()
        logger.info("Migração da Fase 3 concluída com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro crítico na migração: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrar_fase3()
