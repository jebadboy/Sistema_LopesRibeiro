"""
Módulo de Integração com Google Workspace
Sistema Lopes & Ribeiro - Unificação Drive, Gmail e Calendar

Este módulo centraliza todas as integrações com Google Workspace,
permitindo:
- Gestão documental automática no Drive
- Monitoramento de e-mails de tribunais
- Sincronização inteligente com Calendar
"""

import os
import io
import re
import logging
import base64
import pickle
from dataclasses import dataclass
from typing import Optional, List, Dict, Callable
from enum import Enum
from datetime import datetime, timedelta

# Google APIs
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

# PDF
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

# Streamlit (para secrets)
try:
    import streamlit as st
    STREAMLIT_AVAILABLE = True
except ImportError:
    STREAMLIT_AVAILABLE = False

# Módulos internos
import database as db

logger = logging.getLogger(__name__)

# ==============================================================================
# CONSTANTES E CONFIGURAÇÕES
# ==============================================================================

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/cloud-vision'
]

SERVICE_ACCOUNT_FILE = 'service_account.json'
TOKEN_DIR = os.getenv('DATA_DIR', '.')


# ==============================================================================
# ENUMS E DATACLASSES
# ==============================================================================

class AlertType(Enum):
    """Tipos de alertas financeiros detectados em e-mails."""
    ALVARA = "alvará"
    MANDADO_PAGAMENTO = "mandado_pagamento"
    DEPOSITO = "depósito"
    RPV = "rpv"
    PRECATORIO = "precatório"
    INTIMACAO = "intimação"
    CITACAO = "citação"


@dataclass
class EmailAlert:
    """Estrutura de um alerta de e-mail processado."""
    tipo: AlertType
    remetente: str
    assunto: str
    numero_processo: Optional[str]
    valor_detectado: Optional[float]
    data_recebimento: str
    corpo_resumo: str


# ==============================================================================
# GERENCIAMENTO DE TOKENS E CREDENCIAIS
# ==============================================================================

class TokenManager:
    """Gerencia refresh de tokens OAuth."""
    
    MAX_REFRESH_ATTEMPTS = 3
    
    @staticmethod
    def get_token_file(username: str) -> str:
        """Retorna o caminho do arquivo de token para o usuário."""
        return os.path.join(TOKEN_DIR, f"token_{username}.pickle")
    
    @staticmethod
    def get_credentials(username: str = "sistema") -> Optional[Credentials]:
        """
        Obtém credenciais de forma segura.
        Prioridade:
        1. Streamlit Secrets (Produção)
        2. Token OAuth existente
        3. Service Account File
        """
        # 1. Tentar Streamlit Secrets
        if STREAMLIT_AVAILABLE and "gcp_service_account" in st.secrets:
            try:
                return service_account.Credentials.from_service_account_info(
                    dict(st.secrets["gcp_service_account"]),
                    scopes=SCOPES
                )
            except Exception as e:
                logger.error(f"Erro ao usar Streamlit Secrets: {e}")
        
        # 2. Tentar Token OAuth
        token_file = TokenManager.get_token_file(username)
        if os.path.exists(token_file):
            try:
                with open(token_file, 'rb') as f:
                    creds = pickle.load(f)
                if creds and creds.valid:
                    return creds
                if creds and creds.expired and creds.refresh_token:
                    if TokenManager.refresh_credentials(creds, username):
                        return creds
            except Exception as e:
                logger.error(f"Erro ao carregar token: {e}")
        
        # 3. Fallback para Service Account
        if os.path.exists(SERVICE_ACCOUNT_FILE):
            try:
                return service_account.Credentials.from_service_account_file(
                    SERVICE_ACCOUNT_FILE,
                    scopes=SCOPES
                )
            except Exception as e:
                logger.error(f"Erro ao usar Service Account: {e}")
        
        return None
    
    @staticmethod
    def refresh_credentials(creds: Credentials, username: str) -> bool:
        """
        Tenta renovar credenciais expiradas.
        Returns: True se renovado, False se precisa reautenticar.
        """
        for attempt in range(TokenManager.MAX_REFRESH_ATTEMPTS):
            try:
                creds.refresh(Request())
                TokenManager.save_token(creds, username)
                logger.info(f"Token renovado para {username}")
                return True
            except RefreshError as e:
                logger.warning(f"Tentativa {attempt+1} falhou: {e}")
                if attempt == TokenManager.MAX_REFRESH_ATTEMPTS - 1:
                    TokenManager.invalidate_token(username)
                    return False
        return False
    
    @staticmethod
    def save_token(creds: Credentials, username: str):
        """Salva token atualizado."""
        token_file = TokenManager.get_token_file(username)
        with open(token_file, 'wb') as f:
            pickle.dump(creds, f)
    
    @staticmethod
    def invalidate_token(username: str):
        """Remove token inválido."""
        token_file = TokenManager.get_token_file(username)
        if os.path.exists(token_file):
            os.remove(token_file)
            logger.info(f"Token removido: {token_file}")


