"""
Módulo de Criptografia para Dados Sensíveis (LGPD)

Este módulo fornece funções para criptografar e descriptografar
dados sensíveis como CPF/CNPJ usando Fernet (AES-128-CBC).

A chave é armazenada em variável de ambiente CRYPTO_KEY ou
em arquivo .crypto_key na raiz do projeto.
"""

import os
import base64
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Tentar importar cryptography, se não disponível, usar modo fallback
try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("Biblioteca 'cryptography' não instalada. Criptografia desabilitada.")

# Caminho do arquivo de chave
KEY_FILE = Path(__file__).parent / ".crypto_key"
KEY_ENV_VAR = "CRYPTO_KEY"

_fernet_instance = None


def _get_or_create_key() -> bytes:
    """
    Obtém chave de criptografia do Secret Manager (produção) ou 
    variável de ambiente/arquivo (desenvolvimento).
    
    Ordem de busca:
    1. Secret Manager (se em produção)
    2. Variável de ambiente CRYPTO_KEY
    3. Arquivo .crypto_key (fallback dev)
    4. Gera nova chave (apenas dev)
    """
    if not CRYPTO_AVAILABLE:
        return None
    
    # Tentar buscar do Secret Manager primeiro
    try:
        import secrets_manager
        key_str = secrets_manager.get_crypto_key()
        
        # Key pode vir como base64 ou texto plano
        try:
            # Tentar decodificar como base64
            return base64.urlsafe_b64decode(key_str)
        except Exception:
            # Se falhar, usar como está
            return key_str.encode('utf-8')
    except Exception as e:
        logger.debug(f"Secret Manager não disponível ou chave não encontrada: {e}")
        # Continuar para fallbacks
    
    # Fallback 1: Variável de ambiente (dev local)
    key_from_env = os.environ.get(KEY_ENV_VAR)
    if key_from_env:
        try:
            return base64.urlsafe_b64decode(key_from_env)
        except Exception:
            return key_from_env.encode()
    
    # Fallback 2: Arquivo .crypto_key (dev local)
    if KEY_FILE.exists():
        try:
            with open(KEY_FILE, 'rb') as f:
                key_data = f.read().strip()
                logger.info(f"Chave carregada de {KEY_FILE} (dev local)")
                return key_data
        except Exception as e:
            logger.error(f"Erro ao ler chave do arquivo: {e}")
    
    # Fallback 3: Gerar nova chave (APENAS DEV)
    environment = os.getenv('ENVIRONMENT', 'development')
    if environment == 'development':
        logger.warning("⚠️ Gerando nova chave de criptografia (APENAS DEV)")
        new_key = Fernet.generate_key()
        
        try:
            # Salvar para reutilização
            with open(KEY_FILE, 'wb') as f:
                f.write(new_key)
            logger.info(f"Nova chave salva em {KEY_FILE}")
            
            # Adicionar ao .gitignore
            gitignore = Path(__file__).parent / ".gitignore"
            if gitignore.exists():
                content = gitignore.read_text()
                if ".crypto_key" not in content:
                    with open(gitignore, 'a') as f:
                        f.write("\n# Chave de criptografia LGPD\n.crypto_key\n")
            
            return new_key
        except Exception as e:
            logger.error(f"Erro ao salvar chave: {e}")
            return new_key
    else:
        # Em produção, NÃO gerar chave automaticamente
        raise Exception(
            "❌ Chave de criptografia não encontrada em produção! "
            "Configure o secret 'crypto-key' no Google Secret Manager ou "
            "defina a variável CRYPTO_KEY"
        )



def _get_fernet():
    """Retorna instância Fernet singleton"""
    global _fernet_instance
    
    if not CRYPTO_AVAILABLE:
        return None
    
    if _fernet_instance is None:
        key = _get_or_create_key()
        if key:
            try:
                _fernet_instance = Fernet(key)
            except Exception as e:
                logger.error(f"Erro ao inicializar Fernet: {e}")
                return None
    
    return _fernet_instance


def encrypt(plain_text: str) -> str:
    """
    Criptografa um texto.
    
    Args:
        plain_text: Texto a ser criptografado
        
    Returns:
        Texto criptografado em base64 ou texto original se criptografia indisponível
    """
    if not plain_text:
        return plain_text
    
    # Se texto já está criptografado (começa com prefixo), retornar
    if isinstance(plain_text, str) and plain_text.startswith("ENC:"):
        return plain_text
    
    fernet = _get_fernet()
    if not fernet:
        logger.debug("Criptografia indisponível, retornando texto original")
        return plain_text
    
    try:
        encrypted = fernet.encrypt(plain_text.encode('utf-8'))
        return f"ENC:{encrypted.decode('utf-8')}"
    except Exception as e:
        logger.error(f"Erro ao criptografar: {e}")
        return plain_text


def decrypt(cipher_text: str) -> str:
    """
    Descriptografa um texto.
    
    Args:
        cipher_text: Texto criptografado (com prefixo ENC:)
        
    Returns:
        Texto descriptografado ou texto original se não criptografado
    """
    if not cipher_text:
        return cipher_text
    
    # Se não começa com ENC:, não está criptografado
    if not isinstance(cipher_text, str) or not cipher_text.startswith("ENC:"):
        return cipher_text
    
    fernet = _get_fernet()
    if not fernet:
        logger.warning("Criptografia indisponível, não é possível descriptografar")
        return cipher_text  # Retorna criptografado mesmo
    
    try:
        encrypted_part = cipher_text[4:]  # Remove "ENC:"
        decrypted = fernet.decrypt(encrypted_part.encode('utf-8'))
        return decrypted.decode('utf-8')
    except Exception as e:
        logger.error(f"Erro ao descriptografar: {e}")
        return cipher_text


def is_encrypted(text: str) -> bool:
    """Verifica se um texto está criptografado"""
    return isinstance(text, str) and text.startswith("ENC:")


def mask_document(doc: str, show_chars: int = 3) -> str:
    """
    Mascara um documento (CPF/CNPJ) para exibição segura.
    
    Args:
        doc: Documento a mascarar
        show_chars: Quantos caracteres mostrar no início e fim
        
    Returns:
        Documento mascarado (ex: 123.***.789)
    """
    if not doc:
        return ""
    
    # Se estiver criptografado, primeiro descriptografar
    doc = decrypt(doc)
    
    # Remover formatação
    clean = ''.join(c for c in doc if c.isdigit())
    
    if len(clean) <= show_chars * 2:
        return "*" * len(clean)
    
    start = clean[:show_chars]
    end = clean[-show_chars:]
    middle = "*" * (len(clean) - show_chars * 2)
    
    return f"{start}.{middle}.{end}"


# Função de conveniência para verificar se biblioteca está disponível
def is_crypto_available() -> bool:
    """Retorna True se criptografia está disponível"""
    return CRYPTO_AVAILABLE and _get_fernet() is not None


# Auto-inicialização
if CRYPTO_AVAILABLE:
    _get_or_create_key()
