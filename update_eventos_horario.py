import sqlite3
import logging

# Configuração de Logs
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = 'dados_escritorio.db'

def atualizar_eventos_sem_horario():
    """Atualiza eventos sem horário para ter 9:00 como padrão"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Verificar quantos eventos estão sem horário
        cursor.execute("SELECT COUNT(*) FROM agenda WHERE hora_evento IS NULL")
        total_sem_horario = cursor.fetchone()[0]
        
        if total_sem_horario == 0:
            logger.info("✅ Todos os eventos já possuem horário!")
            return
        
        logger.info(f"📊 Encontrados {total_sem_horario} eventos sem horário")
        
        # Atualizar com horário padrão 9:00
        cursor.execute("""
            UPDATE agenda 
            SET hora_evento = '09:00' 
            WHERE hora_evento IS NULL
        """)
        
        conn.commit()
        logger.info(f"✅ {cursor.rowcount} eventos atualizados com horário padrão 9:00")
        
        # Verificar resultado
        cursor.execute("SELECT COUNT(*) FROM agenda WHERE hora_evento IS NULL")
        restantes = cursor.fetchone()[0]
        logger.info(f"📊 Eventos ainda sem horário: {restantes}")
        
    except Exception as e:
        logger.error(f"❌ Erro na atualização: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("=" * 50)
    print("ATUALIZAÇÃO DE HORÁRIOS NA AGENDA")
    print("=" * 50)
    print("")
    
    atualizar_eventos_sem_horario()
    
    print("")
    print("=" * 50)
    print("CONCLUÍDO!")
    print("=" * 50)
