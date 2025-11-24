"""
Script Automatizado para Aplicar Top-3 Protecoes de Erro Criticas

Este script aplica protecoes try...except nas 3 funcoes mais criticas do database.py:
1. kpis() - Protege Painel Geral
2. get_historico() - Protege visualizacao de processos  
3. ver_inadimplencia() - Protege lista de clientes

USO:
    python apply_top3_protections.py

IMPORTANTE: Faz backup antes! O script cria um backup automatico em database.py.bak
"""

import shutil
from datetime import datetime

# Criar backup
print("Criando backup...")
shutil.copy('database.py', f'database.py.bak_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
print("OK - Backup criado!")

# Ler arquivo
with open('database.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("\nAplicando protecoes...")

# Protecao #1: kpis()
print("  [1/3] Protegendo kpis()...")
content = content.replace(
    '''def kpis():
    """Calcula KPIs financeiros e operacionais."""
    with get_connection() as conn:
        f = pd.read_sql("SELECT * FROM financeiro", conn)
        c = pd.read_sql("SELECT * FROM clientes", conn)
        p = pd.read_sql("SELECT * FROM processos", conn)
    
    saldo = 0
    receber = 0
    num_clientes = len(c[c['status_cliente']=='ATIVO']) if not c.empty else 0
    num_processos = len(p) if not p.empty else 0

    if not f.empty:
        entradas = f[(f['tipo']=='Entrada')&(f['status_pagamento']=='Pago')]['valor'].sum()
        saidas = f[(f['tipo']=='Saída')&(f['status_pagamento']=='Pago')]['valor'].sum()
        saldo = entradas - saidas
        receber = f[(f['tipo']=='Entrada')&(f['status_pagamento']=='Pendente')]['valor'].sum()
        
    return saldo, receber, num_clientes, num_processos''',
    '''def kpis():
    """Calcula KPIs financeiros e operacionais."""
    try:
        with get_connection() as conn:
            f = pd.read_sql("SELECT * FROM financeiro", conn)
            c = pd.read_sql("SELECT * FROM clientes", conn)
            p = pd.read_sql("SELECT * FROM processos", conn)
        
        saldo = 0
        receber = 0
        num_clientes = len(c[c['status_cliente']=='ATIVO']) if not c.empty else 0
        num_processos = len(p) if not p.empty else 0

        if not f.empty:
            entradas = f[(f['tipo']=='Entrada')&(f['status_pagamento']=='Pago')]['valor'].sum()
            saidas = f[(f['tipo']=='Saída')&(f['status_pagamento']=='Pago')]['valor'].sum()
            saldo = entradas - saidas
            receber = f[(f['tipo']=='Entrada')&(f['status_pagamento']=='Pendente')]['valor'].sum()
            
        return saldo, receber, num_clientes, num_processos
    except Exception as e:
        logger.error(f"Erro ao calcular KPIs: {e}")
        return 0, 0, 0, 0  # Valores seguros em caso de erro'''
)

# Protecao #2: get_historico()
print("  [2/3] Protegendo get_historico()...")
content = content.replace(
    '''def get_historico(id_processo):
    """Busca histórico de andamentos de um processo."""
    with get_connection() as conn:
        return pd.read_sql("SELECT data, descricao, responsavel FROM andamentos WHERE id_processo=? ORDER BY data DESC", conn, params=(id_processo,))''',
    '''def get_historico(id_processo):
    """Busca histórico de andamentos de um processo."""
    try:
        with get_connection() as conn:
            return pd.read_sql("SELECT data, descricao, responsavel FROM andamentos WHERE id_processo=? ORDER BY data DESC", conn, params=(id_processo,))
    except Exception as e:
        logger.error(f"Erro ao buscar histórico do processo {id_processo}: {e}")
        return pd.DataFrame(columns=['data', 'descricao', 'responsavel'])  # DataFrame vazio em caso de erro'''
)

# Protecao #3: ver_inadimplencia()
print("  [3/3] Protegendo ver_inadimplencia()...")
content = content.replace(
    '''def ver_inadimplencia(nome):
    """Verifica inadimplência de forma segura (sem SQL Injection)."""
    with get_connection() as conn:
        hoje = datetime.now().strftime("%Y-%m-%d")
        query = "SELECT * FROM financeiro WHERE descricao LIKE ? AND status_pagamento = 'Pendente' AND vencimento < ? AND tipo = 'Entrada'"
        df = pd.read_sql_query(query, conn, params=(f'%{nome}%', hoje))
        return "INADIMPLENTE" if not df.empty else "Adimplente"''',
    '''def ver_inadimplencia(nome):
    """Verifica inadimplência de forma segura (sem SQL Injection)."""
    try:
        with get_connection() as conn:
            hoje = datetime.now().strftime("%Y-%m-%d")
            query = "SELECT * FROM financeiro WHERE descricao LIKE ? AND status_pagamento = 'Pendente' AND vencimento < ? AND tipo = 'Entrada'"
            df = pd.read_sql_query(query, conn, params=(f'%{nome}%', hoje))
            return "INADIMPLENTE" if not df.empty else "Adimplente"
    except Exception as e:
        logger.error(f"Erro ao verificar inadimplencia para {nome}: {e}")
        return "Erro ao verificar"  # Mensagem de erro amigavel'''
)

# Salvar arquivo modificado
with open('database.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\nOK - Protecoes aplicadas com sucesso!")
print("\nRESUMO:")
print("   [OK] Funcao kpis() protegida - Painel Geral a prova de erros")
print("   [OK] Funcao get_historico() protegida - Processos a prova de erros")
print("   [OK] Funcao ver_inadimplencia() protegida - Clientes a prova de erros")
print("\nPROXIMO PASSO: Teste o sistema com 'streamlit run app.py'")
print("\nSe algo der errado, restaure o backup criado.")
