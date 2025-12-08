"""
Módulo de Sinais (Event Bus)
Permite que partes do sistema (como a IA) reajam a eventos (como criação de cliente).
"""

import logging

logger = logging.getLogger(__name__)

# Dicionário de assinantes: { 'evento': [funcao1, funcao2] }
_subscribers = {}

def subscribe(event_name, callback):
    """Inscreve uma função para ser chamada quando o evento ocorrer."""
    if event_name not in _subscribers:
        _subscribers[event_name] = []
    
    # Evitar duplicidade (comum no Streamlit devido aos reruns)
    if callback not in _subscribers[event_name]:
        _subscribers[event_name].append(callback)
        logger.info(f"Função {callback.__name__} inscrita no evento {event_name}")
    else:
        logger.debug(f"Função {callback.__name__} já inscrita em {event_name}")

def emit(event_name, data=None):
    """Emite um evento, chamando todos os assinantes."""
    if event_name in _subscribers:
        for callback in _subscribers[event_name]:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Erro ao processar evento {event_name} na função {callback.__name__}: {e}")
