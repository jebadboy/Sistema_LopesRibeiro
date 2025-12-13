"""
Módulo de gerenciamento de secrets usando Google Secret Manager.
Substitui leitura de .env e arquivos locais (.crypto_key).

Este módulo prioriza segurança seguindo as boas práticas:
- Secrets nunca armazenados em código
- Fallback para variáveis de ambiente em dev local
- Logging seguro (não expõe valores)
- Cache em memória para reduzir chamadas à API

Uso:
    from secrets_manager import get_crypto_key, get_gemini_api_key
    
    crypto_key = get_crypto_key()
    api_key = get_gemini_api_key()
"""

from google.cloud import secretmanager
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Configuração
PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'sistema-lopes-ribeiro')
ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')  # 'development' ou 'production'

class SecretsManager:
    """
    Gerenciador de secrets com suporte a Google Secret Manager.
    
    Features:
    - Cache em memória (evita chamadas repetidas)
    - Fallback para variáveis de ambiente em dev
    - Logging seguro (não expõe valores)
    """
    
    def __init__(self):
        self.client = None
        self.project_path = f"projects/{PROJECT_ID}"
        self._cache = {}  # Cache em memória
        
        # Inicializar client apenas em produção
        if ENVIRONMENT == 'production':
            try:
                self.client = secretmanager.SecretManagerServiceClient()
                logger.info("Secret Manager inicializado (produção)")
            except Exception as e:
                logger.error(f"Erro ao inicializar Secret Manager: {e}")
                logger.warning("Usando fallback para variáveis de ambiente")
        else:
            logger.info("Ambiente dev: usando variáveis de ambiente")
    
    def get_secret(self, secret_id: str, version: str = "latest") -> str:
        """
        Recupera secret do Google Secret Manager ou variável de ambiente.
        
        Args:
            secret_id: ID do secret (ex: 'crypto-key', 'gemini-api-key')
            version: Versão do secret (default: 'latest')
        
        Returns:
            Valor do secret em string
            
        Raises:
            SecretNotFoundError: Se secret não encontrado
        """
        # Verificar cache primeiro
        cache_key = f"{secret_id}:{version}"
        if cache_key in self._cache:
            logger.debug(f"Secret {secret_id} obtido do cache")
            return self._cache[cache_key]
        
        # Tentar Secret Manager (apenas em produção)
        if ENVIRONMENT == 'production' and self.client:
            try:
                name = f"{self.project_path}/secrets/{secret_id}/versions/{version}"
                response = self.client.access_secret_version(request={"name": name})
                value = response.payload.data.decode('UTF-8')
                
                # Cachear
                self._cache[cache_key] = value
                logger.info(f"Secret {secret_id} obtido do Secret Manager")
                return value
            except Exception as e:
                logger.error(f"Erro ao acessar secret {secret_id} no Secret Manager: {e}")
                # Continuar para fallback
        
        # Fallback: variável de ambiente
        env_var = secret_id.upper().replace('-', '_')
        value = os.getenv(env_var)
        
        if value:
            logger.info(f"Secret {secret_id} obtido de variável de ambiente {env_var}")
            self._cache[cache_key] = value
            return value
        
        # Não encontrado
        raise SecretNotFoundError(
            f"Secret '{secret_id}' não encontrado no Secret Manager nem em variável de ambiente {env_var}"
        )
    
    def create_secret(self, secret_id: str, value: str) -> bool:
        """
        Cria novo secret ou adiciona versão (apenas em produção).
        
        Args:
            secret_id: ID do secret
            value: Valor a armazenar
            
        Returns:
            True se criado com sucesso
        """
        if ENVIRONMENT != 'production' or not self.client:
            logger.warning("create_secret só funciona em produção com Secret Manager")
            return False
        
        try:
            # Tentar criar o secret
            parent = self.project_path
            secret = {'replication': {'automatic': {}}}
            
            try:
                self.client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": secret_id,
                        "secret": secret
                    }
                )
                logger.info(f"Secret {secret_id} criado")
            except Exception as e:
                logger.debug(f"Secret {secret_id} já existe (ou erro ao criar): {e}")
            
            # Adicionar versão
            parent = f"{self.project_path}/secrets/{secret_id}"
            payload = value.encode('UTF-8')
            
            self.client.add_secret_version(
                request={
                    "parent": parent,
                    "payload": {"data": payload}
                }
            )
            
            logger.info(f"Nova versão do secret {secret_id} criada")
            
            # Limpar cache
            self._invalidate_cache(secret_id)
            
            return True
        except Exception as e:
            logger.error(f"Erro ao criar secret {secret_id}: {e}")
            return False
    
    def _invalidate_cache(self, secret_id: str):
        """Remove secret do cache."""
        keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{secret_id}:")]
        for key in keys_to_remove:
            del self._cache[key]
        logger.debug(f"Cache invalidado para {secret_id}")

