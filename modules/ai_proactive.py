"""
Módulo de IA Proativa
Responsável por analisar eventos do sistema e gerar insights automáticos.
"""

import logging
import modules.signals as signals
import database as db
import ai_gemini as ai
from datetime import datetime
import time
import random

logger = logging.getLogger(__name__)

def inicializar():
    """Inscreve as funções de IA nos eventos do sistema."""
    signals.subscribe("insert_clientes", analisar_novo_cliente)
    signals.subscribe("insert_processos", analisar_novo_processo)
    signals.subscribe("insert_financeiro", analisar_financeiro)
    logger.info("IA Proativa inicializada e escutando eventos.")

def salvar_insight(titulo, descricao, prioridade='media', acao_sugerida=None, link_acao=None):
    """Salva um insight no banco de dados."""
    try:
        db.sql_run("""
            INSERT INTO ai_insights (tipo, titulo, descricao, prioridade, acao_sugerida, link_acao)
            VALUES (?, ?, ?, ?, ?, ?)
        """, ('proativo', titulo, descricao, prioridade, acao_sugerida, link_acao))
        logger.info(f"Insight gerado: {titulo}")
    except Exception as e:
        logger.error(f"Erro ao salvar insight: {e}")

def executar_com_retry(func, *args, max_retries=3, **kwargs):
    """Executa uma função com retries e backoff exponencial."""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"Falha final após {max_retries} tentativas: {e}")
                raise e
            
            sleep_time = (2 ** attempt) + random.uniform(0, 1)
            logger.warning(f"Tentativa {attempt + 1} falhou. Dormindo {sleep_time:.2f}s. Erro: {e}")
            time.sleep(sleep_time)

# --- Handlers de Eventos ---

def analisar_novo_cliente(payload):
    """Analisa um novo cliente cadastrado."""
    try:
        data = payload.get('data')
        if not data: return
        
        nome = data.get('nome')
        
        # Regra 1: Validação básica (Hardcoded)
        if not data.get('cpf_cnpj'):
            salvar_insight(
                titulo=f"Cadastro Incompleto: {nome}",
                descricao=f"O cliente {nome} foi cadastrado sem CPF/CNPJ. Isso pode impedir a emissão de contratos.",
                prioridade="media",
                acao_sugerida="Completar Cadastro",
                link_acao=f"page=Clientes&id={payload.get('id')}"
            )
            return # Se faltar dados básicos, nem gasta token com IA

        # Regra 2: Análise Estratégica (Gemini)
        try:
            prompt = f"""
            Analise o perfil deste novo cliente de advocacia e sugira uma estratégia de abordagem inicial:
            Dados: {data}
            
            Responda com:
            1. Perfil resumido
            2. Potenciais demandas jurídicas (baseado na profissão/estado civil)
            3. Tom de voz recomendado
            """
            # Usando Retry
            analise = executar_com_retry(ai.chat_assistente, prompt, contexto={"origem": "novo_cliente"})
            
            salvar_insight(
                titulo=f"Análise de Perfil: {nome}",
                descricao=analise[:500] + "..." if len(analise) > 500 else analise, # Truncar se for muito longo
                prioridade="baixa",
                acao_sugerida="Ver Detalhes",
                link_acao=f"page=Clientes&id={payload.get('id')}"
            )
        except Exception as e_ai:
            logger.error(f"Erro ao chamar Gemini para cliente após retries: {e_ai}")
            # Fallback simples para não ficar sem insight
            salvar_insight(
                titulo=f"Novo Cliente: {nome}",
                descricao=f"Cliente {nome} cadastrado com sucesso. Verifique se todos os documentos necessários foram solicitados.",
                prioridade="baixa",
                acao_sugerida="Ver Detalhes",
                link_acao=f"page=Clientes&id={payload.get('id')}"
            )
        
    except Exception as e:
        logger.error(f"Erro na análise de novo cliente: {e}")

