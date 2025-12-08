"""
Script de Simulação de Eventos para Teste da IA Proativa
"""
import database as db
import modules.signals as signals
import modules.ai_proactive as ai_proactive
import time
import pandas as pd

def run_simulation():
    print("--- Iniciando Simulação ---")
    
    # 1. Inicializar Banco e IA
    db.init_db()
    ai_proactive.inicializar()
    print("✅ Sistema inicializado.")
    
    # 2. Simular Criação de Cliente sem CPF (Deve gerar insight)
    print("\n--- Simulando Cliente Incompleto ---")
    cliente_data = {
        'nome': 'Cliente Teste Simulação',
        'email': 'teste@exemplo.com',
        # 'cpf_cnpj': Falta propositalmente
        'status_cliente': 'EM NEGOCIAÇÃO'
    }
    # Usamos crud_insert diretamente para disparar o sinal
    id_cliente = db.crud_insert('clientes', cliente_data, log_msg="Cliente Simulado Criado")
    print(f"Cliente criado com ID: {id_cliente}")
    
    # 3. Simular Nova Despesa Alta (Deve gerar insight)
    print("\n--- Simulando Despesa Alta ---")
    financeiro_data = {
        'data': '2024-01-01',
        'tipo': 'Saída',
        'categoria': 'Equipamentos',
        'descricao': 'Compra de Servidor',
        'valor': 15000.00, # Valor alto
        'status_pagamento': 'Pendente'
    }
    id_fin = db.crud_insert('financeiro', financeiro_data, log_msg="Despesa Simulada Criada")
    print(f"Despesa criada com ID: {id_fin}")

    # 4. Verificar Insights Gerados
    print("\n--- Verificando Insights Gerados ---")
    time.sleep(1) # Garantir que houve tempo (embora seja síncrono por enquanto)
    
    insights = db.sql_get_query("SELECT * FROM ai_insights ORDER BY id DESC LIMIT 5")
    
    if not insights.empty:
        print(f"Encontrados {len(insights)} insights:")
        for _, row in insights.iterrows():
            print(f"[{row['id']}] {row['prioridade'].upper()} - {row['titulo']}: {row['descricao']}")
    else:
        print("❌ Nenhum insight encontrado!")

    # 5. Limpeza (Opcional, mas bom para não sujar muito o banco de teste)
    # db.crud_delete('clientes', 'id = ?', (id_cliente,), "Removendo cliente teste")
    # db.crud_delete('financeiro', 'id = ?', (id_fin,), "Removendo despesa teste")
    # db.sql_run("DELETE FROM ai_insights WHERE id IN (SELECT id FROM ai_insights ORDER BY id DESC LIMIT 2)")
    # print("\n✅ Dados de teste limpos (comentado para verificação manual).")

if __name__ == "__main__":
    run_simulation()
