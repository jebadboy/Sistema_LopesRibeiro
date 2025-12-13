"""
Script para RESETAR COMPLETAMENTE o banco de dados.
ATENÇÃO: APAGA TODOS OS DADOS!
Mantém apenas a estrutura das tabelas e recria o usuário Admin padrão.
"""
import sys
import os
import sqlite3
import hashlib
import time

# Adicionar diretório raiz ao path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

import database as db

# Configuração do Admin Padrão
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"
ADMIN_NOME = "Administrador"

def reset_database():
    print("="*60)
    print("  RESET GERAL DO BANCO DE DADOS  ")
    print("="*60)
    print("Isso apagará TODOS os dados de clientes, processos, financeiro, etc.")
    print("O usuário 'admin' será recriado com a senha padrão.")
    print("="*60)
    
    # Lista de todas as tabelas para limpar
    tables = [
        "clientes", 
        "processos", 
        "financeiro", 
        "andamentos", 
        "parcelas", 
        "agenda", 
        "config", 
        "cliente_timeline", 
        "documentos_drive", 
        "modelos_proposta", 
        "config_aniversarios", 
        "ai_historico", 
        "audit_logs", 
        "partes_processo", 
        "modelos_documentos", 
        "tokens_publicos", 
        "ai_insights", 
        "ai_cache", 
        "alertas_email",
        "usuarios" # Apagar também para recriar ID 1 limpo
    ]

    try:
        with db.adapter.get_connection() as conn:
            cursor = conn.cursor()
            
            # Desativar foreign keys temporariamente para evitar erros de constraint
            cursor.execute("PRAGMA foreign_keys = OFF")
            
            for table in tables:
                try:
                    # DELETE FROM apaga os dados mas mantém a estrutura
                    # Usar DELETE é mais seguro que DROP para manter triggers/indices se houver,
                    # mas se quiser zerar autoincrement teria que ser DROP ou DELETE + sqlite_sequence
                    cursor.execute(f"DELETE FROM {table}")
                    
                    # Resetar autoincrement
                    cursor.execute("DELETE FROM sqlite_sequence WHERE name=?", (table,))
                    
                    print(f"[OK] Tabela '{table}' limpa.")
                except Exception as e:
                    print(f"[--] Erro ao limpar '{table}' (pode não existir): {e}")

            cursor.execute("PRAGMA foreign_keys = ON")
            conn.commit()
            
        print("\n[INFO] Todas as tabelas foram limpas.")
        
        # Recriar Usuário Admin
        print("\n[INFO] Recriando usuário Admin...")
        
        # Gerar hash SHA-256 (compatibilidade legacy, o sistema atualiza para bcrypt no login)
        senha_hash = hashlib.sha256(ADMIN_PASS.encode()).hexdigest()
        
        with db.adapter.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO usuarios (username, password_hash, nome, role, ativo, criado_em)
                VALUES (?, ?, ?, 'admin', 1, CURRENT_TIMESTAMP)
            """, (ADMIN_USER, senha_hash, ADMIN_NOME))
            conn.commit()
            
        print(f"[SUCESSO] Usuário '{ADMIN_USER}' recriado com senha '{ADMIN_PASS}'.")
        print("="*60)
        print("SISTEMA LIMPO E PRONTO PARA USO.")
        
    except Exception as e:
        print(f"[ERRO CRÍTICO] Falha no reset: {e}")

if __name__ == "__main__":
    # Confirmação simples via argumento ou input se interativo
    if len(sys.argv) > 1 and sys.argv[1] == "--force":
        reset_database()
    else:
        confirm = input("Tem certeza que deseja apagar TUDO? Digite 'SIM': ")
        if confirm == "SIM":
            reset_database()
        else:
            print("Operação cancelada.")
