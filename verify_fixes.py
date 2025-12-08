import os
import sqlite3
import logging
from datetime import datetime

# Configurar logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerifyFixes")

# Mocking database adapter to use a local test db
import database_adapter as adapter
adapter.USE_POSTGRES = False
adapter.db_adapter.db_name = 'test_verification.db'

import database as db

def setup_test_db():
    """Cria um banco de teste limpo."""
    if os.path.exists('test_verification.db'):
        os.remove('test_verification.db')
    
    logger.info("Inicializando banco de teste...")
    db.init_db()

def test_crud_seguro():
    """Testa operações CRUD com caracteres especiais (SQL Injection)."""
    logger.info("--- Testando CRUD Seguro ---")
    
    # 1. Insert com aspas (Teste de SQL Injection)
    nome_perigoso = "D'Avila & O'Brian"
    cliente_data = {
        'nome': nome_perigoso,
        'cpf_cnpj': '12345678900',
        'status_cliente': 'ATIVO'
    }
    
    try:
        cid = db.crud_insert('clientes', cliente_data, "Teste Insert Seguro")
        logger.info(f"Insert OK. ID: {cid}")
    except Exception as e:
        logger.error(f"Falha no Insert: {e}")
        return False

    # Verificar se gravou corretamente
    res = db.sql_get_query("SELECT nome FROM clientes WHERE id=?", (cid,))
    if not res.empty and res.iloc[0]['nome'] == nome_perigoso:
        logger.info("✅ Leitura verificada com sucesso.")
    else:
        logger.error("❌ Dados gravados incorretamente.")
        return False

    # 2. Update seguro
    novo_nome = "O'Neil Updated"
    try:
        # A função crud_update agora espera params como tupla para o where_clause
        # where_clause: "id = ?"
        # params: (cid,)
        db.crud_update('clientes', {'nome': novo_nome}, "id = ?", (cid,), "Teste Update Seguro")
        logger.info("Update executado.")
    except Exception as e:
        logger.error(f"Falha no Update: {e}")
        return False

    res = db.sql_get_query("SELECT nome FROM clientes WHERE id=?", (cid,))
    if not res.empty and res.iloc[0]['nome'] == novo_nome:
        logger.info("✅ Update verificado com sucesso.")
    else:
        logger.error(f"❌ Falha na verificação do Update. Esperado: {novo_nome}, Encontrado: {res.iloc[0]['nome'] if not res.empty else 'Nada'}")
        return False

    return True

def test_processos_query_fix():
    """Simula a correção feita em processos.py (busca segura)."""
    logger.info("--- Testando Correção Processos ---")
    
    # Criar cliente
    nome = "Cliente Teste"
    db.crud_insert('clientes', {'nome': nome, 'link_drive': 'http://drive/link'}, "Setup Cliente")
    
    # Simular a query corrigida
    try:
        # Antes era: db.sql_get(f"SELECT ... WHERE nome='{nome}'") -> Errado
        # Agora é:
        cli_data = db.sql_get_query("SELECT link_drive FROM clientes WHERE nome=?", (nome,))
        
        if not cli_data.empty and cli_data.iloc[0]['link_drive'] == 'http://drive/link':
            logger.info("✅ Query de Processos funcionando.")
        else:
            logger.error("❌ Query de Processos falhou ou não retornou dados.")
            return False
    except Exception as e:
        logger.error(f"❌ Erro ao executar query de processos: {e}")
        return False
        
    return True

def cleanup():
    if os.path.exists('test_verification.db'):
        os.remove('test_verification.db')
    logger.info("Limpeza concluída.")

if __name__ == "__main__":
    try:
        setup_test_db()
        if test_crud_seguro() and test_processos_query_fix():
            print("\n✅ TODOS OS TESTES PASSARAM! As correções estão funcionais.")
        else:
            print("\n❌ ALGUNS TESTES FALHARAM.")
    finally:
        cleanup()
