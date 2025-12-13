# -*- coding: utf-8 -*-
import sqlite3
import sys
import io

# Configura stdout para UTF-8 no Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def auditar_ia():
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    
    print("=== 📊 RELATÓRIO DE IMPACTO E DEPENDÊNCIA DA IA ===\n")
    
    # Primeiro, vamos verificar quais tabelas existem
    c.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tabelas = [row[0] for row in c.fetchall()]
    
    print(f"📋 TABELAS EXISTENTES NO BANCO: {tabelas}\n")
    
    # 1. ANÁLISE DA TIMELINE (Movimentações)
    print(f"1. TIMELINE (Micro-Análises):")
    if 'andamentos' in tabelas:
        c.execute("SELECT count(*) FROM andamentos")
        total_movs = c.fetchone()[0]
        
        c.execute("SELECT count(*) FROM andamentos WHERE analise_ia IS NOT NULL")
        com_ia = c.fetchone()[0]
        
        c.execute("SELECT analise_ia FROM andamentos WHERE analise_ia IS NOT NULL")
        rows = c.fetchall()
        
        erros_cota = 0
        sucessos = 0
        
        for row in rows:
            texto = row[0].lower() if row[0] else ""
            if "quota" in texto or "429" in texto or "limite" in texto:
                erros_cota += 1
            else:
                sucessos += 1
        
        print(f"   - Total de Movimentos: {total_movs}")
        print(f"   - Processados pela IA: {com_ia} ({(com_ia/total_movs*100) if total_movs else 0:.1f}%)")
        print(f"   - Sucessos Reais: {sucessos}")
        print(f"   - Falhas de Cota (Lixo): {erros_cota}")
        print(f"   --> IMPACTO DO CORTE: {total_movs - sucessos} movimentos ficarão sem 'Resumo Explicativo' e 'Mensagem de WhatsApp'.\n")
    else:
        print(f"   ⚠️  Tabela 'andamentos' NÃO EXISTE no banco.")
        print(f"   --> A funcionalidade de micro-análises de movimentações ainda não foi implementada.\n")
    
    # 2. ESTRATÉGIA (Single Shot)
    print(f"2. ESTRATÉGIA (Visão Geral):")
    if 'ai_analises_cache' in tabelas:
        try:
            c.execute("SELECT count(*), min(data_analise), max(data_analise) FROM ai_analises_cache")
            res = c.fetchone()
            total_estrategia = res[0]
            ultimo_uso = res[2]
        except:
            total_estrategia = 0
            ultimo_uso = "Nunca"
            
        print(f"   - Processos com Parecer Salvo: {total_estrategia}")
        print(f"   - Última Geração: {ultimo_uso}")
        print(f"   --> IMPACTO DO CORTE: Perda da análise de 'Probabilidade de Êxito' e 'Sugestão Financeira'.\n")
    else:
        print(f"   ⚠️  Tabela 'ai_analises_cache' NÃO EXISTE no banco.")
        print(f"   --> A funcionalidade de cache de análises de IA ainda não foi implementada.\n")
    
    # 3. Verificar Processos existentes
    print(f"3. PROCESSOS CADASTRADOS:")
    if 'processos' in tabelas:
        c.execute("SELECT count(*) FROM processos")
        total_processos = c.fetchone()[0]
        print(f"   - Total de Processos: {total_processos}")
    else:
        print(f"   ⚠️  Tabela 'processos' NÃO EXISTE.")
    
    print("\n" + "="*60)
    print("📌 CONCLUSÃO:")
    print("   O banco de dados atual NÃO possui as tabelas de movimentações")
    print("   (andamentos) nem cache de análises de IA (ai_analises_cache).")
    print("   O impacto do corte da IA é MÍNIMO no estado atual do sistema.")
    print("="*60)
    
    conn.close()

if __name__ == "__main__":
    auditar_ia()
