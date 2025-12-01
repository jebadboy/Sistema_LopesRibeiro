"""
Helper de integração com Google Calendar API.
Gerencia autenticação OAuth 2.0 e sincronização bidirecional de eventos.
"""

import os
import pickle
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import streamlit as st
import database as db
import logging

logger = logging.getLogger(__name__)

# Escopos necessários para Google Calendar
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]

CREDENTIALS_FILE = 'credentials.json'
TOKEN_DIR = os.getenv('DATA_DIR', '.')


def get_token_file(username):
    """Retorna o caminho do arquivo de token para o usuário."""
    return os.path.join(TOKEN_DIR, f'token_{username}.pickle')


def verificar_autenticacao(username):
    """Verifica se o usuário está autenticado com Google Calendar."""
    token_file = get_token_file(username)
    return os.path.exists(token_file)


def autenticar_google(username):
    """
    Autentica usuário com Google Calendar usando OAuth 2.0.
    Retorna objeto de serviço da API ou None se falhar.
    """
    creds = None
    token_file = get_token_file(username)
    
    try:
        # Verificar se já existe token salvo
        if os.path.exists(token_file):
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
        
        # Se não há credenciais válidas, fazer login
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Token expirado, renovar
                creds.refresh(Request())
                logger.info(f"Token renovado para usuário {username}")
            else:
                # Primeira autenticação
                if not os.path.exists(CREDENTIALS_FILE):
                    logger.error(f"Arquivo {CREDENTIALS_FILE} não encontrado!")
                    return None
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
                logger.info(f"Autenticação realizada com sucesso para {username}")
            
            # Salvar credenciais para próxima execução
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
        
        # Criar serviço Google Calendar
        service = build('calendar', 'v3', credentials=creds)
        return service
    
    except Exception as e:
        logger.error(f"Erro na autenticação Google Calendar: {e}")
        return None


def desconectar_google(username):
    """Remove tokens de autenticação do usuário."""
    token_file = get_token_file(username)
    try:
        if os.path.exists(token_file):
            os.remove(token_file)
            logger.info(f"Usuário {username} desconectado do Google Calendar")
            return True
    except Exception as e:
        logger.error(f"Erro ao desconectar: {e}")
    return False


def criar_evento_google(service, evento_data):
    """
    Cria evento no Google Calendar.
    
    Args:
        service: Serviço Google Calendar autenticado
        evento_data: Dict com dados do evento (titulo, descricao, data_evento, etc)
    
    Returns:
        str: ID do evento no Google Calendar ou None se falhar
    """
    try:
        # Converter data do evento para formato Google Calendar
        data_evento = datetime.strptime(evento_data['data_evento'], '%Y-%m-%d')
        
        # Montar evento no formato Google Calendar
        event = {
            'summary': evento_data['titulo'],
            'description': evento_data.get('descricao', ''),
            'start': {
                'date': data_evento.strftime('%Y-%m-%d'),
                'timeZone': 'America/Sao_Paulo',
            },
            'end': {
                'date': (data_evento + timedelta(days=1)).strftime('%Y-%m-%d'),
                'timeZone': 'America/Sao_Paulo',
            },
            'reminders': {
                'useDefault': False,
                'overrides': [
                    {'method': 'popup', 'minutes': 24 * 60},  # 1 dia antes
                    {'method': 'popup', 'minutes': 60},  # 1 hora antes
                ],
            },
        }
        
        # Adicionar cor baseada na prioridade
        cores_prioridade = {
            'baixa': '2',    # Verde
            'media': '5',    # Amarelo
            'alta': '11',    # Vermelho
            'urgente': '11'  # Vermelho
        }
        prioridade = evento_data.get('prioridade', 'media')
        event['colorId'] = cores_prioridade.get(prioridade, '5')
        
        # Criar evento no calendário
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        
        logger.info(f"Evento criado no Google Calendar: {created_event['id']}")
        return created_event['id']
    
    except Exception as e:
        logger.error(f"Erro ao criar evento no Google Calendar: {e}")
        return None