# ==============================================================================
# TRATAMENTO DE COTAS
# ==============================================================================

class QuotaHandler:
    """Gerencia limites de quota das APIs Google."""
    
    @staticmethod
    def handle_api_error(error: HttpError) -> bool:
        """
        Trata erros de API com retry inteligente.
        Returns: True se deve tentar novamente, False caso contrário.
        """
        if error.resp.status == 429:
            retry_after = int(error.resp.get('Retry-After', 60))
            logger.warning(f"Rate limit atingido. Aguardando {retry_after}s")
            import time
            time.sleep(retry_after)
            return True
        elif error.resp.status == 403:
            logger.error("Quota excedida ou permissão negada")
            return False
        elif error.resp.status >= 500:
            logger.warning("Erro no servidor Google, tentando novamente...")
            import time
            time.sleep(5)
            return True
        return False


# ==============================================================================
# DRIVE CLIENT
# ==============================================================================

class DriveClient:
    """
    Gerencia operações do Google Drive.
    Expande funcionalidades com leitura de PDFs e OCR.
    """
    
    PASTA_RAIZ_CLIENTES = "Clientes"
    
    def __init__(self):
        self.service = None
        self.pasta_raiz_id = None
    
    def conectar(self, username: str = "sistema") -> bool:
        """Conecta ao Google Drive."""
        try:
            creds = TokenManager.get_credentials(username)
            if not creds:
                logger.error("Credenciais não disponíveis para Drive")
                return False
            
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Conectado ao Google Drive")
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar ao Drive: {e}")
            return False
    
    def _find_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """Busca pasta pelo nome."""
        try:
            query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            results = self.service.files().list(
                q=query, fields="files(id, name)"
            ).execute()
            
            files = results.get('files', [])
            return files[0]['id'] if files else None
        except HttpError as e:
            if QuotaHandler.handle_api_error(e):
                return self._find_folder(folder_name, parent_id)
            return None
    
    def _create_folder(self, folder_name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """Cria pasta no Drive."""
        try:
            # Verificar se já existe
            existing = self._find_folder(folder_name, parent_id)
            if existing:
                return existing
            
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                file_metadata['parents'] = [parent_id]
            
            file = self.service.files().create(
                body=file_metadata, fields='id'
            ).execute()
            
            logger.info(f"Pasta criada: {folder_name}")
            return file.get('id')
        except HttpError as e:
            if QuotaHandler.handle_api_error(e):
                return self._create_folder(folder_name, parent_id)
            return None
    
    def criar_estrutura_cliente(
        self, 
        nome_cliente: str, 
        numero_processo: Optional[str] = None
    ) -> Dict[str, Optional[str]]:
        """
        Cria estrutura: Clientes / [Nome] / [Processo]
        Returns: {"cliente_folder_id": "...", "processo_folder_id": "..."}
        """
        result = {"cliente_folder_id": None, "processo_folder_id": None}
        
        if not self.service:
            logger.error("Drive não conectado")
            return result
        
        try:
            # Encontrar ou criar pasta raiz "Clientes"
            if not self.pasta_raiz_id:
                self.pasta_raiz_id = self._create_folder(self.PASTA_RAIZ_CLIENTES)
            
            if not self.pasta_raiz_id:
                logger.error("Não foi possível criar pasta raiz")
                return result
            
            # Criar pasta do cliente
            cliente_folder_id = self._create_folder(nome_cliente, self.pasta_raiz_id)
            result["cliente_folder_id"] = cliente_folder_id
            
            # Criar pasta do processo (se fornecido)
            if numero_processo and cliente_folder_id:
                processo_folder_id = self._create_folder(numero_processo, cliente_folder_id)
                result["processo_folder_id"] = processo_folder_id
            
            return result
        except Exception as e:
            logger.error(f"Erro ao criar estrutura: {e}")
            return result
    
    def ler_pdf_texto(self, file_id: str) -> str:
        """
        Baixa PDF do Drive e extrai texto com PyMuPDF.
        Para PDFs escaneados, usa Google Vision OCR.
        """
        if not self.service:
            return ""
        
        try:
            # Baixar arquivo
            request = self.service.files().get_media(fileId=file_id)
            file_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(file_buffer, request)
            
            done = False
            while not done:
                _, done = downloader.next_chunk()
            
            file_buffer.seek(0)
            
            # Tentar extrair com PyMuPDF
            if PYMUPDF_AVAILABLE:
                text = self._extract_with_pymupdf(file_buffer)
                if text.strip():
                    return text
            
            # Fallback para OCR (Google Vision)
            file_buffer.seek(0)
            return self._extract_with_vision_ocr(file_buffer)
            
        except Exception as e:
            logger.error(f"Erro ao ler PDF: {e}")
            return ""
    
    def _extract_with_pymupdf(self, file_buffer: io.BytesIO) -> str:
        """Extrai texto usando PyMuPDF."""
        try:
            doc = fitz.open(stream=file_buffer.read(), filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception as e:
            logger.warning(f"PyMuPDF falhou: {e}")
            return ""
    
    def _extract_with_vision_ocr(self, file_buffer: io.BytesIO) -> str:
        """Extrai texto usando Google Cloud Vision OCR."""
        try:
            from google.cloud import vision
            
            client = vision.ImageAnnotatorClient()
            content = file_buffer.read()
            
            # Converter PDF para imagem e fazer OCR
            # Nota: Vision API precisa de imagens, não PDFs diretamente
            # Aqui usamos document_text_detection para PDFs
            image = vision.Image(content=content)
            response = client.document_text_detection(image=image)
            
            if response.error.message:
                logger.error(f"Vision API error: {response.error.message}")
                return ""
            
            return response.full_text_annotation.text
        except ImportError:
            logger.warning("google-cloud-vision não instalado")
            return ""
        except Exception as e:
            logger.error(f"Vision OCR falhou: {e}")
            return ""
    
    def enviar_para_analise_ia(
        self, 
        file_id: str, 
        tipo_documento: str = "petição"
    ) -> Dict:
        """
        Lê PDF e envia para ai_gemini.analisar_documento()
        Returns: Resultado da análise IA
        """
        texto = self.ler_pdf_texto(file_id)
        
        if not texto:
            return {"erro": "Não foi possível extrair texto do PDF"}
        
        try:
            from ai_gemini import analisar_documento
            return analisar_documento(texto, tipo_documento)
        except Exception as e:
            logger.error(f"Erro na análise IA: {e}")
            return {"erro": str(e)}


# ==============================================================================
# GMAIL WATCHER
# ==============================================================================

class GmailWatcher:
    """
    Monitora caixa de e-mail para intimações judiciais.
    Usa polling a cada 30 minutos (via Windows Task Scheduler).
    """
    
    REMETENTES_ALTA_PRIORIDADE = [
        "push@tjrj.jus.br",
        "pje@trt1.jus.br",
        "intimacao@tjrj.jus.br",
        "noreply@pje.jus.br",
        "naoresponda@trf2.jus.br",
        "citacao@tjrj.jus.br",
        "intimacoes@trf2.jus.br"
    ]
    
    PALAVRAS_CHAVE_FINANCEIRO = [
        "alvará", "mandado de pagamento", "depósito judicial",
        "rpv", "precatório", "pagamento liberado", "liberação de valores",
        "levantamento", "expedido alvará"
    ]
    
    PALAVRAS_CHAVE_PROCESSUAL = [
        "intimação", "citação", "prazo", "audiência",
        "sentença", "despacho", "decisão"
    ]
    
    def __init__(self):
        self.service = None
        self.last_history_id = None
    
    def conectar(self, username: str = "sistema") -> bool:
        """Conecta ao Gmail API."""
        try:
            creds = TokenManager.get_credentials(username)
            if not creds:
                logger.error("Credenciais não disponíveis para Gmail")
                return False
            
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("Conectado ao Gmail")
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar ao Gmail: {e}")
            return False
    
    def buscar_emails_recentes(
        self, 
        max_results: int = 50,
        dias_atras: int = 1
    ) -> List[Dict]:
        """
        Busca e-mails recentes para análise.
        Filtra por remetentes de tribunais e palavras-chave.
        """
        if not self.service:
            return []
        
        try:
            # Calcular data de corte
            data_corte = datetime.now() - timedelta(days=dias_atras)
            query = f"after:{data_corte.strftime('%Y/%m/%d')}"
            
            # Buscar mensagens
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for msg in messages:
                email_data = self._get_email_content(msg['id'])
                if email_data:
                    emails.append(email_data)
            
            return emails
        except HttpError as e:
            if QuotaHandler.handle_api_error(e):
                return self.buscar_emails_recentes(max_results, dias_atras)
            return []
    
    def _get_email_content(self, message_id: str) -> Optional[Dict]:
        """Obtém conteúdo de um e-mail específico."""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            headers = message.get('payload', {}).get('headers', [])
            
            # Extrair campos do cabeçalho
            email_data = {
                'id': message_id,
                'remetente': '',
                'assunto': '',
                'data': '',
                'corpo': ''
            }
            
            for header in headers:
                name = header.get('name', '').lower()
                value = header.get('value', '')
                if name == 'from':
                    email_data['remetente'] = value
                elif name == 'subject':
                    email_data['assunto'] = value
                elif name == 'date':
                    email_data['data'] = value
            
            # Extrair corpo
            email_data['corpo'] = self._extract_body(message.get('payload', {}))
            
            return email_data
        except Exception as e:
            logger.error(f"Erro ao obter e-mail {message_id}: {e}")
            return None
    
    def _extract_body(self, payload: Dict) -> str:
        """Extrai corpo do e-mail (texto plano ou HTML)."""
        body = ""
        
        if 'body' in payload and 'data' in payload['body']:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        elif 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    if 'data' in part.get('body', {}):
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                        break
                elif part.get('mimeType') == 'text/html' and not body:
                    if 'data' in part.get('body', {}):
                        html = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                        # Remover tags HTML básicas
                        import re
                        body = re.sub('<[^<]+?>', ' ', html)
        
        return body[:5000]  # Limitar tamanho
    
    def classificar_email(self, email_data: Dict) -> Optional[EmailAlert]:
        """
        Classifica e-mail e retorna alerta se relevante.
        """
        remetente = email_data.get('remetente', '').lower()
        assunto = email_data.get('assunto', '').lower()
        corpo = email_data.get('corpo', '').lower()
        texto_completo = f"{assunto} {corpo}"
        
        # Verificar se é de tribunal
        is_tribunal = any(r in remetente for r in self.REMETENTES_ALTA_PRIORIDADE)
        
        # Verificar palavras-chave financeiras
        tipo_alerta = None
        for palavra in self.PALAVRAS_CHAVE_FINANCEIRO:
            if palavra in texto_completo:
                if "alvará" in palavra:
                    tipo_alerta = AlertType.ALVARA
                elif "mandado" in texto_completo and "pagamento" in texto_completo:
                    tipo_alerta = AlertType.MANDADO_PAGAMENTO
                elif "rpv" in texto_completo:
                    tipo_alerta = AlertType.RPV
                elif "precatório" in texto_completo:
                    tipo_alerta = AlertType.PRECATORIO
                else:
                    tipo_alerta = AlertType.DEPOSITO
                break
        
        # Verificar palavras-chave processuais (se de tribunal)
        if not tipo_alerta and is_tribunal:
            for palavra in self.PALAVRAS_CHAVE_PROCESSUAL:
                if palavra in texto_completo:
                    if "intimação" in palavra or "intimacao" in texto_completo:
                        tipo_alerta = AlertType.INTIMACAO
                    elif "citação" in palavra or "citacao" in texto_completo:
                        tipo_alerta = AlertType.CITACAO
                    break
        
        # Se não encontrou nada relevante
        if not tipo_alerta and not is_tribunal:
            return None
        
        # Se é de tribunal mas sem palavra-chave específica
        if not tipo_alerta:
            tipo_alerta = AlertType.INTIMACAO
        
        # Extrair número do processo
        numero_processo = self._extrair_numero_processo(texto_completo)
        
        # Extrair valor (se houver)
        valor = self._extrair_valor(texto_completo)
        
        return EmailAlert(
            tipo=tipo_alerta,
            remetente=email_data.get('remetente', ''),
            assunto=email_data.get('assunto', '')[:200],
            numero_processo=numero_processo,
            valor_detectado=valor,
            data_recebimento=email_data.get('data', ''),
            corpo_resumo=corpo[:500]
        )
    
    def _extrair_numero_processo(self, texto: str) -> Optional[str]:
        """Extrai número de processo no formato CNJ."""
        # Padrão CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO
        padrao = r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}'
        match = re.search(padrao, texto)
        return match.group(0) if match else None
    
    def _extrair_valor(self, texto: str) -> Optional[float]:
        """Extrai valor monetário do texto."""
        # Padrões comuns: R$ 1.234,56 ou R$1234.56
        padroes = [
            r'R\$\s*([\d.,]+)',
            r'valor[:\s]+R?\$?\s*([\d.,]+)',
        ]
        
        for padrao in padroes:
            match = re.search(padrao, texto, re.IGNORECASE)
            if match:
                try:
                    valor_str = match.group(1)
                    # Normalizar formato
                    valor_str = valor_str.replace('.', '').replace(',', '.')
                    return float(valor_str)
                except ValueError:
                    continue
        return None
    
    def processar_emails(self, emails: List[Dict]) -> List[EmailAlert]:
        """Processa lista de e-mails e retorna alertas."""
        alertas = []
        for email in emails:
            alerta = self.classificar_email(email)
            if alerta:
                alertas.append(alerta)
        return alertas


# ==============================================================================
# CALENDAR CLIENT
# ==============================================================================

class CalendarClient:
    """
    Gerencia eventos do Google Calendar.
    Integra com ai_gemini para criar tarefas automaticamente.
    """
    
    def __init__(self):
        self.service = None
    
    def conectar(self, username: str = "sistema") -> bool:
        """Conecta ao Google Calendar."""
        try:
            creds = TokenManager.get_credentials(username)
            if not creds:
                logger.error("Credenciais não disponíveis para Calendar")
                return False
            
            self.service = build('calendar', 'v3', credentials=creds)
            logger.info("Conectado ao Google Calendar")
            return True
        except Exception as e:
            logger.error(f"Erro ao conectar ao Calendar: {e}")
            return False
    
    def criar_tarefa_ia(
        self,
        titulo: str,
        descricao: str,
        data_prazo: str,
        advogado_responsavel: str,
        processo_id: Optional[int] = None
    ) -> Optional[str]:
        """
        Cria evento a partir de sugestão da IA.
        Returns: google_calendar_id
        """
        if not self.service:
            return None
        
        try:
            # Parsear data
            if isinstance(data_prazo, str):
                try:
                    dt = datetime.strptime(data_prazo, '%Y-%m-%d')
                except ValueError:
                    dt = datetime.strptime(data_prazo, '%d/%m/%Y')
            else:
                dt = data_prazo
            
            # Criar evento
            event = {
                'summary': titulo,
                'description': f"{descricao}\n\nResponsável: {advogado_responsavel}",
                'start': {
                    'date': dt.strftime('%Y-%m-%d'),
                    'timeZone': 'America/Sao_Paulo',
                },
                'end': {
                    'date': dt.strftime('%Y-%m-%d'),
                    'timeZone': 'America/Sao_Paulo',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 1440},  # 1 dia antes
                        {'method': 'popup', 'minutes': 60},    # 1 hora antes
                    ],
                },
            }
            
            # Adicionar referência ao processo
            if processo_id:
                event['description'] += f"\n\nProcesso ID: {processo_id}"
            
            result = self.service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
            
            logger.info(f"Evento criado: {titulo}")
            return result.get('id')
        except Exception as e:
            logger.error(f"Erro ao criar evento: {e}")
            return None
    
    def vincular_processo(self, evento_id: str, processo_id: int) -> bool:
        """Vincula evento existente a um processo."""
        if not self.service:
            return False
        
        try:
            # Obter evento existente
            event = self.service.events().get(
                calendarId='primary',
                eventId=evento_id
            ).execute()
            
            # Atualizar descrição
            desc = event.get('description', '')
            if f"Processo ID: {processo_id}" not in desc:
                event['description'] = f"{desc}\n\nProcesso ID: {processo_id}"
                
                self.service.events().update(
                    calendarId='primary',
                    eventId=evento_id,
                    body=event
                ).execute()
            
            return True
        except Exception as e:
            logger.error(f"Erro ao vincular processo: {e}")
            return False