def analisar_novo_processo(payload):
    """Analisa um novo processo cadastrado."""
    try:
        data = payload.get('data')
        if not data: return
        
        numero = data.get('numero')
        acao = data.get('acao')
        area = data.get('area')
        
        # Análise Jurídica (Gemini)
        try:
            prompt = f"""
            Um novo processo foi cadastrado.
            Número: {numero}
            Ação: {acao}
            Área: {area}
            
            Sugira:
            1. Prazos típicos iniciais para esta ação.
            2. Documentos indispensáveis que devem ser solicitados ao cliente.
            3. Riscos comuns neste tipo de demanda.
            """
            # Usando Retry
            analise = executar_com_retry(ai.chat_assistente, prompt, contexto={"origem": "novo_processo"})
            
            salvar_insight(
                titulo=f"Estratégia Processual: {acao}",
                descricao=analise[:600] + "..." if len(analise) > 600 else analise,
                prioridade="alta",
                acao_sugerida="Ver Processo",
                link_acao=f"page=Processos&id={payload.get('id')}"
            )
        except Exception as e_ai:
             # Fallback simples
            logger.warning(f"Falha na IA para processo {numero}, usando fallback.")
            salvar_insight(
                titulo="Novo Processo Iniciado",
                descricao=f"Processo {numero} ({acao}) cadastrado. Verifique se há prazos iniciais a cumprir.",
                prioridade="alta",
                acao_sugerida="Ver Processo",
                link_acao=f"page=Processos&id={payload.get('id')}"
            )
        
    except Exception as e:
        logger.error(f"Erro na análise de novo processo: {e}")

def analisar_financeiro(payload):
    """Analisa lançamentos financeiros."""
    try:
        data = payload.get('data')
        if not data: return
        
        valor = data.get('valor', 0)
        tipo = data.get('tipo')
        categoria = data.get('categoria')
        
        # Regra de Valor Alto
        if tipo == 'Saída' and valor > 5000:
            # Análise de Impacto (Gemini)
            try:
                prompt = f"""
                Uma saída financeira de alto valor foi registrada.
                Valor: R$ {valor}
                Categoria: {categoria}
                Descrição: {data.get('descricao')}
                
                Analise se isso é comum para um escritório de advocacia e sugira medidas de controle de fluxo de caixa.
                """
                # Usando Retry
                analise = executar_com_retry(ai.chat_assistente, prompt, contexto={"origem": "financeiro_alto_valor"})
                
                salvar_insight(
                    titulo="Alerta de Alta Despesa",
                    descricao=analise[:500],
                    prioridade="alta",
                    acao_sugerida="Ver Financeiro",
                    link_acao="page=Financeiro"
                )
            except Exception as e:
                # Fallback
                salvar_insight(
                    titulo="Alerta de Alta Despesa",
                    descricao=f"Uma saída de R$ {valor:.2f} foi registrada. Verifique o impacto no fluxo de caixa.",
                    prioridade="alta",
                    acao_sugerida="Ver Financeiro",
                    link_acao="page=Financeiro"
                )
            
    except Exception as e:
        logger.error(f"Erro na análise financeira: {e}")

def analyze_event(event_type, data):
    """
    Ponto central para análise de eventos.
    Pode ser chamado manualmente ou via sinais.
    """
    payload = {'data': data}
    if event_type == 'novo_cliente':
        analisar_novo_cliente(payload)
    elif event_type == 'novo_processo':
        analisar_novo_processo(payload)
    elif event_type == 'financeiro':
        analisar_financeiro(payload)
    else:
        logger.warning(f"Tipo de evento desconhecido para análise: {event_type}")

def generate_insights():
    """
    Gera insights periódicos (background jobs).
    Pode ser chamado por um scheduler ou cron.
    """
    # Exemplo: Verificar processos parados há muito tempo
    # Exemplo: Verificar clientes sem contato recente
    logger.info("Gerando insights periódicos (Simulação)...")
    pass

def get_copilot_response(message, context=None):
    """
    Obtém resposta do Copiloto (Gemini).
    Centraliza a lógica de chat para a UI.
    """
    try:
        # Usando Retry
        return executar_com_retry(ai.chat_assistente, message, contexto=context)
    except Exception as e:
        logger.error(f"Erro no Copiloto: {e}")
        return "Desculpe, estou com dificuldades para processar sua solicitação no momento. Tente novamente em alguns instantes."
