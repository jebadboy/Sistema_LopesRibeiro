# -*- coding: utf-8 -*-
"""
Script de teste para verificar a criação das tabelas no database.py (Fase 1)
"""

import os
import sys
import sqlite3

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_database_schema():
    """Testa se todas as tabelas foram criadas corretamente"""
    
    # Renomear DB existente para backup
    db_file = 'dados_escritorio.db'
    if os.path.exists(db_file):
        backup_name = f'{db_file}.backup_fase1'
        if os.path.exists(backup_name):
            os.remove(backup_name)
        os.rename(db_file, backup_name)
        print(f"[OK] Backup do banco existente criado: {backup_name}")
    
    # Importar e inicializar o database
    try:
        import database as db
        print("[OK] Modulo database importado com sucesso")
        
        # Inicializar o banco
        db.init_db()
        print("[OK] init_db() executado sem erros")
        
        # Conectar ao banco e verificar tabelas
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Lista de tabelas esperadas
        tabelas_esperadas = [
            'usuarios',
            'clientes',
            'processos',
            'financeiro',  # NOVA
            'andamentos',  # CORRIGIDA
            'parcelas',    # NOVA
            'agenda',      # NOVA
            'config',      # NOVA
            'cliente_timeline',  # NOVA
            'documentos_drive',  # NOVA
            'modelos_proposta',
            'config_aniversarios'
        ]
        
        # Buscar todas as tabelas criadas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tabelas_criadas = [row[0] for row in cursor.fetchall()]
        
        print("\nVerificando tabelas...")
        print("-" *60)
        
        todas_ok = True
        for tabela in tabelas_esperadas:
            if tabela in tabelas_criadas:
                cursor.execute(f"PRAGMA table_info({tabela})")
                colunas = cursor.fetchall()
                print(f"[OK] {tabela} - CRIADA ({len(colunas)} colunas)")
            else:
                print(f"[ERRO] {tabela} - NAO ENCONTRADA")
                todas_ok = False
        
        print("-" * 60)
        
        # Verificar estrutura específica da tabela andamentos (corrigida)
        print("\nVerificando correcao da tabela 'andamentos'...")
        cursor.execute("PRAGMA table_info(andamentos)")
        colunas_andamentos = cursor.fetchall()
        
        colunas_nomes = [col[1] for col in colunas_andamentos]
        
        # Verificar que NÃO tem as colunas erradas
        colunas_erradas = ['numero_parcela', 'total_parcelas', 'valor_parcela', 
                          'vencimento', 'status_parcela', 'pago_em', 'id_lancamento_financeiro']
        
        tem_erro = False
        for col in colunas_erradas:
            if col in colunas_nomes:
                print(f"   [ERRO] Coluna errada encontrada: {col}")
                tem_erro = True
        
        if not tem_erro:
            print("   [OK] Tabela andamentos CORRIGIDA (sem colunas de parcelas)")
        
        # Verificar que TEM as colunas corretas
        colunas_corretas = ['id', 'id_processo', 'data', 'descricao', 'tipo', 'responsavel', 'criado_em']
        for col in colunas_corretas:
            if col in colunas_nomes:
                print(f"   [OK] Coluna correta: {col}")
            else:
                print(f"   [ERRO] Coluna ausente: {col}")
                todas_ok = False
        
        # Verificar tabela parcelas (nova)
        print("\nVerificando nova tabela 'parcelas'...")
        cursor.execute("PRAGMA table_info(parcelas)")
        colunas_parcelas = cursor.fetchall()
        colunas_parcelas_nomes = [col[1] for col in colunas_parcelas]
        
        colunas_esperadas_parcelas = ['id', 'id_lancamento_financeiro', 'numero_parcela', 
                                     'total_parcelas', 'valor_parcela', 'vencimento', 
                                     'status_parcela', 'pago_em', 'obs']
        
        for col in colunas_esperadas_parcelas:
            if col in colunas_parcelas_nomes:
                print(f"   [OK] Coluna: {col}")
            else:
                print(f"   [ERRO] Coluna ausente: {col}")
                todas_ok = False
        
        # Verificar tabela cliente_timeline
        print("\nVerificando nova tabela 'cliente_timeline'...")
        cursor.execute("PRAGMA table_info(cliente_timeline)")
        colunas_timeline = cursor.fetchall()
        colunas_timeline_nomes = [col[1] for col in colunas_timeline]
        
        colunas_esperadas_timeline = ['id', 'cliente_id', 'tipo_evento', 'titulo', 
                                      'descricao', 'icone', 'data_evento']
        
        for col in colunas_esperadas_timeline:
            if col in colunas_timeline_nomes:
                print(f"   [OK] Coluna: {col}")
            else:
                print(f"   [ERRO] Coluna ausente: {col}")
                todas_ok = False
        
        conn.close()
        
        print("\n" + "=" * 60)
        if todas_ok:
            print("[SUCESSO] TESTE PASSOU! Todas as tabelas foram criadas corretamente.")
            print("=" * 60)
            return True
        else:
            print("[FALHA] TESTE FALHOU! Algumas tabelas ou colunas estao faltando.")
            print("=" * 60)
            return False
            
    except Exception as e:
        print(f"\n[ERRO] durante o teste: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TESTE DE SCHEMA DO DATABASE - FASE 1")
    print("=" * 60)
    print()
    
    sucesso = test_database_schema()
    
    if sucesso:
        print("\nFase 1 concluida com sucesso!")
        print("Voce pode agora testar o sistema executando: python app.py")
    else:
        print("\nCorreja os erros acima antes de prosseguir.")
    
    sys.exit(0 if sucesso else 1)
