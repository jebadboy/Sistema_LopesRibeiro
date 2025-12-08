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
