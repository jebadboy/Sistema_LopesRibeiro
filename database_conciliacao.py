"""
Funções adicionais de database para Conciliação Bancária
"""

import database as db
import database_adapter as adapter
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def get_transacoes_pendentes():
    """Retorna transações bancárias pendentes de conciliação"""
    query = """
    SELECT * FROM transacoes_bancarias 
    WHERE status_conciliacao = 'Pendente' 
    ORDER BY data_transacao DESC
    """
    return db.run_query(query)

def get_transacoes_conciliadas(data_inicio, data_fim):
    """Retorna histórico de transações conciliadas"""
    query = """
    SELECT tb.*, f.descricao as lanc_descricao, c.nome as cliente_nome
    FROM transacoes_bancarias tb
    LEFT JOIN financeiro f ON tb.id_financeiro = f.id
    LEFT JOIN clientes c ON f.id_cliente = c.id
    WHERE tb.status_conciliacao = 'Conciliado'
    AND tb.data_conciliacao BETWEEN ? AND ?
    ORDER BY tb.data_conciliacao DESC
    """
    
    if adapter.USE_POSTGRES:
        query = query.replace('?', '%s')
    
    return db.run_query(query, (data_inicio, data_fim))

def get_estatisticas_conciliacao():
    """Retorna estatísticas de conciliação do mês atual"""
    mes_atual = datetime.now().month
    ano_atual = datetime.now().year
    
    # Total importado no mês
    query_importado = """
    SELECT COALESCE(SUM(valor), 0) as total
    FROM transacoes_bancarias
    WHERE tipo = 'Crédito'
    AND CAST(strftime('%m', data_importacao) AS INTEGER) = ?
    AND CAST(strftime('%Y', data_importacao) AS INTEGER) = ?
    """
    
    # Total conciliado
    query_conciliado = """
    SELECT COALESCE(SUM(valor), 0) as total, COUNT(*) as qtd
    FROM transacoes_bancarias
    WHERE tipo = 'Crédito'
    AND status_conciliacao = 'Conciliado'
    AND CAST(strftime('%m', data_importacao) AS INTEGER) = ?
    AND CAST(strftime('%Y', data_importacao) AS INTEGER) = ?
    """
    
    # Total pendente
    query_pendente = """
    SELECT COALESCE(SUM(valor), 0) as total
    FROM transacoes_bancarias
    WHERE tipo = 'Crédito'
    AND status_conciliacao = 'Pendente'
    """
    
    # Total de transações
    query_total = """
    SELECT COUNT(*) as qtd
    FROM transacoes_bancarias
    WHERE tipo = 'Crédito'
    AND CAST(strftime('%m', data_importacao) AS INTEGER) = ?
    AND CAST(strftime('%Y', data_importacao) AS INTEGER) = ?
    """
    
    if adapter.USE_POSTGRES:
        query_importado = """
        SELECT COALESCE(SUM(valor), 0) as total
        FROM transacoes_bancarias
        WHERE tipo = 'Crédito'
        AND EXTRACT(MONTH FROM data_importacao::timestamp) = %s
        AND EXTRACT(YEAR FROM data_importacao::timestamp) = %s
        """
        
        query_conciliado = """
        SELECT COALESCE(SUM(valor), 0) as total, COUNT(*) as qtd
        FROM transacoes_bancarias
        WHERE tipo = 'Crédito'
        AND status_conciliacao = 'Conciliado'
        AND EXTRACT(MONTH FROM data_importacao::timestamp) = %s
        AND EXTRACT(YEAR FROM data_importacao::timestamp) = %s
        """
        
        query_total = """
        SELECT COUNT(*) as qtd
        FROM transacoes_bancarias
        WHERE tipo = 'Crédito'
        AND EXTRACT(MONTH FROM data_importacao::timestamp) = %s
        AND EXTRACT(YEAR FROM data_importacao::timestamp) = %s
        """
    
    try:
        res_importado = db.run_query(query_importado, (mes_atual, ano_atual))
        res_conciliado = db.run_query(query_conciliado, (mes_atual, ano_atual))
        res_pendente = db.run_query(query_pendente)
        res_total = db.run_query(query_total, (mes_atual, ano_atual))
        
        total_importado = res_importado[0]['total'] if res_importado else 0
        total_conciliado = res_conciliado[0]['total'] if res_conciliado else 0
        qtd_conciliadas = res_conciliado[0]['qtd'] if res_conciliado else 0
        total_pendente = res_pendente[0]['total'] if res_pendente else 0
        qtd_total = res_total[0]['qtd'] if res_total else 0
        
        taxa_conciliacao = (qtd_conciliadas / qtd_total * 100) if qtd_total > 0 else 0
        
        return {
            'total_importado': total_importado,
            'total_conciliado': total_conciliado,
            'total_pendente': total_pendente,
            'qtd_conciliadas': qtd_conciliadas,
            'qtd_total': qtd_total,
            'taxa_conciliacao': taxa_conciliacao
        }
    except Exception as e:
        logger.error(f"Erro ao buscar estatísticas: {e}")
        return {
            'total_importado': 0,
            'total_conciliado': 0,
            'total_pendente': 0,
            'qtd_conciliadas': 0,
            'qtd_total': 0,
            'taxa_conciliacao': 0
        }

