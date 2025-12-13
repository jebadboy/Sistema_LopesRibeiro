"""
Configuração Centralizada de Logging - Sistema Lopes & Ribeiro

Implementa rotação automática de logs com:
- Limite de 5MB por arquivo
- Mantém 3 backups (.log.1, .log.2, .log.3)
- Formato padronizado com timestamp
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

# Diretório base do sistema
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, 'logs')

# Criar diretório de logs se não existir
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Configurações de rotação
MAX_BYTES = 5 * 1024 * 1024  # 5MB
BACKUP_COUNT = 3  # Mantém 3 arquivos de backup

def get_logger(name: str, log_file: str = None) -> logging.Logger:
    """
    Retorna um logger configurado com rotação automática.
    
    Args:
        name: Nome do logger (geralmente __name__)
        log_file: Nome do arquivo de log (opcional, padrão: sistema.log)
    
    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    
    # Evitar handlers duplicados
    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)
    
    # Arquivo de log
    if log_file is None:
        log_file = 'sistema.log'
    
    log_path = os.path.join(LOG_DIR, log_file)
    
    # Handler com rotação
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    
    # Formato do log
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    # Também log para console em desenvolvimento
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Só warnings+ no console
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# Logger principal do sistema
sistema_logger = get_logger('sistema', 'sistema.log')

# Loggers específicos
def get_email_logger():
    """Logger para o scheduler de e-mails"""
    return get_logger('email_scheduler', 'email_scheduler.log')

def get_tasks_logger():
    """Logger para tarefas agendadas"""
    return get_logger('scheduled_tasks', 'scheduled_tasks.log')

def get_datajud_logger():
    """Logger para integração DataJud"""
    return get_logger('datajud', 'datajud.log')
