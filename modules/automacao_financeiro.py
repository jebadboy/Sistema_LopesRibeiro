"""
Módulo de Automação Financeiro ↔ Processos
==========================================
Cria lançamentos financeiros automaticamente quando andamentos processuais
contêm gatilhos específicos (sentença favorável, alvará, etc.)

Sprint 2 - Automações Internas
"""

import logging
import database as db
from datetime import datetime

logger = logging.getLogger(__name__)

# === GATILHOS FINANCEIROS CONFIGURÁVEIS ===
# Formato: "termo_busca": {"tipo": "receita|despesa", "categoria": "...", "status": "...", "descricao_padrao": "..."}

GATILHOS_PADRAO = {
    # Receitas de Êxito
    "sentença favorável": {
        "tipo": "Entrada",
        "categoria": "Honorários Êxito",
        "status": "Pendente",
        "descricao": "Honorários de Êxito - Sentença Favorável",
        "sugerir_valor": True
    },
    "procedente": {
        "tipo": "Entrada",
        "categoria": "Honorários Êxito",
        "status": "Pendente",
        "descricao": "Honorários de Êxito - Procedência",
        "sugerir_valor": True
    },
    "alvará": {
        "tipo": "Entrada",
        "categoria": "Honorários Êxito",
        "status": "Pendente",
        "descricao": "Levantamento de Valores - Alvará",
        "sugerir_valor": True
    },
    "depósito judicial": {
        "tipo": "Entrada",
        "categoria": "Levantamento",
        "status": "Pendente",
        "descricao": "Levantamento de Depósito Judicial",
        "sugerir_valor": True
    },
    
    # RPV e Precatórios
    "rpv": {
        "tipo": "Entrada",
        "categoria": "RPV/Precatório",
        "status": "Pendente",
        "descricao": "RPV - Requisição de Pequeno Valor",
        "sugerir_valor": True
    },
    "precatório": {
        "tipo": "Entrada",
        "categoria": "RPV/Precatório",
        "status": "Pendente",
        "descricao": "Precatório",
        "sugerir_valor": True
    },
    
    # Sucumbência
    "honorários sucumbenciais": {
        "tipo": "Entrada",
        "categoria": "Honorários Sucumbência",
        "status": "Pendente",
        "descricao": "Honorários Sucumbenciais",
        "sugerir_valor": True
    },
    "sucumbência": {
        "tipo": "Entrada",
        "categoria": "Honorários Sucumbência",
        "status": "Pendente",
        "descricao": "Honorários Sucumbenciais",
        "sugerir_valor": True
    },
    
    # Despesas - Custas
    "custas": {
        "tipo": "Saída",
        "categoria": "Custas Processuais",
        "status": "Pendente",
        "descricao": "Custas Processuais",
        "sugerir_valor": False
    },
    "preparo": {
        "tipo": "Saída",
        "categoria": "Custas Processuais",
        "status": "Pendente",
        "descricao": "Preparo de Recurso",
        "sugerir_valor": False
    },
    "diligência": {
        "tipo": "Saída",
        "categoria": "Despesas de Diligências",
        "status": "Pendente",
        "descricao": "Despesas de Diligência",
        "sugerir_valor": False
    }
}


def detectar_gatilho(texto_andamento: str) -> dict:
    """
    Detecta se o texto do andamento contém algum gatilho financeiro.
    
    Args:
        texto_andamento: Descrição do andamento processual
    
    Returns:
        dict: Dados do gatilho encontrado ou None
    """
    if not texto_andamento:
        return None
    
    texto_lower = texto_andamento.lower()
    
    for termo, config in GATILHOS_PADRAO.items():
        if termo in texto_lower:
            return {
                "termo_detectado": termo,
                **config
            }
    
    return None


