"""
Módulo de Sinais (Event Bus) - Sistema Lopes & Ribeiro

Permite que partes do sistema reajam a eventos em tempo real.
Usado para:
- IA Proativa reagir a novos clientes/processos
- Log centralizado de atividades
- Dashboard de atividade recente
"""

import logging
from datetime import datetime
from collections import deque
from typing import Callable, Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Dicionário de assinantes: { 'evento': [funcao1, funcao2] }
_subscribers: Dict[str, List[Callable]] = {}

# Buffer de eventos recentes (últimos 100)
_event_log: deque = deque(maxlen=100)

# Contadores de eventos
_event_counters: Dict[str, int] = {}


def subscribe(event_name: str, callback: Callable) -> bool:
    """
    Inscreve uma função para ser chamada quando o evento ocorrer.
    
    Args:
        event_name: Nome do evento (ex: 'insert_clientes')
        callback: Função a ser chamada
    
    Returns:
        True se inscrito com sucesso, False se já estava inscrito
    """
    if event_name not in _subscribers:
        _subscribers[event_name] = []
    
    # Evitar duplicidade (comum no Streamlit devido aos reruns)
    if callback not in _subscribers[event_name]:
        _subscribers[event_name].append(callback)
        logger.info(f"Função {callback.__name__} inscrita no evento {event_name}")
        return True
    else:
        logger.debug(f"Função {callback.__name__} já inscrita em {event_name}")
        return False


def unsubscribe(event_name: str, callback: Callable) -> bool:
    """Remove uma função da lista de assinantes."""
    if event_name in _subscribers and callback in _subscribers[event_name]:
        _subscribers[event_name].remove(callback)
        logger.info(f"Função {callback.__name__} removida do evento {event_name}")
        return True
    return False


def emit(event_name: str, data: Any = None) -> int:
    """
    Emite um evento, chamando todos os assinantes.
    
    Args:
        event_name: Nome do evento
        data: Dados a serem passados para os callbacks
    
    Returns:
        Número de callbacks executados com sucesso
    """
    # Registrar no log de eventos
    _log_event(event_name, data)
    
    # Incrementar contador
    _event_counters[event_name] = _event_counters.get(event_name, 0) + 1
    
    # Executar callbacks
    success_count = 0
    if event_name in _subscribers:
        for callback in _subscribers[event_name]:
            try:
                callback(data)
                success_count += 1
            except Exception as e:
                logger.error(f"Erro ao processar evento {event_name} na função {callback.__name__}: {e}")
    
    return success_count


def _log_event(event_name: str, data: Any = None):
    """Registra evento no buffer de log."""
    event_entry = {
        'timestamp': datetime.now().isoformat(),
        'event': event_name,
        'data': _sanitize_data(data),
        'tipo': _get_event_type(event_name)
    }
    _event_log.append(event_entry)


def _sanitize_data(data: Any) -> Optional[Dict]:
    """Remove dados sensíveis antes de logar."""
    if data is None:
        return None
    if isinstance(data, dict):
        # Remover campos sensíveis
        sanitized = {}
        sensitive_fields = ['password', 'senha', 'token', 'secret', 'hash']
        for key, value in data.items():
            if any(s in key.lower() for s in sensitive_fields):
                sanitized[key] = '***'
            else:
                sanitized[key] = str(value)[:100]  # Limitar tamanho
        return sanitized
    return str(data)[:100]


def _get_event_type(event_name: str) -> str:
    """Classifica o tipo do evento."""
    if event_name.startswith('insert_'):
        return 'create'
    elif event_name.startswith('update_'):
        return 'update'
    elif event_name.startswith('delete_'):
        return 'delete'
    else:
        return 'other'


# === FUNÇÕES DE CONSULTA ===

def get_recent_events(limit: int = 20) -> List[Dict]:
    """Retorna os eventos mais recentes."""
    events = list(_event_log)
    events.reverse()  # Mais recentes primeiro
    return events[:limit]


def get_event_counts() -> Dict[str, int]:
    """Retorna contadores de eventos por tipo."""
    return _event_counters.copy()


def get_events_by_type(event_type: str, limit: int = 20) -> List[Dict]:
    """Retorna eventos filtrados por tipo (create/update/delete)."""
    events = [e for e in _event_log if e['tipo'] == event_type]
    events.reverse()
    return events[:limit]


def get_subscribers_info() -> Dict[str, List[str]]:
    """Retorna informações sobre os assinantes registrados."""
    return {
        event: [cb.__name__ for cb in callbacks]
        for event, callbacks in _subscribers.items()
    }


def clear_event_log():
    """Limpa o log de eventos (útil para testes)."""
    _event_log.clear()
    _event_counters.clear()


# === EVENTOS PRÉ-DEFINIDOS ===

# Constantes para nomes de eventos (evita erros de digitação)
EVENT_INSERT_CLIENTE = 'insert_clientes'
EVENT_UPDATE_CLIENTE = 'update_clientes'
EVENT_DELETE_CLIENTE = 'delete_clientes'

EVENT_INSERT_PROCESSO = 'insert_processos'
EVENT_UPDATE_PROCESSO = 'update_processos'
EVENT_DELETE_PROCESSO = 'delete_processos'

EVENT_INSERT_FINANCEIRO = 'insert_financeiro'
EVENT_UPDATE_FINANCEIRO = 'update_financeiro'
EVENT_DELETE_FINANCEIRO = 'delete_financeiro'

EVENT_INSERT_AGENDA = 'insert_agenda'
EVENT_UPDATE_AGENDA = 'update_agenda'


def get_activity_summary() -> Dict[str, Any]:
    """
    Retorna resumo da atividade recente para o dashboard.
    
    Returns:
        Dict com contagens e eventos recentes
    """
    events = get_recent_events(50)
    
    # Contar por tipo
    creates = sum(1 for e in events if e['tipo'] == 'create')
    updates = sum(1 for e in events if e['tipo'] == 'update')
    deletes = sum(1 for e in events if e['tipo'] == 'delete')
    
    # Eventos por tabela
    tables = {}
    for e in events:
        table = e['event'].replace('insert_', '').replace('update_', '').replace('delete_', '')
        tables[table] = tables.get(table, 0) + 1
    
    return {
        'total_events': len(events),
        'creates': creates,
        'updates': updates,
        'deletes': deletes,
        'by_table': tables,
        'recent_5': events[:5]
    }
