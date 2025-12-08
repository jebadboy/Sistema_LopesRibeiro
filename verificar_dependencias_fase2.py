# -*- coding: utf-8 -*-
"""
Script de teste para verificar dependências do módulo clientes (Fase 2)
"""

import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_utils_functions():
    """Testa se todas as funções necessárias de utils.py existem"""
    
    try:
        import utils as ut
        print("[OK] Modulo utils importado com sucesso")
        
        # Lista de funções necessárias para o módulo clientes
        funcoes_necessarias = [
            'formatar_documento',
            'formatar_celular',
            'safe_float',
            'safe_int',
            'criar_doc',
            'buscar_cep',
            'limpar_numeros',
            'validar_cpf_matematico',
            'validar_cnpj'
        ]
        
        print("\nVerificando funcoes do utils.py...")
        print("-" * 60)
        
        funcoes_ausentes = []
        for funcao in funcoes_necessarias:
            if hasattr(ut, funcao):
                print(f"[OK] {funcao}")
            else:
                print(f"[ERRO] {funcao} - NAO ENCONTRADA")
                funcoes_ausentes.append(funcao)
        
        print("-" * 60)
        
        if funcoes_ausentes:
            print(f"\n[FALHA] {len(funcoes_ausentes)} funcoes ausentes: {', '.join(funcoes_ausentes)}")
            return False
        else:
            print("\n[SUCESSO] Todas as funcoes necessarias existem!")
            return True
            
    except Exception as e:
        print(f"\n[ERRO] durante o teste: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_components():
    """Testa se os componentes necessários existem"""
    
    try:
        from components.cliente_styles import get_cliente_css
        print("\n[OK] Componente cliente_styles importado com sucesso")
        
        # Testar se get_cliente_css retorna algo
        css = get_cliente_css()
        if css and len(css) > 0:
            print(f"[OK] get_cliente_css retorna CSS ({len(css)} caracteres)")
            return True
        else:
            print("[ERRO] get_cliente_css retorna vazio")
            return False
            
    except Exception as e:
        print(f"\n[ERRO] ao importar componente: {e}")
        return False

def test_database_functions():
    """Testa se o database.py tem as funções necessárias"""
    
    try:
        import database as db
        print("\n[OK] Modulo database importado com sucesso")
        
        funcoes_db_necessarias = [
            'sql_get',
            'sql_run',
            'sql_get_query',
            'get_config',
            'set_config',
            'cpf_existe'
        ]
        
        print("\nVerificando funcoes do database.py...")
        print("-" * 60)
        
        funcoes_ausentes = []
        for funcao in funcoes_db_necessarias:
            if hasattr(db, funcao):
                print(f"[OK] {funcao}")
            else:
                print(f"[ERRO] {funcao} - NAO ENCONTRADA")
                funcoes_ausentes.append(funcao)
        
        print("-" * 60)
        
        if funcoes_ausentes:
            print(f"\n[FALHA] {len(funcoes_ausentes)} funcoes ausentes: {', '.join(funcoes_ausentes)}")
            return False
        else:
            print("\n[SUCESSO] Todas as funcoes do database necessarias existem!")
            return True
            
    except Exception as e:
        print(f"\n[ERRO] durante o teste: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TESTE DE DEPENDENCIAS - FASE 2")
    print("=" * 60)
    print()
    
    resultado_utils = test_utils_functions()
    resultado_components = test_components()
    resultado_database = test_database_functions()
    
    sucesso = resultado_utils and resultado_components and resultado_database
    
    if sucesso:
        print("\n" + "=" * 60)
        print("[SUCESSO] Todas as dependencias estao OK!")
        print("=" * 60)
        print("\nFase 2 concluida com sucesso!")
    else:
        print("\n" + "=" * 60)
        print("[FALHA] Algumas dependencias estao faltando")
        print("=" * 60)
        print("\nCorreja os erros acima antes de prosseguir.")
    
    sys.exit(0 if sucesso else 1)
