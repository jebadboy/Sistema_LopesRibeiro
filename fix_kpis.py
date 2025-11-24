"""
Script para corrigir a função kpis() em database.py
Execute este arquivo para aplicar a correção automaticamente.
"""

import re

# Ler o arquivo atual
with open(r"H:\Meu Drive\automatizacao\Sistema_LopesRibeiro\database.py", "r", encoding="utf-8") as f:
    content = f.read()

# Função corrigida
new_function = '''def kpis():
    """Calcula KPIs financeiros e operacionais."""
    with get_connection() as conn:
        f = pd.read_sql("SELECT * FROM financeiro", conn)
        c = pd.read_sql("SELECT * FROM clientes", conn)
        p = pd.read_sql("SELECT * FROM processos", conn)
    
    faturamento_mes = 0
    despesas_mes = 0
    lucro_mes = 0
    inadimplencia_total = 0
    processos_ativos = len(p[p['status_processo']=='Ativo']) if not p.empty else 0

    if not f.empty:
        # Filtrar apenas mês atual
        mes_atual = pd.Timestamp.now().month
        ano_atual = pd.Timestamp.now().year
        f['data_dt'] = pd.to_datetime(f['data'])
        f_mes = f[(f['data_dt'].dt.month == mes_atual) & (f['data_dt'].dt.year == ano_atual)]
        
        faturamento_mes = f_mes[(f_mes['tipo']=='Entrada')&(f_mes['status_pagamento']=='Pago')]['valor'].sum()
        despesas_mes = f_mes[(f_mes['tipo']=='Saída')&(f_mes['status_pagamento']=='Pago')]['valor'].sum()
        lucro_mes = faturamento_mes - despesas_mes
        inadimplencia_total = f[(f['tipo']=='Entrada')&(f['status_pagamento']=='Pendente')]['valor'].sum()
        
    return {
        'faturamento_mes': faturamento_mes,
        'despesas_mes': despesas_mes,
        'lucro_mes': lucro_mes,
        'inadimplencia_total': inadimplencia_total,
        'processos_ativos': processos_ativos
    }'''

# Padrão para encontrar a função kpis antiga
pattern = r'def kpis\(\):.*?return saldo, receber, num_clientes, num_processos'

# Substituir
content_new = re.sub(pattern, new_function, content, flags=re.DOTALL)

# Salvar
with open(r"H:\Meu Drive\automatizacao\Sistema_LopesRibeiro\database.py", "w", encoding="utf-8") as f:
    f.write(content_new)

print("Funcao kpis() corrigida com sucesso!")
print("Agora retorna um dicionario em vez de tupla.")
