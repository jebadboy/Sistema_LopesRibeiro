import sys
import os
import logging
import time

# Adicionar diretório raiz ao path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import database as db
import modules.ai_proactive as ai_proactive
import modules.signals as signals

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_proactive_ai():
    print("--- Iniciando Verificação de IA Proativa ---")
    
    # 1. Inicializar Banco e IA
    db.init_db()
    ai_proactive.inicializar()
    
    # Limpar insights anteriores de teste
    db.sql_run("DELETE FROM ai_insights WHERE titulo LIKE 'Cadastro Incompleto%' OR titulo LIKE 'Estratégia Processual%' OR titulo LIKE 'Alerta de Alta Despesa%'")
    
    # 2. Simular Evento: Novo Cliente (Sem CPF - Regra Básica)
    print("\n[Teste 1] Novo Cliente sem CPF (Regra Básica)")
    cliente_incompleto = {
        'nome': 'Cliente Teste Incompleto',
        'email': 'teste@email.com'
        # CPF faltando propositalmente
    }
    # Simular inserção e pegar ID (mockado)
    signals.emit('insert_clientes', {'id': 999, 'data': cliente_incompleto})
    
    # Verificar se insight foi criado
    insights = db.sql_get_query("SELECT * FROM ai_insights WHERE titulo LIKE 'Cadastro Incompleto%'")
    if not insights.empty:
        print("[OK] Insight de cadastro incompleto gerado com sucesso!")
        print(insights.iloc[-1][['titulo', 'descricao']].to_dict())
    else:
        print("[ERRO] Falha ao gerar insight de cadastro incompleto.")

    # 3. Simular Evento: Novo Processo (Regra Gemini)
    print("\n[Teste 2] Novo Processo (Regra Gemini)")
    processo_novo = {
        'numero': '0001234-55.2024.8.19.0001',
        'acao': 'Divórcio Litigioso',
        'area': 'Família'
    }
    signals.emit('insert_processos', {'id': 888, 'data': processo_novo})
    
    # Aguardar um pouco pois a chamada da API pode demorar
    time.sleep(2)
    
    # Verificar se insight foi criado
    insights_proc = db.sql_get_query("SELECT * FROM ai_insights WHERE titulo LIKE 'Estratégia Processual%' OR titulo LIKE 'Novo Processo Iniciado'")
    if not insights_proc.empty:
        print("[OK] Insight de processo gerado com sucesso!")
        print(insights_proc.iloc[-1][['titulo', 'descricao']].to_dict())
    else:
        print("[ERRO] Falha ao gerar insight de processo.")

    # 4. Simular Evento: Financeiro Alto (Regra Híbrida)
    print("\n[Teste 3] Saída Financeira Alta")
    financeiro_alto = {
        'valor': 15000.00,
        'tipo': 'Saída',
        'categoria': 'Equipamentos',
        'descricao': 'Compra de Servidores'
    }
    signals.emit('insert_financeiro', {'id': 777, 'data': financeiro_alto})
    
    time.sleep(2)

    insights_fin = db.sql_get_query("SELECT * FROM ai_insights WHERE titulo LIKE 'Alerta de Alta Despesa%'")
    if not insights_fin.empty:
        print("[OK] Insight financeiro gerado com sucesso!")
        print(insights_fin.iloc[-1][['titulo', 'descricao']].to_dict())
    else:
        print("[ERRO] Falha ao gerar insight financeiro.")

if __name__ == "__main__":
    verify_proactive_ai()
