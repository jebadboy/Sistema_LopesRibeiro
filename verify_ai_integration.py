import sys
import os

# Adicionar diretório atual ao path
sys.path.append(os.getcwd())

import database as db
import modules.ai_proactive as ai
import time

def test_ai_integration():
    print("Iniciando teste de integração da IA Proativa...")
    
    # 1. Inicializar Banco de Dados
    db.init_db()
    print("Banco de dados inicializado.")
    
    # 2. Inicializar IA
    ai.inicializar()
    print("IA inicializada.")
    
    # 3. Simular Evento: Novo Cliente sem CPF (deve gerar insight)
    print("Simulando cadastro de cliente sem CPF...")
    cliente_data = {
        'nome': 'Cliente Teste IA',
        'email': 'teste@exemplo.com',
        'cpf_cnpj': '' # Vazio para disparar regra
    }
    
    # Inserir cliente (isso deve disparar o sinal 'insert_clientes')
    # Como o sinal é síncrono no código atual (chamada direta), podemos verificar logo em seguida
    try:
        db.crud_insert('clientes', cliente_data, log_msg="Cliente de teste inserido")
        print("Cliente inserido.")
    except Exception as e:
        print(f"Erro ao inserir cliente: {e}")
        return

    # 4. Verificar se o Insight foi gerado
    print("Verificando tabela ai_insights...")
    insights = db.sql_get_query("SELECT * FROM ai_insights WHERE titulo LIKE 'Cadastro Incompleto%' ORDER BY id DESC LIMIT 1")
    
    if not insights.empty:
        print("SUCESSO: Insight gerado corretamente!")
        print(f"Título: {insights.iloc[0]['titulo']}")
        print(f"Descrição: {insights.iloc[0]['descricao']}")
        
        # Limpar dados de teste
        print("Limpando dados de teste...")
        db.crud_delete('clientes', "nome = ?", ('Cliente Teste IA',), log_msg="Removendo cliente teste")
        db.crud_delete('ai_insights', "id = ?", (insights.iloc[0]['id'],), log_msg="Removendo insight teste")
    else:
        print("FALHA: Nenhum insight gerado.")

if __name__ == "__main__":
    test_ai_integration()
