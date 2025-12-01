import database as db
import pandas as pd
import logging

# Configurar logger para ver output
logging.basicConfig(level=logging.INFO)

def verify():
    print("--- INICIANDO VERIFICAÇÃO DO MÓDULO FINANCEIRO ---")
    
    # 1. Inicializar Banco (deve acionar a migração)
    print("1. Inicializando banco de dados...")
    try:
        db.init_db()
        print("   Banco inicializado com sucesso.")
    except Exception as e:
        print(f"   ERRO ao inicializar banco: {e}")
        return

    # 2. Verificar Schema da Tabela Financeiro
    print("\n2. Verificando colunas da tabela 'financeiro'...")
    with db.get_connection() as conn:
        c = conn.cursor()
        c.execute("PRAGMA table_info(financeiro)")
        columns = [col[1] for col in c.fetchall()]
        
        required_cols = ['categoria', 'centro_custo', 'recorrente', 'data_pagamento']
        missing = [col for col in required_cols if col not in columns]
        
        if missing:
            print(f"   FALHA: Colunas ausentes: {missing}")
        else:
            print("   SUCESSO: Todas as novas colunas foram encontradas.")
            print(f"   Colunas atuais: {columns}")

    # 3. Teste de Inserção com Novos Campos
    print("\n3. Testando inserção com novos campos...")
    dados = {
        "data": "2023-10-27",
        "tipo": "Saída",
        "categoria": "Marketing",
        "descricao": "Teste Verificação",
        "valor": 150.00,
        "responsavel": "Teste",
        "status_pagamento": "Pago",
        "vencimento": "2023-10-27",
        "centro_custo": "Escritório",
        "recorrente": 1,
        "data_pagamento": "2023-10-27"
    }
    
    try:
        new_id = db.crud_insert("financeiro", dados, "Teste Verificação")
        print(f"   Inserção realizada com ID: {new_id}")
        
        # 4. Ler de volta e verificar valores
        df = db.sql_get("financeiro")
        row = df[df['id'] == new_id].iloc[0]
        
        if row['centro_custo'] == "Escritório" and row['recorrente'] == 1:
            print("   SUCESSO: Dados gravados e recuperados corretamente.")
        else:
            print(f"   FALHA: Dados incorretos. Centro Custo: {row['centro_custo']}, Recorrente: {row['recorrente']}")
            
        # Limpar teste
        db.crud_delete("financeiro", "id = ?", (new_id,), "Limpeza Teste")
        print("   Registro de teste removido.")
        
    except Exception as e:
        print(f"   ERRO durante teste de inserção/leitura: {e}")

if __name__ == "__main__":
    verify()
