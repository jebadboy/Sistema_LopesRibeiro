import sys
import os
import logging
from pathlib import Path

# Adiciona o diretório raiz ao path para importar módulos
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

# Configuração de log
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def test_crypto_module():
    logger.info("--- Testando Módulo de Criptografia (crypto.py) ---")
    try:
        import crypto
    except ImportError as e:
        logger.error(f"Falha ao importar modulo crypto: {e}")
        return False

    if not crypto.is_crypto_available():
        logger.error("Criptografia NÃO está disponível (biblioteca ou chave faltando).")
        return False
    logger.info("Criptografia disponível.")

    # 1. Teste Básico
    original = "123.456.789-00"
    logger.info(f"Original: {original}")

    encrypted = crypto.encrypt(original)
    logger.info(f"Encriptado: {encrypted}")

    if not encrypted.startswith("ENC:"):
        logger.error("Erro: Texto encriptado não começa com 'ENC:'")
        return False
    
    decrypted = crypto.decrypt(encrypted)
    logger.info(f"Decriptado: {decrypted}")

    if decrypted != original:
        logger.error(f"Erro: Decriptado ({decrypted}) != Original ({original})")
        return False
    
    logger.info("Teste Básico: SUCESSO")

    # 2. Teste Idempotência (Encriptar o que já está encriptado)
    re_encrypted = crypto.encrypt(encrypted)
    if re_encrypted != encrypted:
        logger.error("Erro: Re-encriptação alterou o texto já encriptado.")
        return False
    logger.info("Teste Idempotência: SUCESSO")

    # 3. Teste Decriptar Texto Plano (Deve retornar o próprio texto)
    plain_decrypt = crypto.decrypt(original)
    if plain_decrypt != original:
        logger.error("Erro: Decriptar texto plano alterou o texto.")
        return False
    logger.info("Teste Decriptar Plano: SUCESSO")

    return True

def simulate_client_flow():
    logger.info("\n--- Simulando Fluxo de Cliente (clientes.py logica) ---")
    import crypto

    # Simula dados vindos do banco (Encriptados)
    db_cpf = crypto.encrypt("111.222.333-44")
    logger.info(f"Dado no Banco: {db_cpf}")

    # Simula Display (View)
    display_cpf = crypto.decrypt(db_cpf)
    logger.info(f"Exibido na UI: {display_cpf}")
    
    if display_cpf != "111.222.333-44":
        logger.error("Erro na exibição.")
        return False

    # Simula Edição (Usuário altera um dígito)
    # Usuário vê "111.222.333-44", edita para "111.222.333-55"
    edited_cpf = "111.222.333-55"
    logger.info(f"Editado pelo Usuário: {edited_cpf}")

    # Simula Salvar (Controller)
    # O código verifica se começa com ENC. Se não, encripta.
    to_save = edited_cpf
    if not str(to_save).startswith('ENC:'):
        to_save = crypto.encrypt(to_save)
    
    logger.info(f"Dado a Salvar: {to_save}")

    if not to_save.startswith("ENC:"):
         logger.error("Erro: Dado a salvar não está encriptado.")
         return False
    
    if crypto.decrypt(to_save) != edited_cpf:
         logger.error("Erro: Dado salvo não corresponde ao editado quando decriptado.")
         return False

    logger.info("Simulação de Fluxo: SUCESSO")
    return True

if __name__ == "__main__":
    if test_crypto_module() and simulate_client_flow():
        logger.info("\n✅ TODOS OS TESTES PASSARAM")
        sys.exit(0)
    else:
        logger.error("\n❌ FALHA NOS TESTES")
        sys.exit(1)
