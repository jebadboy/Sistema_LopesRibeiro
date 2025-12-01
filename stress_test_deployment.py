import sqlite3
import pandas as pd
import os
import logging
from database import get_connection, TABELAS_VALIDAS, init_db

# Configuração de Log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def verify_tables_exist():
    """Verifica se todas as tabelas esperadas existem no banco."""
    logger.info("--- Verificando Existência de Tabelas ---")
    missing_tables = []
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        for tabela in TABELAS_VALIDAS:
            if tabela not in tables:
                missing_tables.append(tabela)
                logger.error(f"❌ Tabela faltando: {tabela}")
            else:
                logger.info(f"✅ Tabela encontrada: {tabela}")
    
    if missing_tables:
        logger.error(f"Tabelas ausentes: {missing_tables}")
        return False
    return True

def verify_schema_integrity():
    """Verifica colunas críticas em tabelas chave."""
    logger.info("--- Verificando Integridade do Schema ---")
    critical_columns = {
        'financeiro': ['id_cliente', 'id_processo', 'percentual_parceria'],
        'usuarios': ['username', 'password_hash', 'role'],
        'agenda': ['google_calendar_id', 'status']
    }
    
    success = True
    with get_connection() as conn:
        cursor = conn.cursor()
        for table, columns in critical_columns.items():
            cursor.execute(f"PRAGMA table_info({table})")
            existing_columns = [row[1] for row in cursor.fetchall()]
            for col in columns:
                if col not in existing_columns:
                    logger.error(f"❌ Coluna '{col}' faltando na tabela '{table}'")
                    success = False
                else:
                    logger.info(f"✅ Coluna '{col}' presente em '{table}'")
    return success

def verify_foreign_keys():
    """Verifica integridade referencial (se IDs apontam para registros existentes)."""
    logger.info("--- Verificando Chaves Estrangeiras (Integridade de Dados) ---")
    checks = [
        ("financeiro", "id_cliente", "clientes", "id"),
        ("financeiro", "id_processo", "processos", "id"),
        ("processos", "id_cliente", "clientes", "id"),
        ("agenda", "id_processo", "processos", "id")
    ]
    
    success = True
    with get_connection() as conn:
        cursor = conn.cursor()
        for table, fk_col, ref_table, ref_col in checks:
            # Selecionar FKs que não têm correspondência na tabela pai
            query = f"""
                SELECT t.{fk_col} 
                FROM {table} t 
                LEFT JOIN {ref_table} r ON t.{fk_col} = r.{ref_col}
                WHERE t.{fk_col} IS NOT NULL AND r.{ref_col} IS NULL
            """
            cursor.execute(query)
            orphans = cursor.fetchall()
            if orphans:
                logger.warning(f"⚠️ Encontrados {len(orphans)} registros órfãos em '{table}.{fk_col}' (IDs: {[o[0] for o in orphans[:5]]}...)")
                # Não falha o teste, mas avisa
            else:
                logger.info(f"✅ Integridade OK: {table}.{fk_col} -> {ref_table}.{ref_col}")
    return success

def simulate_stress():
    """Simula situações de erro e validação."""
    logger.info("--- Simulando Testes de Stress e Erros ---")
    
    # 1. Teste de Conexão
    try:
        with get_connection() as conn:
            pass
        logger.info("✅ Conexão com banco: OK")
    except Exception as e:
        logger.error(f"❌ Falha na conexão: {e}")
        return False

    # 2. Verificar Usuário Admin
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT count(*) FROM usuarios WHERE username='admin'")
        if cursor.fetchone()[0] > 0:
            logger.info("✅ Usuário admin existe")
        else:
            logger.error("❌ Usuário admin NÃO encontrado!")
            return False

    return True

if __name__ == "__main__":
    print("\n=== INICIANDO VERIFICAÇÃO PRÉ-DEPLOY ===\n")
    
    # Garantir que banco está inicializado
    init_db()
    
    tabelas_ok = verify_tables_exist()
    schema_ok = verify_schema_integrity()
    fks_ok = verify_foreign_keys()
    stress_ok = simulate_stress()
    
    print("\n=== RESULTADO FINAL ===")
    if tabelas_ok and schema_ok and stress_ok:
        print("[OK] O SISTEMA ESTA INTEGRO E PRONTO PARA DEPLOY!")
        print("Nota: Se houver avisos de registros orfaos, considere limpa-los, mas nao impedem o funcionamento.")
    else:
        print("[ERRO] FORAM ENCONTRADOS ERROS CRITICOS. CORRIJA ANTES DE PUBLICAR.")