def criar_lancamento_automatico(id_processo: int, config_gatilho: dict, texto_andamento: str) -> int:
    """
    Cria um lançamento financeiro automático vinculado ao processo.
    
    Args:
        id_processo: ID do processo no banco
        config_gatilho: Configuração do gatilho detectado
        texto_andamento: Texto original do andamento (para referência)
    
    Returns:
        int: ID do lançamento criado ou None se falhar
    """
    try:
        # Buscar dados do processo
        processo = db.sql_get_query("SELECT cliente_nome, id_cliente FROM processos WHERE id = ?", (id_processo,))
        
        if processo.empty:
            logger.warning(f"Processo {id_processo} não encontrado para criação de lançamento automático")
            return None
        
        processo_row = processo.iloc[0]
        
        # Montar dados do lançamento
        data_lancamento = {
            "data": datetime.now().strftime("%Y-%m-%d"),
            "tipo": config_gatilho.get("tipo", "Entrada"),
            "categoria": config_gatilho.get("categoria", "Honorários"),
            "descricao": f"[AUTO] {config_gatilho.get('descricao', 'Lançamento Automático')}",
            "valor": 0.0,  # Valor zero - usuário precisa preencher
            "status_pagamento": config_gatilho.get("status", "Pendente"),
            "id_processo": id_processo,
            "id_cliente": processo_row.get("id_cliente"),
            "cliente": processo_row.get("cliente_nome", ""),
            "obs": f"Gerado automaticamente a partir de: {texto_andamento[:100]}..."
        }
        
        # Inserir no banco
        lancamento_id = db.crud_insert("financeiro", data_lancamento, "Lançamento automático criado")
        
        logger.info(f"Lançamento automático criado: ID {lancamento_id} para processo {id_processo}")
        
        return lancamento_id
        
    except Exception as e:
        logger.error(f"Erro ao criar lançamento automático: {e}")
        return None


def processar_andamento_para_financeiro(payload: dict):
    """
    Callback chamado pelo sistema de signals quando um novo andamento é inserido.
    
    Args:
        payload: {"id": int, "data": dict} com dados do andamento
    """
    try:
        data = payload.get("data", {})
        id_processo = data.get("id_processo")
        descricao = data.get("descricao", "")
        
        if not id_processo or not descricao:
            return
        
        # Detectar gatilho
        gatilho = detectar_gatilho(descricao)
        
        if gatilho:
            logger.info(f"Gatilho financeiro detectado: '{gatilho['termo_detectado']}' no processo {id_processo}")
            
            # Verificar se já existe lançamento similar recente (evitar duplicatas)
            existentes = db.sql_get_query("""
                SELECT id FROM financeiro 
                WHERE id_processo = ? 
                AND descricao LIKE ? 
                AND data >= date('now', '-7 days')
            """, (id_processo, f"%{gatilho['descricao'][:30]}%"))
            
            if existentes.empty:
                # Criar lançamento automático
                lancamento_id = criar_lancamento_automatico(id_processo, gatilho, descricao)
                
                if lancamento_id:
                    # Notificar usuário via insight
                    try:
                        db.crud_insert("ai_insights", {
                            "tipo": "financeiro_automatico",
                            "titulo": f"💰 Lançamento Financeiro Sugerido",
                            "descricao": f"Detectamos '{gatilho['termo_detectado']}' em andamento processual. "
                                        f"Um lançamento de {gatilho['tipo']} foi criado automaticamente. "
                                        f"Por favor, verifique e adicione o valor.",
                            "prioridade": "alta",
                            "acao_sugerida": "Verificar Financeiro",
                            "link_acao": f"page=Financeiro",
                            "lido": 0
                        }, "Insight de lançamento automático criado")
                    except Exception as e:
                        logger.debug(f"Erro ao criar insight: {e}")
            else:
                logger.info(f"Lançamento similar já existe para processo {id_processo}, ignorando duplicata")
                
    except Exception as e:
        logger.error(f"Erro ao processar andamento para financeiro: {e}")


def inicializar():
    """
    Inicializa o módulo de automação, conectando ao sistema de signals.
    """
    try:
        from modules import signals
        
        # Subscrever ao evento de inserção de andamentos
        signals.subscribe("insert_andamentos", processar_andamento_para_financeiro)
        
        logger.info("Módulo de automação financeiro inicializado")
        
    except ImportError:
        logger.warning("Módulo signals não disponível, automação financeira desabilitada")
    except Exception as e:
        logger.error(f"Erro ao inicializar automação financeira: {e}")


def get_gatilhos_configurados() -> dict:
    """
    Retorna os gatilhos configurados (para interface de administração futura).
    """
    return GATILHOS_PADRAO


def testar_gatilho(texto: str) -> dict:
    """
    Função utilitária para testar detecção de gatilhos.
    
    Args:
        texto: Texto de exemplo
    
    Returns:
        dict: Resultado do teste
    """
    gatilho = detectar_gatilho(texto)
    
    return {
        "texto_testado": texto,
        "gatilho_detectado": gatilho is not None,
        "detalhes": gatilho
    }
