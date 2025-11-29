# Arquivo de Correção #1: SQL Injection em sql_get()
# Arquivo: database.py
# Problema: Parâmetro 'ordem' concatenado diretamente na query SQL sem validação

# ANTES (VULNERÁVEL):
"""
def sql_get(tabela, ordem=""):
    if tabela not in TABELAS_VALIDAS:
        logger.error(f"Tentativa de acesso a tabela inválida: {tabela}")
        raise ValueError(f"Tabela inválida: {tabela}. Tabelas permitidas: {TABELAS_VALIDAS}")
    
    try:
        with get_connection() as conn:
            sql = f"SELECT * FROM {tabela}"
            if ordem: 
                sql += f" ORDER BY {ordem}"  # VULNERÁVEL A SQL INJECTION!
            return pd.read_sql_query(sql, conn)
    except Exception as e:
        logger.error(f"Erro ao buscar dados da tabela {tabela}: {e}")
        return pd.DataFrame()
"""

# DEPOIS (SEGURO):
"""
# 1. Adicionar após TABELAS_VALIDAS (linha ~13):

# CORREÇÃO: Whitelist de colunas permitidas para ORDER BY (previne SQL injection)
COLUNAS_PERMITIDAS = {
    'clientes': ['id', 'nome', 'cpf_cnpj', 'email', 'telefone', 'status_cliente', 'data_cadastro', 'cidade', 'estado'],
    'financeiro': ['id', 'data', 'tipo', 'categoria', 'descricao', 'valor', 'responsavel', 'status_pagamento', 'vencimento'],
    'processos': ['id', 'cliente_nome', 'acao', 'numero_processo', 'status_processo', 'data_abertura', 'responsavel'],
    'andamentos': ['id', 'id_processo', 'data', 'descricao', 'responsavel'],
    'agenda': ['id', 'tipo', 'titulo', 'data_evento', 'data_inicio', 'data_fim', 'responsavel', 'status', 'prioridade'],
    'documentos_processo': ['id', 'id_processo', 'tipo_documento', 'nome_documento', 'criado_em'],
    'parcelamentos': ['id', 'id_lancamento_financeiro', 'numero_parcela', 'vencimento', 'status_parcela'],
    'modelos_proposta': ['id', 'nome_modelo', 'area_atuacao', 'valor_sugerido', 'criado_em']
}

# 2. Substituir função sql_get (linha ~201):

def sql_get(tabela, ordem=""):
    \"\"\"
    Busca dados de uma tabela com validação de segurança contra SQL injection.
    
    Args:
        tabela: Nome da tabela (validada contra TABELAS_VALIDAS)
        ordem: Coluna para ordenação (validada contra COLUNAS_PERMITIDAS)
    
    Returns:
        DataFrame com os dados ou DataFrame vazio em caso de erro
    \"\"\"
    if tabela not in TABELAS_VALIDAS:
        logger.error(f"Tentativa de acesso a tabela inválida: {tabela}")
        raise ValueError(f"Tabela inválida: {tabela}. Tabelas permitidas: {TABELAS_VALIDAS}")
    
    # CORREÇÃO: Validar coluna de ordenação contra SQL injection
    if ordem:
        colunas_validas = COLUNAS_PERMITIDAS.get(tabela, [])
        if ordem not in colunas_validas:
            logger.error(f"Tentativa de ordenação com coluna inválida: {ordem} na tabela {tabela}")
            raise ValueError(f"Coluna de ordenação inválida: '{ordem}'. Colunas permitidas para '{tabela}': {colunas_validas}")
    
    try:
        with get_connection() as conn:
            sql = f"SELECT * FROM {tabela}"
            if ordem: 
                sql += f" ORDER BY {ordem}"  # Agora é seguro após validação
            return pd.read_sql_query(sql, conn)
    except Exception as e:
        logger.error(f"Erro ao buscar dados da tabela {tabela}: {e}")
        return pd.DataFrame()
"""

# INSTRUÇÕES DE APLICAÇÃO:
# 1. Abrir database.py
# 2. Adicionar COLUNAS_PERMITIDAS após linha 13 (após TABELAS_VALIDAS)
# 3. Substituir a função sql_get (linhas ~201-215) pela versão corrigida
# 4. Salvar e testar

# TESTE DE VALIDAÇÃO:
# Tentar: db.sql_get("clientes", "nome; DROP TABLE clientes;--")
# Resultado esperado: ValueError com mensagem de coluna inválida
