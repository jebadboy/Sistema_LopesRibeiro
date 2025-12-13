"""
Módulo de integração com Google Drive usando Service Account.
Permite upload de arquivos e gestão de pastas sem intervenção humana.

Features Sprint 3:
- Refresh automático de token quando expira
- Tratamento robusto de erros de autenticação
"""

import os
import logging
import time
from functools import wraps
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Escopos
SCOPES = ['https://www.googleapis.com/auth/drive']

# Caminho do arquivo de credenciais (Service Account)
SERVICE_ACCOUNT_FILE = 'service_account.json'

# ID da pasta alvo no Google Drive (Compartilhada com a Service Account)
PASTA_ALVO_ID = '1wJENklSqCOYbCIoq4MaBiLncVzD1B69R'

try:
    import streamlit as st
    if "DRIVE_PASTA_ALVO_ID" in st.secrets:
        PASTA_ALVO_ID = st.secrets["DRIVE_PASTA_ALVO_ID"]
except:
    pass

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# Cache global do service para reutilização
_drive_service = None
_last_auth_time = None

def autenticar(force_refresh: bool = False):
    """
    Autentica usando OAuth (token.json) ou Service Account.
    Prioridade:
    1. Streamlit Secrets (Produção)
    2. OAuth (Usuário Local) - com refresh automático
    3. Service Account File (Fallback Local)
    
    Args:
        force_refresh: Forçar re-autenticação (ignora cache)
    """
    global _drive_service, _last_auth_time
    import streamlit as st
    
    # Reutilizar service se autenticado recentemente (< 45 min)
    if not force_refresh and _drive_service and _last_auth_time:
        age_minutes = (time.time() - _last_auth_time) / 60
        if age_minutes < 45:
            return _drive_service
    
    # 1. Tentar Streamlit Secrets (Produção)
    if "gcp_service_account" in st.secrets:
        try:
            service_account_info = st.secrets["gcp_service_account"]
            creds = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=SCOPES
            )
            service = build('drive', 'v3', credentials=creds)
            logger.info("Autenticado via Streamlit Secrets (Service Account)")
            _drive_service = service
            _last_auth_time = time.time()
            return service
        except Exception as e:
            logger.error(f"Erro ao autenticar via Secrets: {e}")

    creds = None
    
    # 2. Tentar OAuth (Usuário)
    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            
            # Verificar se precisa refresh
            if creds and creds.expired and creds.refresh_token:
                logger.info("[Drive] Token expirado, fazendo refresh...")
                creds.refresh(Request())
                
                # Salvar token atualizado para próxima vez
                with open('token.json', 'w') as token_file:
                    token_file.write(creds.to_json())
                logger.info("[Drive] Token renovado e salvo com sucesso!")
            
            service = build('drive', 'v3', credentials=creds)
            _drive_service = service
            _last_auth_time = time.time()
            return service
        except Exception as e:
            logger.error(f"Erro na autenticação OAuth: {e}")
            # Fallback para Service Account
    
    # 3. Fallback para Service Account File
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        logger.error(f"Arquivo de credenciais não encontrado: {SERVICE_ACCOUNT_FILE}")
        return None

    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build('drive', 'v3', credentials=creds)
        _drive_service = service
        _last_auth_time = time.time()
        return service
    except Exception as e:
        logger.error(f"Erro na autenticação do Drive: {e}")
        return None

def retry_on_auth_error(func):
    """
    Decorator que re-autentica e tenta novamente em caso de erro 401/403.
    
    Uso:
        @retry_on_auth_error
        def upload_file(service, ...):
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HttpError as e:
            if e.resp.status in [401, 403]:
                logger.warning(f"[Drive] Erro de autenticação ({e.resp.status}), tentando re-autenticar...")
                
                # Forçar re-autenticação
                new_service = autenticar(force_refresh=True)
                
                if new_service:
                    # Substituir o primeiro argumento (service) pelo novo
                    if args:
                        args = (new_service,) + args[1:]
                    return func(*args, **kwargs)
                else:
                    logger.error("[Drive] Falha ao re-autenticar!")
                    raise
            else:
                raise
        except Exception as e:
            logger.error(f"[Drive] Erro inesperado: {e}")
            raise
    
    return wrapper



def find_folder(service, folder_name, parent_id=None):
    """
    Procura uma pasta pelo nome.
    Retorna o ID da pasta ou None se não encontrar.
    """
    try:
        query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        results = service.files().list(
            q=query, fields="files(id, name)"
        ).execute()
        
        files = results.get('files', [])
        if files:
            return files[0]['id']
        return None
    except Exception as e:
        logger.error(f"Erro ao buscar pasta {folder_name}: {e}")
        return None

def create_folder(service, folder_name, parent_id=None):
    """
    Cria uma pasta no Drive.
    Retorna o ID da nova pasta.
    """
    try:
        # Primeiro verifica se já existe
        existing_id = find_folder(service, folder_name, parent_id)
        if existing_id:
            return existing_id

        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]

        file = service.files().create(
            body=file_metadata, fields='id'
        ).execute()
        
        logger.info(f"Pasta criada: {folder_name} (ID: {file.get('id')})")
        return file.get('id')
    except Exception as e:
        logger.error(f"Erro ao criar pasta {folder_name}: {e}")
        return None

def upload_file(service, file_path, folder_id=None, mime_type=None):
    """
    Faz upload de um arquivo para o Drive.
    Retorna o ID do arquivo e o Link de Visualização.
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"Arquivo local não encontrado: {file_path}")
            return None, None

        file_name = os.path.basename(file_path)
        
        # Usar pasta alvo configurada se não for passada
        target_folder = folder_id or PASTA_ALVO_ID
        
        file_metadata = {'name': file_name}
        if target_folder:
            file_metadata['parents'] = [target_folder]

        media = MediaFileUpload(file_path, mimetype=mime_type)

        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()

        logger.info(f"Arquivo enviado: {file_name} (ID: {file.get('id')})")
        return file.get('id'), file.get('webViewLink')
    except Exception as e:
        logger.error(f"Erro ao enviar arquivo {file_path}: {e}")
        print(f"DEBUG ERROR: {e}")
        return None, None

def listar_arquivos(service, folder_id):
    """
    Lista arquivos dentro de uma pasta.
    Retorna lista de dicts: [{'id':, 'name':, 'webViewLink':, 'mimeType':}]
    """
    try:
        query = f"'{folder_id}' in parents and trashed=false"
        response = service.files().list(
            q=query, 
            fields="files(id, name, webViewLink, mimeType, createdTime)",
            orderBy="createdTime desc"
        ).execute()
        return response.get('files', [])
    except Exception as e:
        logger.error(f"Erro ao listar arquivos da pasta {folder_id}: {e}")
        return []

def set_permission_anyone_reader(service, file_id):
    """
    Define permissão de leitura para qualquer pessoa com o link.
    Útil se quiser que o link seja acessível facilmente.
    """
    try:
        user_permission = {
            'type': 'anyone',
            'role': 'reader',
        }
        service.permissions().create(
            fileId=file_id,
            body=user_permission,
            fields='id',
        ).execute()
        return True
    except Exception as e:
        logger.error(f"Erro ao definir permissão: {e}")
        return False