def atualizar_evento_google(service, google_calendar_id, evento_data):
    """
    Atualiza evento existente no Google Calendar.
    
    Args:
        service: Serviço Google Calendar autenticado
        google_calendar_id: ID do evento no Google Calendar
        evento_data: Dict com novos dados do evento
    
    Returns:
        bool: True se atualizado com sucesso
    """
    try:
        # Buscar evento existente
        event = service.events().get(calendarId='primary', eventId=google_calendar_id).execute()
        
        # Atualizar campos
        data_evento = datetime.strptime(evento_data['data_evento'], '%Y-%m-%d')
        
        event['summary'] = evento_data['titulo']
        event['description'] = evento_data.get('descricao', '')
        event['start'] = {
            'date': data_evento.strftime('%Y-%m-%d'),
            'timeZone': 'America/Sao_Paulo',
        }
        event['end'] = {
            'date': (data_evento + timedelta(days=1)).strftime('%Y-%m-%d'),
            'timeZone': 'America/Sao_Paulo',
        }
        
        # Atualizar cor baseada na prioridade
        cores_prioridade = {
            'baixa': '2', 'media': '5', 'alta': '11', 'urgente': '11'
        }
        prioridade = evento_data.get('prioridade', 'media')
        event['colorId'] = cores_prioridade.get(prioridade, '5')
        
        # Atualizar no calendário
        updated_event = service.events().update(
            calendarId='primary', 
            eventId=google_calendar_id, 
            body=event
        ).execute()
        
        logger.info(f"Evento atualizado no Google Calendar: {google_calendar_id}")
        return True
    
    except Exception as e:
        logger.error(f"Erro ao atualizar evento no Google Calendar: {e}")
        return False


def excluir_evento_google(service, google_calendar_id):
    """
    Exclui evento do Google Calendar.
    
    Args:
        service: Serviço Google Calendar autenticado
        google_calendar_id: ID do evento no Google Calendar
    
    Returns:
        bool: True se excluído com sucesso
    """
    try:
        service.events().delete(calendarId='primary', eventId=google_calendar_id).execute()
        logger.info(f"Evento excluído do Google Calendar: {google_calendar_id}")
        return True
    except Exception as e:
        logger.error(f"Erro ao excluir evento do Google Calendar: {e}")
        return False


def importar_eventos_google(service, data_inicio=None, data_fim=None):
    """
    Importa eventos do Google Calendar para o sistema.
    
    Args:
        service: Serviço Google Calendar autenticado
        data_inicio: Data inicial para filtro (opcional)
        data_fim: Data final para filtro (opcional)
    
    Returns:
        list: Lista de eventos importados
    """
    try:
        # Definir período de busca (próximos 90 dias se não especificado)
        if not data_inicio:
            data_inicio = datetime.now()
        if not data_fim:
            data_fim = data_inicio + timedelta(days=90)
        
        # Buscar eventos
        events_result = service.events().list(
            calendarId='primary',
            timeMin=data_inicio.isoformat() + 'Z',
            timeMax=data_fim.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        eventos_importados = []
        for event in events:
            # Verificar se evento já existe no sistema
            google_id = event['id']
            
            # Preparar dados do evento
            titulo = event.get('summary', 'Sem título')
            descricao = event.get('description', '')
            
            # Extrair data
            start = event['start'].get('date') or event['start'].get('dateTime', '')
            if start:
                if 'T' in start:  # datetime
                    data_evento = start.split('T')[0]
                else:  # date
                    data_evento = start
            else:
                continue
            
            eventos_importados.append({
                'google_calendar_id': google_id,
                'titulo': titulo,
                'descricao': descricao,
                'data_evento': data_evento,
                'tipo': 'tarefa',  # Padrão
                'status': 'pendente',
                'prioridade': 'media'
            })
        
        logger.info(f"Importados {len(eventos_importados)} eventos do Google Calendar")
        return eventos_importados
    
    except Exception as e:
        logger.error(f"Erro ao importar eventos do Google Calendar: {e}")
        return []


def sincronizar_evento(username, evento_id, evento_data, operacao='criar'):
    """
    Sincroniza evento com Google Calendar.
    
    Args:
        username: Nome do usuário
        evento_id: ID do evento no sistema local
        evento_data: Dados do evento
        operacao: 'criar', 'atualizar' ou 'excluir'
    
    Returns:
        str ou bool: ID do Google Calendar (criar), True/False (atualizar/excluir)
    """
    # Verificar se usuário está autenticado
    if not verificar_autenticacao(username):
        logger.warning(f"Usuário {username} não autenticado no Google Calendar")
        return None if operacao == 'criar' else False
    
    # Autenticar
    service = autenticar_google(username)
    if not service:
        return None if operacao == 'criar' else False
    
    # Executar operação
    if operacao == 'criar':
        return criar_evento_google(service, evento_data)
    elif operacao == 'atualizar':
        google_id = evento_data.get('google_calendar_id')
        if google_id:
            return atualizar_evento_google(service, google_id, evento_data)
        return False
    elif operacao == 'excluir':
        google_id = evento_data.get('google_calendar_id')
        if google_id:
            return excluir_evento_google(service, google_id)
        return False
    
    return None
