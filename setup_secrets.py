import os
import base64
import logging

# Configuração de Log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_credentials():
    """
    Recupera as credenciais do Google da variável de ambiente e salva em arquivo.
    Isso permite que o arquivo credentials.json não precise ser comitado no Git.
    """
    logger.info("Iniciando configuração de segredos...")
    
    # 1. Google Credentials (credentials.json)
    google_creds_b64 = os.getenv('GOOGLE_CREDENTIALS_BASE64')
    
    if google_creds_b64:
        try:
            # Decodificar Base64
            creds_json = base64.b64decode(google_creds_b64).decode('utf-8')
            
            # Salvar no arquivo
            with open('credentials.json', 'w') as f:
                f.write(creds_json)
            
            logger.info("✅ Arquivo credentials.json criado com sucesso via variável de ambiente.")
        except Exception as e:
            logger.error(f"❌ Erro ao decodificar GOOGLE_CREDENTIALS_BASE64: {e}")
    else:
        logger.warning("⚠️ Variável GOOGLE_CREDENTIALS_BASE64 não encontrada. O arquivo credentials.json deve existir localmente.")

    # 2. Criar diretório de dados se não existir (para persistência)
    data_dir = os.getenv('DATA_DIR')
    if data_dir and not os.path.exists(data_dir):
        try:
            os.makedirs(data_dir)
            logger.info(f"✅ Diretório de dados criado: {data_dir}")
        except Exception as e:
            logger.error(f"❌ Erro ao criar diretório de dados: {e}")

if __name__ == "__main__":
    setup_credentials()
