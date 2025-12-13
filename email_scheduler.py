"""
Scheduler de E-mails - Sistema Lopes & Ribeiro
Executa a cada 30 minutos via Windows Task Scheduler.
Funciona mesmo quando Streamlit está fechado.

Configuração do Windows Task Scheduler:
    1. Abra o Agendador de Tarefas do Windows
    2. Criar Tarefa Básica
    3. Nome: LopesRibeiro_EmailCheck
    4. Disparador: Repetir a cada 30 minutos
    5. Ação: Iniciar um programa
    6. Programa: pythonw.exe
    7. Argumentos: "G:/Meu Drive/automatizacao/Sistema_LopesRibeiro/email_scheduler.py"
    8. Iniciar em: "G:/Meu Drive/automatizacao/Sistema_LopesRibeiro"
"""

import os
import sys
from datetime import datetime

# Configura path do projeto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Usar módulo centralizado de logging com rotação automática
from logging_config import get_email_logger, LOG_DIR
logger = get_email_logger()
LOG_FILE = os.path.join(LOG_DIR, 'email_scheduler.log')


def verificar_emails():
    """
    Verifica novos e-mails e salva alertas no banco.
    Executado automaticamente pelo Windows Task Scheduler.
    """
    logger.info("=" * 50)
    logger.info("Iniciando verificação de e-mails...")
    
    try:
        # Importar módulos do projeto
        from workspace_integration import WorkspaceManager, EmailAlert
        import database as db
        
        # Conectar ao Gmail
        ws = WorkspaceManager()
        if not ws.gmail.conectar("sistema"):
            logger.error("Falha na conexão com Gmail")
            return
        
        logger.info("Conectado ao Gmail com sucesso")
        
        # Buscar e-mails recentes
        emails = ws.gmail.buscar_emails_recentes(max_results=50, dias_atras=1)
        logger.info(f"Encontrados {len(emails)} e-mails recentes")
        
        # Processar e classificar e-mails
        alertas = ws.gmail.processar_emails(emails)
        logger.info(f"Identificados {len(alertas)} alertas relevantes")
        
        # Salvar alertas no banco
        novos_alertas = 0
        for alerta in alertas:
            try:
                # Obter message_id do email para evitar duplicatas
                # O alerta deve ter vindo de um email com id
                email_data = next((e for e in emails if e.get('assunto') == alerta.assunto), None)
                email_id = email_data.get('id', '') if email_data else ''
                
                # Verificar se já existe alerta com este email_id (mais confiável)
                if email_id:
                    existente = db.sql_get_query("""
                        SELECT id FROM alertas_email 
                        WHERE email_message_id = ?
                        LIMIT 1
                    """, [email_id])
                else:
                    # Fallback para assunto + data se não tiver id
                    existente = db.sql_get_query("""
                        SELECT id FROM alertas_email 
                        WHERE assunto = ? AND remetente = ?
                        LIMIT 1
                    """, [alerta.assunto[:200], alerta.remetente])
                
                if existente.empty:
                    # === ANÁLISE COM IA (NOVO) ===
                    ia_resultado = {}
                    processo_vinculado_id = None
                    
                    try:
                        from ai_gemini import analisar_email_juridico
                        
                        # Obter corpo completo do email
                        corpo_email = email_data.get('corpo', '') if email_data else alerta.corpo_resumo
                        
                        # Analisar com IA
                        ia_resultado = analisar_email_juridico(
                            assunto=alerta.assunto,
                            corpo=corpo_email,
                            remetente=alerta.remetente
                        )
                        logger.info(f"IA analisou email: prazo={ia_resultado.get('prazo_dias')} dias")
                        
                        # Buscar processo vinculado pelo número CNJ
                        numero_cnj = alerta.numero_processo or ia_resultado.get('numero_processo')
                        if numero_cnj:
                            processo = db.sql_get_query(
                                "SELECT id FROM processos WHERE numero = ? LIMIT 1",
                                [numero_cnj]
                            )
                            if not processo.empty:
                                processo_vinculado_id = int(processo.iloc[0]['id'])
                                logger.info(f"Processo vinculado: ID {processo_vinculado_id}")
                    except Exception as e_ia:
                        logger.warning(f"Erro na análise IA (não crítico): {e_ia}")
                    
                    # Salvar alerta com dados da IA
                    import json
                    db.crud_insert("alertas_email", {
                        "tipo": alerta.tipo.value,
                        "remetente": alerta.remetente,
                        "assunto": alerta.assunto[:200],
                        "numero_processo": alerta.numero_processo or ia_resultado.get('numero_processo'),
                        "valor_detectado": alerta.valor_detectado or ia_resultado.get('valor_mencionado'),
                        "data_recebimento": alerta.data_recebimento,
                        "corpo_resumo": alerta.corpo_resumo[:1000],
                        "email_message_id": email_id,
                        "processado": 0,
                        "criado_em": datetime.now().isoformat(),
                        # Novos campos IA
                        "prazo_dias": ia_resultado.get('prazo_dias'),
                        "data_fatal_sugerida": ia_resultado.get('data_fatal_sugerida'),
                        "processo_vinculado_id": processo_vinculado_id,
                        "ia_analise": json.dumps(ia_resultado) if ia_resultado else None,
                        "status_ia": "sugestao_ia" if ia_resultado.get('prazo_identificado') else "sem_prazo"
                    })
                    novos_alertas += 1
                    
                    if ia_resultado.get('prazo_identificado'):
                        logger.info(f"Alerta salvo COM PRAZO: {alerta.tipo.value} - {ia_resultado.get('prazo_dias')} dias")
                    else:
                        logger.info(f"Alerta salvo: {alerta.tipo.value} - {alerta.assunto[:50]}...")
                else:
                    logger.debug(f"Alerta já existe, ignorando: {alerta.assunto[:50]}...")
            except Exception as e:
                logger.error(f"Erro ao salvar alerta: {e}")
        
        logger.info(f"Verificação concluída: {novos_alertas} novos alertas salvos")
        
    except ImportError as e:
        logger.error(f"Erro de importação: {e}")
        logger.error("Verifique se todos os módulos estão instalados")
    except Exception as e:
        logger.error(f"Erro na verificação: {e}")
        import traceback
        logger.error(traceback.format_exc())


def renovar_gmail_watch():
    """
    Renova o watch do Gmail (se estiver usando Push).
    Executado a cada 6 dias.
    """
    logger.info("Renovando watch do Gmail...")
    # Implementação futura para Push notifications
    pass


if __name__ == "__main__":
    verificar_emails()