def marcar_transacao_ignorada(id_transacao, usuario):
    """Marca transação como ignorada (não precisa conciliar)"""
    from datetime import datetime
    db.crud_update(
        'transacoes_bancarias',
        {
            'status_conciliacao': 'Ignorado',
            'conciliado_por': usuario,
            'data_conciliacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        },
        'id = ?',
        (id_transacao,),
        f'Transação ignorada por {usuario}'
    )

def reverter_conciliacao(id_transacao, usuario):
    """
    Reverte uma conciliação, voltando a transação para status Pendente.
    Também atualiza o lançamento financeiro vinculado.
    
    Args:
        id_transacao: ID da transação bancária
        usuario: Nome do usuário que está revertendo
        
    Returns:
        dict: {'sucesso': bool, 'erro': str}
    """
    try:
        # 1. Buscar id_financeiro antes de reverter
        query = "SELECT id_financeiro FROM transacoes_bancarias WHERE id = ?"
        if adapter.USE_POSTGRES:
            query = query.replace('?', '%s')
        result = db.run_query(query, (id_transacao,))
        
        id_financeiro = None
        if result and len(result) > 0:
            id_financeiro = result[0].get('id_financeiro')
        
        # 2. Reverter status da transação bancária
        db.crud_update(
            'transacoes_bancarias',
            {
                'status_conciliacao': 'Pendente',
                'id_financeiro': None,
                'conciliado_por': None,
                'data_conciliacao': None
            },
            'id = ?',
            (id_transacao,),
            f'Conciliação revertida por {usuario}'
        )
        
        # 3. Reverter status do lançamento financeiro (se havia vínculo)
        if id_financeiro:
            db.crud_update(
                'financeiro',
                {
                    'status_pagamento': 'Pendente',
                    'data_pagamento': None
                },
                'id = ?',
                (id_financeiro,),
                f'Baixa revertida via conciliação bancária'
            )
        
        logger.info(f"Conciliação revertida: transação {id_transacao} por {usuario}")
        return {'sucesso': True}
        
    except Exception as e:
        logger.error(f"Erro ao reverter conciliação: {e}")
        return {'sucesso': False, 'erro': str(e)}


# =====================================================
# FUNÇÕES PARA DASHBOARD AVANÇADO
# =====================================================

def get_evolucao_conciliacao(data_inicio, data_fim):
    """Retorna evolução de conciliações por mês para gráficos"""
    query = """
    SELECT 
        strftime('%Y-%m', data_conciliacao) as mes,
        SUM(CASE WHEN status_conciliacao = 'Conciliado' THEN valor ELSE 0 END) as total_conciliado,
        SUM(CASE WHEN status_conciliacao = 'Pendente' THEN valor ELSE 0 END) as total_pendente,
        COUNT(CASE WHEN status_conciliacao = 'Conciliado' THEN 1 END) as qtd_conciliado,
        COUNT(CASE WHEN status_conciliacao = 'Pendente' THEN 1 END) as qtd_pendente
    FROM transacoes_bancarias
    WHERE data_importacao BETWEEN ? AND ?
    GROUP BY strftime('%Y-%m', data_conciliacao)
    ORDER BY mes
    """
    
    if adapter.USE_POSTGRES:
        query = """
        SELECT 
            TO_CHAR(data_conciliacao::timestamp, 'YYYY-MM') as mes,
            SUM(CASE WHEN status_conciliacao = 'Conciliado' THEN valor ELSE 0 END) as total_conciliado,
            SUM(CASE WHEN status_conciliacao = 'Pendente' THEN valor ELSE 0 END) as total_pendente,
            COUNT(CASE WHEN status_conciliacao = 'Conciliado' THEN 1 END) as qtd_conciliado,
            COUNT(CASE WHEN status_conciliacao = 'Pendente' THEN 1 END) as qtd_pendente
        FROM transacoes_bancarias
        WHERE data_importacao BETWEEN %s AND %s
        GROUP BY TO_CHAR(data_conciliacao::timestamp, 'YYYY-MM')
        ORDER BY mes
        """
    
    return db.run_query(query, (data_inicio, data_fim))


def get_totais_por_conta():
    """Retorna totais agrupados por conta/instituição"""
    query = """
    SELECT 
        COALESCE(conta_origem, 'Não informado') as conta,
        COALESCE(tipo_origem, 'N/A') as tipo,
        COUNT(*) as qtd_transacoes,
        SUM(valor) as total_valor,
        SUM(CASE WHEN status_conciliacao = 'Conciliado' THEN 1 ELSE 0 END) as conciliadas,
        SUM(CASE WHEN status_conciliacao = 'Pendente' THEN 1 ELSE 0 END) as pendentes
    FROM transacoes_bancarias
    GROUP BY conta_origem, tipo_origem
    ORDER BY total_valor DESC
    """
    return db.run_query(query)


def get_pendentes_antigos(dias):
    """Retorna transações pendentes há mais de X dias"""
    query = """
    SELECT * FROM transacoes_bancarias
    WHERE status_conciliacao = 'Pendente'
    AND date(data_importacao) <= date('now', '-' || ? || ' days')
    ORDER BY data_importacao ASC
    """
    
    if adapter.USE_POSTGRES:
        query = """
        SELECT * FROM transacoes_bancarias
        WHERE status_conciliacao = 'Pendente'
        AND data_importacao::date <= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY data_importacao ASC
        """
    
    return db.run_query(query, (dias,))


# =====================================================
# FUNÇÕES PARA REGRAS AUTOMÁTICAS
# =====================================================

def _criar_tabela_regras():
    """Cria tabela de regras se não existir"""
    try:
        db.sql_run("""
            CREATE TABLE IF NOT EXISTS regras_conciliacao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                padrao_descricao TEXT NOT NULL,
                id_cliente INTEGER,
                categoria TEXT,
                ativo INTEGER DEFAULT 1,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    except:
        pass

# Garantir que tabela existe
_criar_tabela_regras()


def criar_regra_conciliacao(dados):
    """Cria nova regra de conciliação automática"""
    return db.crud_insert(
        'regras_conciliacao',
        dados,
        f"Regra criada: {dados.get('nome', '')}"
    )


def get_regras_conciliacao(apenas_ativas=False):
    """Retorna regras de conciliação"""
    query = """
    SELECT r.*, c.nome as cliente_nome
    FROM regras_conciliacao r
    LEFT JOIN clientes c ON r.id_cliente = c.id
    """
    if apenas_ativas:
        query += " WHERE r.ativo = 1"
    query += " ORDER BY r.nome"
    
    return db.run_query(query)


def toggle_regra(id_regra):
    """Alterna status ativo/inativo da regra"""
    query = "UPDATE regras_conciliacao SET ativo = CASE WHEN ativo = 1 THEN 0 ELSE 1 END WHERE id = ?"
    if adapter.USE_POSTGRES:
        query = query.replace('?', '%s')
    db.sql_run(query, (id_regra,))


def excluir_regra(id_regra):
    """Exclui regra de conciliação"""
    db.crud_delete('regras_conciliacao', 'id = ?', (id_regra,), f"Regra {id_regra} excluída")


def buscar_lancamentos_cliente(id_cliente, valor, margem=0.1):
    """
    Busca lançamentos financeiros de um cliente com valor próximo.
    
    Args:
        id_cliente: ID do cliente
        valor: Valor de referência
        margem: Margem de tolerância (0.1 = 10%)
    """
    valor_min = valor * (1 - margem)
    valor_max = valor * (1 + margem)
    
    query = """
    SELECT f.*, c.nome as cliente_nome
    FROM financeiro f
    LEFT JOIN clientes c ON f.id_cliente = c.id
    WHERE f.id_cliente = ?
    AND f.tipo = 'Entrada'
    AND f.status_pagamento = 'Pendente'
    AND f.valor BETWEEN ? AND ?
    ORDER BY ABS(f.valor - ?) ASC
    LIMIT 5
    """
    
    if adapter.USE_POSTGRES:
        query = query.replace('?', '%s')
    
    return db.run_query(query, (id_cliente, valor_min, valor_max, valor))
