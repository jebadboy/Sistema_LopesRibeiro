"""
Módulo de integração com Google Drive usando Service Account.
Permite upload de arquivos e gestão de pastas sem intervenção humana.
"""

import os
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Escopos
SCOPES = ['https://www.googleapis.com/auth/drive']

# Caminho do arquivo de credenciais (Service Account)
# Caminho do arquivo de credenciais (Service Account)
SERVICE_ACCOUNT_FILE = 'service_account.json'

# ID da pasta alvo no Google Drive (Compartilhada com a Service Account)
# O usuário deve fornecer este ID.
PASTA_ALVO_ID = '1wJENklSqCOYbCIoq4MaBiLncVzD1B69R'

try:
    import streamlit as st
    if "DRIVE_PASTA_ALVO_ID" in st.secrets:
        PASTA_ALVO_ID = st.secrets["DRIVE_PASTA_ALVO_ID"]
except:
    pass

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

def autenticar():
    """
    Autentica usando OAuth (token.json) ou Service Account.
    Prioridade:
    1. Streamlit Secrets (Produção)
    2. OAuth (Usuário Local)
    3. Service Account File (Fallback Local)
    """
    import streamlit as st
    
    # 1. Tentar Streamlit Secrets (Produção)
    if "gcp_service_account" in st.secrets:
        try:
            service_account_info = st.secrets["gcp_service_account"]
            creds = service_account.Credentials.from_service_account_info(
                service_account_info, scopes=SCOPES
            )
            service = build('drive', 'v3', credentials=creds)
            logger.info("Autenticado via Streamlit Secrets (Service Account)")
            return service
        except Exception as e:
            logger.error(f"Erro ao autenticar via Secrets: {e}")

    creds = None
    
    # 2. Tentar OAuth (Usuário)
    if os.path.exists('token.json'):
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            
            service = build('drive', 'v3', credentials=creds)
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
        return service
    except Exception as e:
        logger.error(f"Erro na autenticação do Drive: {e}")
        return None

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
