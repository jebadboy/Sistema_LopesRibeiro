"""
Script automatizado para aplicar blindagem de erros no database.py

Este script aplica proteções try...except em todas as funções críticas
identificadas no plano de blindagem de erros.
"""

import re

def aplicar_protecao_cpf_existe(content):
    """Protege função cpf_existe()"""
    old_func = r'''def cpf_existe\(cpf\):
    """Verifica se CPF já está cadastrado\."""
    with get_connection\(\) as conn:
        c = conn\.cursor\(\)
        c\.execute\("SELECT id FROM clientes WHERE cpf_cnpj = \?", \(cpf,\)\)
        return c\.fetchone\(\) is not None'''
    
    new_func = '''def cpf_existe(cpf):
    """Verifica se CPF já está cadastrado."""
    try:
        with get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT id FROM clientes WHERE cpf_cnpj = ?", (cpf,))
            return c.fetchone() is not None
    except Exception as e:
        logger.error(f"Erro ao verificar CPF {cpf}: {e}")
        # Retorna False para permitir cadastro em caso de erro
        return False'''
    
    return re.sub(old_func, new_func, content)

def aplicar_protecao_ver_inadimplencia(content):
    """Protege função ver_inadimplencia()"""
    old_func = r'''def ver_inadimplencia\(nome\):
    """Verifica inadimplência de forma segura \(sem SQL Injection\)\."""
    with get_connection\(\) as conn:
        hoje = datetime\.now\(\)\.strftime\("%Y-%m-%d"\)
        query = "SELECT \* FROM financeiro WHERE descricao LIKE \? AND status_pagamento = 'Pendente' AND vencimento < \? AND tipo = 'Entrada'"
        df = pd\.read_sql_query\(query, conn, params=\(f'%\{nome\}%', hoje\)\)
        return "INADIMPLENTE" if not df\.empty else "Adimplente"'''
    
    new_func = '''def ver_inadimplencia(nome):
    """Verifica inadimplência de forma segura (sem SQL Injection)."""
    try:
        with get_connection() as conn:
            hoje = datetime.now().strftime("%Y-%m-%d")
            query = "SELECT * FROM financeiro WHERE descricao LIKE ? AND status_pagamento = 'Pendente' AND vencimento < ? AND tipo = 'Entrada'"
            df = pd.read_sql_query(query, conn, params=(f'%{nome}%', hoje))
            return "INADIMPLENTE" if not df.empty else "Adimplente"
    except Exception as e:
        logger.error(f"Erro ao verificar inadimplência para {nome}: {e}")
        return "Erro ao verificar"'''
    
    return re.sub(old_func, new_func, content)

# Leitura do arquivo
with open('database.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("Aplicando proteções...")

# Aplicar cada proteção
content = aplicar_protecao_cpf_existe(content)
content = aplicar_protecao_ver_inadimplencia(content)

# Salvar arquivo modificado
with open('database.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Proteções aplicadas com sucesso!")
