"""
GERADOR DE SECRETS FINAL PARA STREAMLIT CLOUD
Este script le os secrets locais e gera um arquivo pronto para copiar/colar
"""
import os
import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

def ler_arquivo_seguro(caminho):
    """Le arquivo e retorna conteudo"""
    arquivo = BASE_DIR / caminho
    if arquivo.exists():
        with open(arquivo, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return None

def ler_json(caminho):
    """Le arquivo JSON"""
    arquivo = BASE_DIR / caminho
    if arquivo.exists():
        with open(arquivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def gerar_secrets_final():
    """Gera arquivo final de secrets"""
    
    print("\n" + "="*60)
    print("GERANDO SECRETS PARA STREAMLIT CLOUD")
    print("="*60 + "\n")
    
    secrets_content = []
    
    # 1. DATABASE_URL - tentar ler de secrets.toml local
    print("[1] Processando DATABASE_URL...")
    secrets_toml = ler_arquivo_seguro(".streamlit/secrets.toml")
    if secrets_toml:
        # Extrair DATABASE_URL
        for line in secrets_toml.split('\n'):
            if line.strip().startswith('DATABASE_URL'):
                database_url = line.split('=', 1)[1].strip().strip('"\'')
                secrets_content.append("# 1. DATABASE_URL do Supabase")
                secrets_content.append(f'DATABASE_URL = "{database_url}"')
                secrets_content.append("")
                print(f"   [OK] DATABASE_URL encontrado ({len(database_url)} caracteres)")
                break
    
    # 2. CRYPTO_KEY
    print("[2] Processando CRYPTO_KEY...")
    crypto_key = ler_arquivo_seguro(".crypto_key")
    if crypto_key:
        secrets_content.append("# 2. CRYPTO_KEY (criptografia LGPD)")
        secrets_content.append(f'CRYPTO_KEY = "{crypto_key}"')
        secrets_content.append("")
        print(f"   [OK] CRYPTO_KEY encontrada ({len(crypto_key)} caracteres)")
    
    # 3. GEMINI_API_KEY - tentar de .env ou secrets.toml
    print("[3] Processando GEMINI_API_KEY...")
    gemini_key = None
    
    # Tentar .env primeiro
    env_content = ler_arquivo_seguro(".env")
    if env_content:
        for line in env_content.split('\n'):
            if 'GEMINI_API_KEY' in line:
                gemini_key = line.split('=', 1)[1].strip().strip('"\'')
                break
    
    # Se nao achou em .env, tentar secrets.toml
    if not gemini_key and secrets_toml:
        for line in secrets_toml.split('\n'):
            if line.strip().startswith('GEMINI_API_KEY'):
                gemini_key = line.split('=', 1)[1].strip().strip('"\'')
                break
    
    if gemini_key:
        secrets_content.append("# 3. GEMINI_API_KEY (Google AI)")
        secrets_content.append(f'GEMINI_API_KEY = "{gemini_key}"')
        secrets_content.append("")
        print(f"   [OK] GEMINI_API_KEY encontrada ({len(gemini_key)} caracteres)")
    else:
        secrets_content.append("# 3. GEMINI_API_KEY (Google AI)")
        secrets_content.append('GEMINI_API_KEY = "<COLE_AQUI_SUA_CHAVE>"')
        secrets_content.append("")
        print("   [AVISO] GEMINI_API_KEY nao encontrada - preencher manualmente")
    
    # 4. Google Service Account
    print("[4] Processando gcp_service_account...")
    service_account = ler_json("client_secret.json")
    if not service_account:
        service_account = ler_json("service_account.json.bak")
    
    if service_account:
        secrets_content.append("# 4. Google Service Account (Drive, Calendar, Gmail)")
        secrets_content.append("[gcp_service_account]")
        secrets_content.append(f'type = "{service_account.get("type", "service_account")}"')
        secrets_content.append(f'project_id = "{service_account.get("project_id", "")}"')
        secrets_content.append(f'private_key_id = "{service_account.get("private_key_id", "")}"')
        
        # Private key precisa manter quebras de linha
        private_key = service_account.get("private_key", "")
        # Escapar quebras de linha para TOML
        private_key_escaped = private_key.replace('\n', '\\n')
        secrets_content.append(f'private_key = "{private_key_escaped}"')
        
        secrets_content.append(f'client_email = "{service_account.get("client_email", "")}"')
        secrets_content.append(f'client_id = "{service_account.get("client_id", "")}"')
        secrets_content.append(f'auth_uri = "{service_account.get("auth_uri", "")}"')
        secrets_content.append(f'token_uri = "{service_account.get("token_uri", "")}"')
        secrets_content.append(f'auth_provider_x509_cert_url = "{service_account.get("auth_provider_x509_cert_url", "")}"')
        secrets_content.append(f'client_x509_cert_url = "{service_account.get("client_x509_cert_url", "")}"')
        secrets_content.append(f'universe_domain = "{service_account.get("universe_domain", "googleapis.com")}"')
        
        print(f"   [OK] gcp_service_account processado")
        print(f"   [INFO] Project: {service_account.get('project_id', 'N/A')}")
        print(f"   [INFO] Email: {service_account.get('client_email', 'N/A')[:50]}...")
    
    # Salvar arquivo final
    output_file = BASE_DIR / "SECRETS_STREAMLIT_CLOUD.toml"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(secrets_content))
    
    print("\n" + "="*60)
    print("[SUCESSO] Secrets gerados com sucesso!")
    print("="*60)
    print(f"\nArquivo criado: {output_file}")
    print(f"Tamanho: {len('\n'.join(secrets_content))} caracteres")
    print("\n[PROXIMOS PASSOS]")
    print("1. Abra o arquivo: SECRETS_STREAMLIT_CLOUD.toml")
    print("2. Copie TODO o conteudo (Ctrl+A, Ctrl+C)")
    print("3. Acesse: https://share.streamlit.io")
    print("4. Crie novo app ou acesse app existente")
    print("5. Va em: Settings > Secrets")
    print("6. Cole o conteudo copiado")
    print("7. Clique em 'Save'")
    print("\n[ATENCAO]")
    print("- NAO commite este arquivo no Git!")
    print("- Mantenha em local seguro como backup")
    print("="*60 + "\n")

if __name__ == "__main__":
    gerar_secrets_final()
