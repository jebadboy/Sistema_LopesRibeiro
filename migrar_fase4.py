"""
MIGRAÇÃO FASE 4 - Correções do Code Review
Sistema Lopes Ribeiro

Este script adiciona colunas faltantes na tabela financeiro:
- id_cliente (FK para clientes)
- id_processo (FK para processos)
- percentual_parceria (REAL)

IMPORTANTE: Execute este script APENAS UMA VEZ antes de usar a nova versão do sistema.
"""

import sqlite3
import shutil
from datetime import datetime
import os

DB_NAME = 'dados_escritorio.db'

def criar_backup():
    """Cria backup de segurança antes da migração"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = "backups"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    backup_name = f"{backup_dir}/backup_pre_fase4_{timestamp}.db"
    
    try:
        shutil.copy(DB_NAME, backup_name)
        print(f"[OK] Backup criado: {backup_name}")
        return backup_name
    except Exception as e:
        print(f"[ERRO] Falha ao criar backup: {e}")
        raise

def verificar_colunas_existentes():
    """Verifica quais colunas já existem na tabela financeiro"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("PRAGMA table_info(financeiro)")
    colunas = [col[1] for col in c.fetchall()]
    conn.close()
    return colunas

def executar_migracao():
    """Executa a migração adicionando colunas faltantes"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    colunas_existentes = verificar_colunas_existentes()
    print(f"[INFO] Colunas atuais: {', '.join(colunas_existentes)}")
    
    try:
        # Adicionar id_cliente
        if 'id_cliente' not in colunas_existentes:
            print("[...] Adicionando coluna id_cliente")
            c.execute("ALTER TABLE financeiro ADD COLUMN id_cliente INTEGER")
            print("[OK] Coluna id_cliente adicionada")
        else:
            print("[SKIP] Coluna id_cliente ja existe")
        
        # Adicionar id_processo
        if 'id_processo' not in colunas_existentes:
            print("[...] Adicionando coluna id_processo")
            c.execute("ALTER TABLE financeiro ADD COLUMN id_processo INTEGER")
            print("[OK] Coluna id_processo adicionada")
        else:
            print("[SKIP] Coluna id_processo ja existe")
        
        # Adicionar percentual_parceria
        if 'percentual_parceria' not in colunas_existentes:
            print("[...] Adicionando coluna percentual_parceria")
            c.execute("ALTER TABLE financeiro ADD COLUMN percentual_parceria REAL DEFAULT 0.0")
            print("[OK] Coluna percentual_parceria adicionada")
        else:
            print("[SKIP] Coluna percentual_parceria ja existe")
        
        conn.commit()
        print("\n[SUCESSO] Migracao concluida!")
        
        # Verificar resultado
        c.execute("PRAGMA table_info(financeiro)")
        colunas_novas = [col[1] for col in c.fetchall()]
        print(f"[INFO] Colunas apos migracao: {', '.join(colunas_novas)}")
        
    except Exception as e:
        conn.rollback()
        print(f"\n[ERRO] Falha na migracao: {e}")
        raise
    finally:
        conn.close()

def main():
    print("=" * 60)
    print(" MIGRACAO FASE 4 - Sistema Lopes Ribeiro")
    print("=" * 60)
    print()
    
    if not os.path.exists(DB_NAME):
        print(f"[ERRO] Banco de dados nao encontrado: {DB_NAME}")
        print("Execute o sistema ao menos uma vez antes de rodar a migracao.")
        return
    
    # Criar backup
    print("[1/2] Criando backup de seguranca...")
    backup_path = criar_backup()
    print()
    
    # Executar migração
    print("[2/2] Executando migracao...")
    executar_migracao()
    print()
    
    print("=" * 60)
    print(" PROXIMO PASSO:")
    print(" Execute: streamlit run app.py")
    print("=" * 60)

if __name__ == "__main__":
    main()
