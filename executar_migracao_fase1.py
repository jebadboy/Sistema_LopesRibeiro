#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de Migração - Fase 1
Este script executa todas as migrações críticas da Fase 1
"""

import sys
import os

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database as db

def main():
    print("=" * 60)
    print("MIGRACAO FASE 1 - Sistema Lopes Ribeiro")
    print("=" * 60)
    print()
    
    # 1. Criar backup antes de migrar
    print("[1/3] Criando backup de seguranca...")
    try:
        resultado_backup = db.criar_backup()
        print(f"[OK] {resultado_backup}")
    except Exception as e:
        print(f"[ERRO] Erro ao criar backup: {e}")
        print("ATENCAO: Recomendo nao prosseguir sem backup!")
        resposta = input("Deseja continuar mesmo assim? (s/N): ")
        if resposta.lower() != 's':
            print("Migracao cancelada.")
            return
    
    print()
    
    # 2. Executar migração para adicionar id_cliente
    print("[2/3] Adicionando coluna id_cliente a tabela financeiro...")
    try:
        resultado = db.migrar_adicionar_id_cliente_financeiro()
        print(f"[OK] {resultado}")
    except Exception as e:
        print(f"[ERRO] Erro na migracao: {e}")
        print("ATENCAO: A base de dados pode estar em estado inconsistente!")
        return
    
    print()
    
    # 3. Verificar estrutura
    print("[3/3] Verificando estrutura da tabela financeiro...")
    try:
        import sqlite3
        conn = sqlite3.connect('dados_escritorio.db')
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(financeiro)")
        colunas = cursor.fetchall()
        
        print("\nColunas da tabela financeiro:")
        print("-" * 60)
        for col in colunas:
            print(f"  - {col[1]} ({col[2]})")
        
        # Verificar se id_cliente existe
        nomes_colunas = [col[1] for col in colunas]
        if 'id_cliente' in nomes_colunas:
            print("\n[OK] Coluna 'id_cliente' foi adicionada com sucesso!")
        else:
            print("\n[ERRO] Coluna 'id_cliente' NAO foi encontrada!")
        
        if 'mes_referencia' in nomes_colunas:
            print("[OK] Coluna 'mes_referencia' foi adicionada com sucesso!")
        
        if 'ano_referencia' in nomes_colunas:
            print("[OK] Coluna 'ano_referencia' foi adicionada com sucesso!")
        
        conn.close()
        
    except Exception as e:
        print(f"[ERRO] Erro ao verificar: {e}")
        return
    
    print()
    print("=" * 60)
    print("MIGRACAO CONCLUIDA COM SUCESSO!")
    print("=" * 60)
    print()
    print("PROXIMOS PASSOS:")
    print("1. Os dados existentes na tabela 'financeiro' nao foram migrados")
    print("2. Voce precisara vincular os lancamentos financeiros aos clientes")
    print("3. Recomendo executar um script de migracao de dados manual")
    print()

if __name__ == "__main__":
    main()
