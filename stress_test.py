import database as db
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import random
import logging
import time
import concurrent.futures

# Configuração de Log
logging.basicConfig(
    filename='stress_test.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

def setup_stress_test():
    """Prepara o ambiente para o teste."""
    print("Iniciando preparação para Teste de Estresse...")
    try:
        # Criar cliente de teste
        dados_cliente = {
            "nome": "[STRESS_TEST] Cliente Dummy",
            "cpf_cnpj": "000.000.000-00",
            "email": "stress@test.com",
            "telefone": "11999999999"
        }
        id_cliente = db.crud_insert("clientes", dados_cliente, "Setup Stress Test")
        print(f"Cliente de teste criado com ID: {id_cliente}")
        return id_cliente
    except Exception as e:
        logger.error(f"Falha no setup: {e}")
        return None

def teste_insercao_massiva(id_cliente, qtd=500):
    """Insere uma grande quantidade de registros financeiros."""
    print(f"Iniciando inserção massiva de {qtd} registros...")
    inicio = time.time()
    
    sucessos = 0
    erros = 0
    
    for i in range(qtd):
        try:
            tipo = random.choice(["Entrada", "Saída"])
            dados = {
                "data": datetime.now().strftime("%Y-%m-%d"),
                "tipo": tipo,
                "categoria": "Honorários" if tipo == "Entrada" else "Despesa Operacional",
                "descricao": f"[STRESS_TEST] Lançamento {i}",
                "valor": round(random.uniform(100.0, 5000.0), 2),
                "responsavel": "Tester",
                "status_pagamento": random.choice(["Pago", "Pendente"]),
                "vencimento": (datetime.now() + relativedelta(days=random.randint(-30, 60))).strftime("%Y-%m-%d"),
                "id_cliente": id_cliente,
                "centro_custo": "Escritório",
                "recorrente": 0
            }
            db.crud_insert("financeiro", dados, "Stress Test Insert")
            sucessos += 1
        except Exception as e:
            logger.error(f"Erro na inserção {i}: {e}")
            erros += 1
            
    fim = time.time()
    tempo_total = fim - inicio
    print(f"Inserção Massiva Concluída: {sucessos} sucessos, {erros} erros.")
    print(f"Tempo Total: {tempo_total:.2f}s ({sucessos/tempo_total:.2f} ops/s)")

def teste_concorrencia(id_cliente, threads=5, ops_por_thread=50):
    """Simula múltiplos usuários inserindo dados simultaneamente."""
    print(f"Iniciando teste de concorrência ({threads} threads, {ops_por_thread} ops/thread)...")
    
    def worker(thread_id):
        local_sucessos = 0
        for i in range(ops_por_thread):
            try:
                dados = {
                    "data": datetime.now().strftime("%Y-%m-%d"),
                    "tipo": "Saída",
                    "categoria": "Concorrência",
                    "descricao": f"[STRESS_TEST] Thread {thread_id} - {i}",
                    "valor": 50.0,
                    "responsavel": "Tester",
                    "status_pagamento": "Pendente",
                    "vencimento": datetime.now().strftime("%Y-%m-%d"),
                    "id_cliente": id_cliente
                }
                db.crud_insert("financeiro", dados, f"Thread {thread_id}")
                local_sucessos += 1
            except Exception as e:
                logger.error(f"Erro na Thread {thread_id}: {e}")
        return local_sucessos

    inicio = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        resultados = list(executor.map(worker, range(threads)))
    
    fim = time.time()
    total_ops = sum(resultados)
    tempo = fim - inicio
    
    print(f"Concorrência Concluída: {total_ops} operações bem-sucedidas.")
    print(f"Tempo Total: {tempo:.2f}s ({total_ops/tempo:.2f} ops/s)")

def teste_parcelamento_longo(id_cliente):
    """Testa a geração de um parcelamento muito longo (120x)."""
    print("Testando parcelamento longo (120x)...")
    try:
        # Simular chamada da lógica de parcelamento (que está no frontend, mas vamos replicar a lógica de banco aqui)
        valor_total = 120000.0
        parcelas = 120
        valor_parcela = valor_total / parcelas
        
        inicio = time.time()
        for i in range(parcelas):
            dados = {
                "data": datetime.now().strftime("%Y-%m-%d"),
                "tipo": "Entrada",
                "categoria": "Honorários Longo Prazo",
                "descricao": f"[STRESS_TEST] Parcela {i+1}/{parcelas}",
                "valor": valor_parcela,
                "responsavel": "Tester",
                "status_pagamento": "Pendente",
                "vencimento": (datetime.now() + relativedelta(months=i)).strftime("%Y-%m-%d"),
                "id_cliente": id_cliente
            }
            db.crud_insert("financeiro", dados, "Stress Test Parcelamento")
        
        fim = time.time()
        print(f"Parcelamento 120x concluído em {fim-inicio:.2f}s")
        
    except Exception as e:
        logger.error(f"Erro no parcelamento longo: {e}")
        print(f"FALHA no parcelamento longo: {e}")

def limpeza_dados():
    """Remove dados gerados pelo teste."""
    print("Limpando dados de teste...")
    try:
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM financeiro WHERE descricao LIKE '[STRESS_TEST]%'")
            c.execute("DELETE FROM clientes WHERE nome LIKE '[STRESS_TEST]%'")
            conn.commit()
            print(f"Limpeza concluída. Linhas removidas: {c.rowcount}")
    except Exception as e:
        logger.error(f"Erro na limpeza: {e}")
        print(f"Erro na limpeza: {e}")

if __name__ == "__main__":
    id_cliente = setup_stress_test()
    if id_cliente:
        teste_insercao_massiva(id_cliente)
        teste_concorrencia(id_cliente)
        teste_parcelamento_longo(id_cliente)
        
        # Opcional: Comente a linha abaixo para manter os dados e ver no app
        limpeza_dados() 
        
    print("Teste de Estresse Finalizado. Verifique 'stress_test.log' para detalhes.")
