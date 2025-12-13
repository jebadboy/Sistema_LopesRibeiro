#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de verificacao das APIs Google Calendar e Google Drive.
Verifica conectividade, validade dos tokens e funcionamento basico.
"""

import os
import sys
import pickle
from datetime import datetime, timedelta

# Forcar UTF-8 no Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def verificar_arquivos_credenciais():
    """Verifica existencia dos arquivos de credenciais."""
    print("\n" + "="*60)
    print("[ARQUIVOS] VERIFICACAO DE ARQUIVOS DE CREDENCIAIS")
    print("="*60)
    
    arquivos = {
        'credentials.json': 'OAuth 2.0 Client ID (para login interativo)',
        'service_account.json': 'Service Account (para automacao)',
        'token.json': 'Token OAuth do Drive',
        'token_Administrador.pickle': 'Token OAuth do Calendar (usuario Administrador)',
        'token_sistema.pickle': 'Token OAuth do Calendar (sistema)',
    }
    
    status_geral = True
    for arquivo, descricao in arquivos.items():
        existe = os.path.exists(arquivo)
        status = "[OK]" if existe else "[X]"
        tamanho = ""
        modificado = ""
        
        if existe:
            stat = os.stat(arquivo)
            tamanho = f"({stat.st_size} bytes)"
            mod_time = datetime.fromtimestamp(stat.st_mtime)
            modificado = f"- Modificado: {mod_time.strftime('%d/%m/%Y %H:%M')}"
        else:
            status_geral = False
            
        print(f"{status} {arquivo} {tamanho} {modificado}")
        print(f"     -> {descricao}")
    
    return status_geral


def verificar_google_drive():
    """Testa a conexao com Google Drive API."""
    print("\n" + "="*60)
    print("[DRIVE] VERIFICACAO DO GOOGLE DRIVE")
    print("="*60)
    
    try:
        import google_drive
        
        # 1. Autenticacao
        print("\n1. Testando autenticacao...")
        service = google_drive.autenticar()
        
        if not service:
            print("   [FALHA] Nao foi possivel autenticar")
            return False, "Falha na autenticacao"
        
        print("   [OK] Autenticacao OK")
        
        # 2. Verificar acesso a pasta alvo
        print(f"\n2. Verificando acesso a pasta alvo...")
        pasta_id = google_drive.PASTA_ALVO_ID
        print(f"   ID da pasta: {pasta_id}")
        
        try:
            results = service.files().list(
                q=f"'{pasta_id}' in parents and trashed=false",
                fields="files(id, name)",
                pageSize=5
            ).execute()
            files = results.get('files', [])
            print(f"   [OK] Acesso OK - {len(files)} arquivo(s) encontrado(s)")
            for f in files[:3]:
                print(f"      * {f['name']}")
            if len(files) > 3:
                print(f"      ... e mais {len(files)-3} arquivo(s)")
        except Exception as e:
            print(f"   [ERRO] Erro ao acessar pasta: {e}")
            return False, f"Erro de acesso: {e}"
        
        # 3. Verificar informacoes da conta
        print(f"\n3. Verificando informacoes do Drive...")
        try:
            about = service.about().get(fields="user, storageQuota").execute()
            user = about.get('user', {})
            quota = about.get('storageQuota', {})
            
            print(f"   Conta: {user.get('emailAddress', 'N/A')}")
            
            if quota:
                usado = int(quota.get('usage', 0)) / (1024**3)
                limite = int(quota.get('limit', 0)) / (1024**3) if quota.get('limit') else "Ilimitado"
                if isinstance(limite, float):
                    print(f"   Armazenamento: {usado:.2f} GB / {limite:.2f} GB")
                else:
                    print(f"   Armazenamento: {usado:.2f} GB / {limite}")
        except Exception as e:
            print(f"   [AVISO] Nao foi possivel obter info da conta: {e}")
        
        return True, "Funcionando corretamente"
        
    except ImportError as e:
        print(f"   [ERRO] Erro de importacao: {e}")
        return False, f"Modulo nao encontrado: {e}"
    except Exception as e:
        print(f"   [ERRO] Erro inesperado: {e}")
        return False, f"Erro: {e}"


def verificar_google_calendar():
    """Testa a conexao com Google Calendar API."""
    print("\n" + "="*60)
    print("[CALENDAR] VERIFICACAO DO GOOGLE CALENDAR")
    print("="*60)
    
    try:
        import google_calendar
        
        # 1. Verificar autenticacao para usuario "Administrador"
        username = "Administrador"
        print(f"\n1. Verificando autenticacao para '{username}'...")
        
        autenticado = google_calendar.verificar_autenticacao(username)
        if autenticado:
            print(f"   [OK] Token encontrado para {username}")
        else:
            print(f"   [AVISO] Nenhum token encontrado para {username}")
        
        # 2. Tentar autenticar e conectar
        print(f"\n2. Testando conexao com a API...")
        service = google_calendar.autenticar_google(username)
        
        if not service:
            print("   [FALHA] Nao foi possivel conectar")
            return False, "Falha na conexao"
        
        print("   [OK] Conexao estabelecida")
        
        # 3. Listar calendarios disponiveis
        print(f"\n3. Listando calendarios...")
        try:
            calendar_list = service.calendarList().list().execute()
            calendars = calendar_list.get('items', [])
            print(f"   [OK] Encontrados {len(calendars)} calendario(s):")
            for cal in calendars[:5]:
                primary = "[PRINCIPAL]" if cal.get('primary') else ""
                print(f"      * {cal.get('summary', 'Sem nome')} {primary}")
            if len(calendars) > 5:
                print(f"      ... e mais {len(calendars)-5} calendario(s)")
        except Exception as e:
            print(f"   [AVISO] Erro ao listar calendarios: {e}")
        
        # 4. Buscar proximos eventos
        print(f"\n4. Buscando proximos eventos...")
        try:
            now = datetime.utcnow().isoformat() + 'Z'
            events_result = service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=5,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            
            if not events:
                print("   [INFO] Nenhum evento futuro encontrado")
            else:
                print(f"   [OK] Proximos {len(events)} evento(s):")
                for event in events:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    summary = event.get('summary', 'Sem titulo')
                    print(f"      * {start[:10]} - {summary[:40]}")
        except Exception as e:
            print(f"   [AVISO] Erro ao buscar eventos: {e}")
        
        return True, "Funcionando corretamente"
        
    except ImportError as e:
        print(f"   [ERRO] Erro de importacao: {e}")
        return False, f"Modulo nao encontrado: {e}"
    except Exception as e:
        print(f"   [ERRO] Erro inesperado: {e}")
        return False, f"Erro: {e}"


def verificar_validade_tokens():
    """Verifica a validade dos tokens OAuth."""
    print("\n" + "="*60)
    print("[TOKENS] VERIFICACAO DE VALIDADE DOS TOKENS")
    print("="*60)
    
    tokens_status = {}
    
    # Token JSON (Drive)
    if os.path.exists('token.json'):
        try:
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file('token.json')
            
            expired = creds.expired if hasattr(creds, 'expired') else None
            expiry = creds.expiry if hasattr(creds, 'expiry') else None
            has_refresh = bool(creds.refresh_token) if hasattr(creds, 'refresh_token') else False
            
            print(f"\n[DRIVE] token.json:")
            print(f"   * Expirado: {'Sim [!]' if expired else 'Nao [OK]'}")
            if expiry:
                print(f"   * Expira em: {expiry}")
            print(f"   * Refresh Token: {'Sim [OK]' if has_refresh else 'Nao [X]'}")
            
            if expired and has_refresh:
                print(f"   [INFO] Token expirado mas pode ser renovado automaticamente")
                tokens_status['token.json'] = 'renovavel'
            elif expired and not has_refresh:
                print(f"   [!!!] ATENCAO: Token expirado e SEM refresh token!")
                print(f"   --> NECESSARIO: Reautenticar manualmente")
                tokens_status['token.json'] = 'precisa_reautenticar'
            else:
                tokens_status['token.json'] = 'ok'
                
        except Exception as e:
            print(f"\n[DRIVE] token.json: [ERRO] Erro ao analisar: {e}")
            tokens_status['token.json'] = 'erro'
    
    # Token Pickle (Calendar)
    pickle_files = ['token_Administrador.pickle', 'token_sistema.pickle']
    for pickle_file in pickle_files:
        if os.path.exists(pickle_file):
            try:
                with open(pickle_file, 'rb') as f:
                    creds = pickle.load(f)
                
                expired = creds.expired if hasattr(creds, 'expired') else None
                expiry = creds.expiry if hasattr(creds, 'expiry') else None
                has_refresh = bool(creds.refresh_token) if hasattr(creds, 'refresh_token') else False
                
                print(f"\n[CALENDAR] {pickle_file}:")
                print(f"   * Expirado: {'Sim [!]' if expired else 'Nao [OK]'}")
                if expiry:
                    print(f"   * Expira em: {expiry}")
                print(f"   * Refresh Token: {'Sim [OK]' if has_refresh else 'Nao [X]'}")
                
                if expired and has_refresh:
                    print(f"   [INFO] Token expirado mas pode ser renovado automaticamente")
                    tokens_status[pickle_file] = 'renovavel'
                elif expired and not has_refresh:
                    print(f"   [!!!] ATENCAO: Token expirado e SEM refresh token!")
                    print(f"   --> NECESSARIO: Reautenticar manualmente")
                    tokens_status[pickle_file] = 'precisa_reautenticar'
                else:
                    tokens_status[pickle_file] = 'ok'
                    
            except Exception as e:
                print(f"\n[CALENDAR] {pickle_file}: [ERRO] Erro ao analisar: {e}")
                tokens_status[pickle_file] = 'erro'
    
    return tokens_status


def main():
    """Executa todas as verificacoes."""
    print("\n" + "="*60)
    print("DIAGNOSTICO DAS APIS GOOGLE - Sistema Lopes & Ribeiro")
    print(f"Executado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("="*60)
    
    # Mudar para o diretorio do projeto
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"\nDiretorio: {os.getcwd()}")
    
    # Executar verificacoes
    verificar_arquivos_credenciais()
    tokens_status = verificar_validade_tokens()
    
    drive_ok, drive_msg = verificar_google_drive()
    calendar_ok, calendar_msg = verificar_google_calendar()
    
    # Resumo Final
    print("\n" + "="*60)
    print("RESUMO FINAL")
    print("="*60)
    
    print(f"\n{'API':<25} {'STATUS':<15} {'DETALHES'}")
    print("-"*60)
    print(f"{'Google Drive':<25} {'[OK]' if drive_ok else '[FALHA]':<15} {drive_msg}")
    print(f"{'Google Calendar':<25} {'[OK]' if calendar_ok else '[FALHA]':<15} {calendar_msg}")
    
    # Verificar se precisa reautenticar
    precisa_reauth = [k for k, v in tokens_status.items() if v == 'precisa_reautenticar']
    if precisa_reauth:
        print("\n" + "="*60)
        print("[!!!] ACAO NECESSARIA: REAUTENTICACAO")
        print("="*60)
        print("\nOs seguintes tokens precisam ser renovados manualmente:")
        for token in precisa_reauth:
            print(f"   * {token}")
        print("\nPara reautenticar:")
        print("   1. Delete o arquivo de token problematico")
        print("   2. Execute o sistema localmente")
        print("   3. O fluxo de login OAuth sera iniciado automaticamente")
    
    print("\n" + "="*60)
    print("Verificacao concluida!")
    print("="*60 + "\n")
    
    return drive_ok and calendar_ok


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