class SecretNotFoundError(Exception):
    """Exceção quando secret não é encontrado."""
    pass

# ========== INSTÂNCIA GLOBAL (SINGLETON) ==========

_secrets_manager: Optional[SecretsManager] = None

def get_secrets_manager() -> SecretsManager:
    """Retorna instância singleton do SecretsManager."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager

# ========== FUNÇÕES DE CONVENIÊNCIA ==========

def get_crypto_key() -> str:
    """
    Retorna chave de criptografia para módulo crypto.py.
    
    Busca em:
    1. Google Secret Manager (produção)
    2. Variável de ambiente CRYPTO_KEY
    3. Arquivo .crypto_key (fallback dev)
    
    Returns:
        Chave de criptografia como string
    """
    try:
        return get_secrets_manager().get_secret('crypto-key')
    except SecretNotFoundError:
        # Fallback adicional: ler arquivo .crypto_key (dev apenas)
        if ENVIRONMENT == 'development':
            try:
                from pathlib import Path
                key_file = Path(__file__).parent / '.crypto_key'
                if key_file.exists():
                    logger.warning("Usando .crypto_key (INSEGURO - apenas dev)")
                    return key_file.read_text().strip()
            except Exception as e:
                logger.error(f"Erro ao ler .crypto_key: {e}")
        
        raise SecretNotFoundError(
            "Chave de criptografia não encontrada. "
            "Configure a variável CRYPTO_KEY ou crie o secret 'crypto-key' no Secret Manager"
        )

def get_gemini_api_key() -> str:
    """
    Retorna API key do Google Gemini.
    
    Returns:
        API key como string
    """
    try:
        return get_secrets_manager().get_secret('gemini-api-key')
    except SecretNotFoundError:
        raise SecretNotFoundError(
            "Gemini API key não encontrada. "
            "Configure a variável GEMINI_API_KEY ou crie o secret 'gemini-api-key' no Secret Manager"
        )

def get_datajud_token() -> str:
    """
    Retorna token de API do DataJud (CNJ).
    
    Returns:
        Token como string
    """
    try:
        return get_secrets_manager().get_secret('datajud-token')
    except SecretNotFoundError:
        raise SecretNotFoundError(
            "DataJud token não encontrado. "
            "Configure a variável DATAJUD_TOKEN ou crie o secret 'datajud-token' no Secret Manager"
        )

def is_secrets_manager_available() -> bool:
    """Verifica se Secret Manager está disponível e configurado."""
    try:
        sm = get_secrets_manager()
        return sm.client is not None
    except Exception:
        return False

# ========== UTILITÁRIO PARA MIGRAÇÃO ==========

def migrate_env_to_secrets():
    """
    Migra secrets de variáveis de ambiente para Secret Manager.
    Executar uma vez em produção após deploy.
    
    Uso:
        python -c "import secrets_manager; secrets_manager.migrate_env_to_secrets()"
    """
    if ENVIRONMENT != 'production':
        logger.error("migrate_env_to_secrets só deve ser executado em produção")
        return
    
    sm = get_secrets_manager()
    
    secrets_to_migrate = {
        'crypto-key': os.getenv('CRYPTO_KEY'),
        'gemini-api-key': os.getenv('GEMINI_API_KEY'),
        'datajud-token': os.getenv('DATAJUD_TOKEN')
    }
    
    for secret_id, value in secrets_to_migrate.items():
        if value:
            logger.info(f"Migrando {secret_id}...")
            success = sm.create_secret(secret_id, value)
            if success:
                logger.info(f"✅ {secret_id} migrado")
            else:
                logger.error(f"❌ Erro ao migrar {secret_id}")
        else:
            logger.warning(f"⚠️ {secret_id} não encontrado em variáveis de ambiente")
    
    logger.info("Migração concluída!")
