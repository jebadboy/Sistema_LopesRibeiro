"""
Scheduled Tasks - Sistema Lopes & Ribeiro
Script para execução via Windows Task Scheduler ou Cron.

Funcionalidades:
1. Gerar insights periódicos (prazos, processos parados, inadimplência)
2. Verificar recorrências financeiras
3. (Opcional) Verificar e-mails do Gmail

Configuração do Windows Task Scheduler:
    1. Abra o Agendador de Tarefas do Windows (taskschd.msc)
    2. Criar Tarefa Básica
    3. Nome: LopesRibeiro_DailyInsights
    4. Disparador: Diariamente às 07:00
    5. Ação: Iniciar um programa
    6. Programa: pythonw.exe (para rodar em background) ou python.exe
    7. Argumentos: "H:/Meu Drive/automatizacao/Sistema_LopesRibeiro/scheduled_tasks.py"
    8. Iniciar em: "H:/Meu Drive/automatizacao/Sistema_LopesRibeiro"
"""

import os
import sys
from datetime import datetime

# Configura path do projeto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# Usar módulo centralizado de logging com rotação automática
from logging_config import get_tasks_logger, LOG_DIR
logger = get_tasks_logger()
LOG_FILE = os.path.join(LOG_DIR, 'scheduled_tasks.log')


def run_all_tasks():
    """Executa todas as tarefas programadas."""
    logger.info("=" * 60)
    logger.info(f"INICIANDO TAREFAS PROGRAMADAS - {datetime.now()}")
    logger.info("=" * 60)
    
    total_insights = 0
    
    # =====================================================
    # 1. GERAÇÃO DE INSIGHTS (IA Proativa)
    # =====================================================
    try:
        logger.info("\n--- Tarefa 1: Geração de Insights ---")
        
        import database as db
        from modules import ai_proactive
        
        # Inicializar banco
        db.init_db()
        
        # Inicializar IA Proativa (subscreve aos sinais)
        ai_proactive.inicializar()
        
        # Gerar insights periódicos
        insights = ai_proactive.generate_insights()
        total_insights += insights if insights else 0
        
        logger.info(f"✅ Insights gerados: {insights}")
        
    except Exception as e:
        logger.error(f"❌ Erro na geração de insights: {e}")
        import traceback
        logger.error(traceback.format_exc())
    
    # =====================================================
    # 2. VERIFICAR RECORRÊNCIAS FINANCEIRAS
    # =====================================================
    try:
        logger.info("\n--- Tarefa 2: Recorrências Financeiras ---")
        
        from modules import financeiro
        
        financeiro.verificar_recorrencias()
        logger.info("✅ Recorrências verificadas")
        
    except Exception as e:
        logger.error(f"❌ Erro nas recorrências: {e}")
    
    # =====================================================
    # 3. (OPCIONAL) VERIFICAR E-MAILS GMAIL
    # =====================================================
    # Descomente se quiser integrar com email_scheduler
    # try:
    #     logger.info("\n--- Tarefa 3: Verificação de E-mails ---")
    #     from email_scheduler import verificar_emails
    #     verificar_emails()
    #     logger.info("✅ E-mails verificados")
    # except Exception as e:
    #     logger.error(f"❌ Erro na verificação de e-mails: {e}")
    
    # =====================================================
    # RESUMO FINAL
    # =====================================================
    logger.info("\n" + "=" * 60)
    logger.info(f"TAREFAS CONCLUÍDAS - {datetime.now()}")
    logger.info(f"Total de insights gerados: {total_insights}")
    logger.info("=" * 60)
    
    return total_insights


def run_manual_test():
    """Teste manual para verificar se tudo funciona."""
    print("\n🔧 EXECUTANDO TESTE MANUAL\n")
    print("Este script pode ser agendado no Windows Task Scheduler.")
    print("Veja as instruções no cabeçalho deste arquivo.\n")
    
    resultado = run_all_tasks()
    
    print(f"\n✅ Teste concluído! {resultado} insights gerados.")
    print(f"📄 Verifique o log em: {LOG_FILE}")
    
    return resultado


if __name__ == "__main__":
    # Se executado diretamente (manual ou pelo scheduler)
    run_manual_test()
