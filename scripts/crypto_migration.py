"""
Script de Migração de Criptografia de CPFs

Este script criptografa todos os CPF/CNPJ existentes no banco de dados
usando o módulo crypto.py.

IMPORTANTE: Faça backup do banco antes de executar!

Uso: python scripts/crypto_migration.py [--dry-run | --execute]
"""

import argparse
import logging
import sys
import os

# Adicionar pasta raiz ao path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database as db
import crypto

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def migrate_clientes(dry_run: bool = True):
    """Migra CPF/CNPJ da tabela clientes para formato criptografado."""
    print("\n" + "="*60)
    print("[CRYPTO] MIGRACAO DE CRIPTOGRAFIA - CLIENTES")
    print("="*60)
    
    if not crypto.is_crypto_available():
        print("[ERRO] Biblioteca cryptography nao disponivel!")
        print("   Execute: pip install cryptography")
        return 0
    
    clientes = db.sql_get_query("""
        SELECT id, nome, cpf_cnpj 
        FROM clientes 
        WHERE cpf_cnpj IS NOT NULL AND cpf_cnpj != '' AND cpf_cnpj NOT LIKE 'ENC:%'
    """)
    
    if clientes.empty:
        print("[OK] Nenhum CPF/CNPJ precisa ser criptografado.")
        return 0
    
    print(f"\n[INFO] Encontrados {len(clientes)} registros para criptografar")
    if dry_run:
        print("\n[SIMULACAO - Nenhuma alteracao sera feita]\n")
    
    success = 0
    for _, row in clientes.iterrows():
        cpf_criptografado = crypto.encrypt(row['cpf_cnpj'])
        if dry_run:
            masked = crypto.mask_document(row['cpf_cnpj'])
            print(f"   ID {row['id']}: {masked} -> [ENCRYPTED]")
            success += 1
        else:
            try:
                db.sql_run("UPDATE clientes SET cpf_cnpj = ? WHERE id = ?", (cpf_criptografado, row['id']))
                success += 1
            except Exception as e:
                logger.error(f"Erro no cliente {row['id']}: {e}")
    
    print(f"\n{'[SIMULACAO] ' if dry_run else ''}Sucesso: {success}")
    return success


def verify_encryption():
    """Verifica status da criptografia no banco."""
    print("\n[STATUS] CRIPTOGRAFIA DE CPFs")
    total = db.sql_get_query("SELECT COUNT(*) as t FROM clientes WHERE cpf_cnpj IS NOT NULL AND cpf_cnpj != ''")
    enc = db.sql_get_query("SELECT COUNT(*) as t FROM clientes WHERE cpf_cnpj LIKE 'ENC:%'")
    t, e = total.iloc[0]['t'], enc.iloc[0]['t']
    print(f"   Total: {t} | Criptografados: {e} | Pendentes: {t-e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migração de Criptografia")
    parser.add_argument('--dry-run', action='store_true', help='Simular')
    parser.add_argument('--execute', action='store_true', help='Executar')
    parser.add_argument('--verify', action='store_true', help='Verificar')
    args = parser.parse_args()
    
    db.init_db()
    
    if args.verify:
        verify_encryption()
    elif args.execute:
        confirm = input("Digite 'CONFIRMAR' para prosseguir: ")
        if confirm == "CONFIRMAR":
            migrate_clientes(dry_run=False)
            verify_encryption()
        else:
            print("Cancelado.")
    elif args.dry_run:
        migrate_clientes(dry_run=True)
    else:
        parser.print_help()