# ==============================================================================
# WORKSPACE MANAGER (Singleton)
# ==============================================================================

class WorkspaceManager:
    """
    Classe central que orquestra todas as integrações Google Workspace.
    Padrão Singleton para gerenciar conexões e estado.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.drive = DriveClient()
        self.gmail = GmailWatcher()
        self.calendar = CalendarClient()
        self._initialized = True
    
    def conectar_todos(self, username: str = "sistema") -> Dict[str, bool]:
        """Conecta a todos os serviços Google."""
        return {
            "drive": self.drive.conectar(username),
            "gmail": self.gmail.conectar(username),
            "calendar": self.calendar.conectar(username)
        }
    
    def status(self) -> Dict[str, bool]:
        """Retorna status de conexão de cada serviço."""
        return {
            "drive": self.drive.service is not None,
            "gmail": self.gmail.service is not None,
            "calendar": self.calendar.service is not None
        }


# ==============================================================================
# FUNÇÕES HELPER
# ==============================================================================

def get_workspace() -> WorkspaceManager:
    """Retorna instância do WorkspaceManager."""
    return WorkspaceManager()


def criar_pasta_cliente(nome_cliente: str, numero_processo: Optional[str] = None) -> Dict:
    """Helper para criar pasta de cliente no Drive."""
    ws = get_workspace()
    if not ws.drive.service:
        ws.drive.conectar()
    return ws.drive.criar_estrutura_cliente(nome_cliente, numero_processo)


def verificar_emails_novos(max_results: int = 50) -> List[EmailAlert]:
    """Helper para verificar e-mails e retornar alertas."""
    ws = get_workspace()
    if not ws.gmail.service:
        ws.gmail.conectar()
    emails = ws.gmail.buscar_emails_recentes(max_results)
    return ws.gmail.processar_emails(emails)


def criar_evento_ia(
    titulo: str,
    data_prazo: str,
    advogado: str,
    descricao: str = "",
    processo_id: Optional[int] = None
) -> Optional[str]:
    """Helper para criar evento no Calendar."""
    ws = get_workspace()
    if not ws.calendar.service:
        ws.calendar.conectar()
    return ws.calendar.criar_tarefa_ia(titulo, descricao, data_prazo, advogado, processo_id)
