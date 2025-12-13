"""
Script auxiliar para extrair secrets locais e gerar template para Streamlit Cloud
ATENÇÃO: Este script NÃO mostra valores sensíveis no terminal, apenas verifica se existem.
"""
import os
import json
from pathlib import Path

# Diretório base do projeto
BASE_DIR = Path(__file__).parent.parent

def verificar_arquivo(caminho, nome_amigavel):
    """Verifica se um arquivo existe e retorna status"""
    arquivo = BASE_DIR / caminho
    if arquivo.exists():
        tamanho = arquivo.stat().st_size
        print(f"[OK] {nome_amigavel}: ENCONTRADO ({tamanho} bytes)")
        return True
    else:
        print(f"[FALTA] {nome_amigavel}: NAO ENCONTRADO")
        return False

def ler_json_seguro(caminho):
    """Lê arquivo JSON e retorna as chaves (sem valores)"""
    arquivo = BASE_DIR / caminho
    try:
        with open(arquivo, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return list(data.keys())
    except Exception as e:
        print(f"  [AVISO] Erro ao ler: {e}")
        return []

def gerar_template_toml():
    """Gera template TOML com instruções"""
    print("\n" + "="*60)
    print("TEMPLATE PARA STREAMLIT CLOUD SECRETS")
    print("="*60)
    
    template = """
# Cole este conteúdo em: Settings > Secrets no Streamlit Cloud
# SUBSTITUA os valores entre <> pelos seus valores reais

# 1. DATABASE_URL do Supabase
DATABASE_URL = "<cole_aqui_a_url_do_supabase>"
# Exemplo: postgresql://postgres.xxxxx:senha@aws-0-sa-east-1.pooler.supabase.com:6543/postgres

# 2. CRYPTO_KEY (chave de criptografia LGPD)
CRYPTO_KEY = "<cole_aqui_a_crypto_key>"
# IMPORTANTE: Use a MESMA chave que está em .streamlit/secrets.toml local!

# 3. GEMINI_API_KEY (Google AI)
GEMINI_API_KEY = "<cole_aqui_a_gemini_api_key>"
# Exemplo: AIzaSy...

# 4. Google Service Account (copie do client_secret.json)
[gcp_service_account]
type = "service_account"
project_id = "<seu_project_id>"
private_key_id = "<sua_private_key_id>"
private_key = "-----BEGIN PRIVATE KEY-----\\n<sua_chave_privada>\\n-----END PRIVATE KEY-----\\n"
client_email = "<service_account_email@project.iam.gserviceaccount.com>"
client_id = "<seu_client_id>"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "<sua_cert_url>"
universe_domain = "googleapis.com"
"""
    
    print(template)
    
    # Salvar template em arquivo
    output_file = BASE_DIR / "SECRETS_TEMPLATE_STREAMLIT.toml"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(template)
    
    print("\n" + "="*60)
    print(f"[SUCESSO] Template salvo em: {output_file}")
    print("="*60)

def main():
    print("\n[VERIFICACAO] Secrets Locais")
    print("="*60)
    
    secrets_encontrados = []
    
    # 1. Verificar DATABASE_URL
    print("\n[1] DATABASE_URL (Supabase)")
    if verificar_arquivo(".streamlit/secrets.toml", "secrets.toml"):
        secrets_encontrados.append("DATABASE_URL (em secrets.toml)")
    
    # 2. Verificar CRYPTO_KEY
    print("\n[2] CRYPTO_KEY (Criptografia)")
    if verificar_arquivo(".crypto_key", ".crypto_key"):
        secrets_encontrados.append("CRYPTO_KEY")
    elif verificar_arquivo(".streamlit/secrets.toml", "secrets.toml (pode conter CRYPTO_KEY)"):
        print("  [INFO] CRYPTO_KEY pode estar em secrets.toml")
    
    # 3. Verificar GEMINI_API_KEY
    print("\n[3] GEMINI_API_KEY (Google AI)")
    if verificar_arquivo(".env", ".env"):
        secrets_encontrados.append("GEMINI_API_KEY (possivelmente em .env)")
    print("  [INFO] Pode estar em .streamlit/secrets.toml")
    
    # 4. Verificar Google Service Account
    print("\n[4] Google Service Account")
    if verificar_arquivo("client_secret.json", "client_secret.json"):
        chaves = ler_json_seguro("client_secret.json")
        print(f"  [CAMPOS] Encontrados: {', '.join(chaves[:3])}...")
        secrets_encontrados.append("gcp_service_account")
    
    if verificar_arquivo("service_account.json.bak", "service_account.json.bak"):
        print("  [INFO] Backup encontrado")
    
    # Resumo
    print("\n" + "="*60)
    print("[RESUMO]")
    print("="*60)
    print(f"Secrets encontrados: {len(secrets_encontrados)}/4")
    for secret in secrets_encontrados:
        print(f"  [OK] {secret}")
    
    # Gerar template
    gerar_template_toml()
    
    print("\n[PROXIMOS PASSOS]:")
    print("1. Abra o arquivo 'SECRETS_TEMPLATE_STREAMLIT.toml' gerado")
    print("2. Abra '.streamlit/secrets.toml' no seu editor")
    print("3. Copie os valores de secrets.toml para o template")
    print("4. Cole o template completo no Streamlit Cloud (Settings > Secrets)")

if __name__ == "__main__":
    main()
