"""
Script para renovar o token do Google Drive.
Execute este script para gerar um novo token.json válido.

Uso: python renovar_token_drive.py
"""

import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Escopos necessários para o Google Drive
SCOPES = ['https://www.googleapis.com/auth/drive']

# Arquivos de credenciais
CLIENT_SECRET_FILE = 'client_secret.json'
TOKEN_FILE = 'token.json'

def renovar_token():
    """Renova o token OAuth para o Google Drive."""
    print("=" * 60)
    print("  RENOVAÇÃO DE TOKEN - GOOGLE DRIVE")
    print("=" * 60)
    print()
    
    creds = None
    
    # Verificar se já existe um token
    if os.path.exists(TOKEN_FILE):
        print(f"[INFO] Encontrado {TOKEN_FILE} existente.")
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            if creds and creds.valid:
                print("[OK] Token ainda válido!")
                return testar_conexao(creds)
            elif creds and creds.expired and creds.refresh_token:
                print("[INFO] Token expirado. Tentando renovar automaticamente...")
                creds.refresh(Request())
                salvar_token(creds)
                print("[OK] Token renovado com sucesso!")
                return testar_conexao(creds)
        except Exception as e:
            print(f"[AVISO] Erro ao ler/renovar token: {e}")
            print("[INFO] Será necessário reautenticar via navegador.")
            creds = None
    
    # Se não há token válido, iniciar fluxo OAuth
    if not creds or not creds.valid:
        print()
        print("[INFO] Iniciando autenticação via navegador...")
        print("-" * 60)
        
        if not os.path.exists(CLIENT_SECRET_FILE):
            print(f"[ERRO] Arquivo {CLIENT_SECRET_FILE} não encontrado!")
            print("       Baixe o arquivo de credenciais do Google Cloud Console.")
            return False
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE, SCOPES
            )
            # Usar porta 0 para selecionar porta disponível automaticamente
            creds = flow.run_local_server(port=0)
            salvar_token(creds)
            print()
            print("[OK] Autenticação concluída com sucesso!")
        except Exception as e:
            print(f"[ERRO] Falha na autenticação: {e}")
            return False
    
    return testar_conexao(creds)

def salvar_token(creds):
    """Salva as credenciais no arquivo token.json."""
    with open(TOKEN_FILE, 'w') as token:
        token.write(creds.to_json())
    print(f"[OK] Token salvo em {TOKEN_FILE}")

def testar_conexao(creds):
    """Testa a conexão com o Google Drive."""
    print()
    print("-" * 60)
    print("[INFO] Testando conexão com Google Drive...")
    
    try:
        service = build('drive', 'v3', credentials=creds)
        
        # Listar os primeiros 5 arquivos para confirmar
        results = service.files().list(
            pageSize=5, fields="files(id, name)"
        ).execute()
        
        items = results.get('files', [])
        
        print()
        print("=" * 60)
        print("  [OK] CONEXÃO ESTABELECIDA COM SUCESSO!")
        print("=" * 60)
        print()
        
        if items:
            print("Arquivos encontrados no Drive:")
            for item in items:
                print(f"  - {item['name']}")
        else:
            print("(Nenhum arquivo encontrado - Drive pode estar vazio)")
        
        print()
        print("[OK] O sistema está pronto para usar o Google Drive!")
        print()
        return True
        
    except Exception as e:
        print(f"[ERRO] Falha ao conectar: {e}")
        return False

if __name__ == "__main__":
    sucesso = renovar_token()
    
    print()
    if sucesso:
        print("=" * 60)
        print("  STATUS FINAL: SUCESSO")
        print("=" * 60)
    else:
        print("=" * 60)
        print("  STATUS FINAL: FALHA")
        print("  Verifique as mensagens de erro acima.")
        print("=" * 60)
