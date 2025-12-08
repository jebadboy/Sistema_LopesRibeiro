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
import logging
from datetime import datetime

# Configura path do projeto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Configuração de logging
LOG_FILE = os.path.join(BASE_DIR, 'scheduler.log')
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


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
                # Verificar se já existe alerta similar (evitar duplicatas)
                existente = db.sql_get_query("""
                    SELECT id FROM alertas_email 
                    WHERE assunto = ? AND data_recebimento = ?
                    LIMIT 1
                """, [alerta.assunto[:200], alerta.data_recebimento])
                
                if existente.empty:
                    db.crud_insert("alertas_email", {
                        "tipo": alerta.tipo.value,
                        "remetente": alerta.remetente,
                        "assunto": alerta.assunto[:200],
                        "numero_processo": alerta.numero_processo,
                        "valor_detectado": alerta.valor_detectado,
                        "data_recebimento": alerta.data_recebimento,
                        "corpo_resumo": alerta.corpo_resumo[:1000],
                        "processado": 0,
                        "criado_em": datetime.now().isoformat()
                    })
                    novos_alertas += 1
                    logger.info(f"Alerta salvo: {alerta.tipo.value} - {alerta.assunto[:50]}...")
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
