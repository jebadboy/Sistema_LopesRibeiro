import shutil
import os
from datetime import datetime
import logging

# Configuração de Log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_backup():
    """
    Cria um backup completo do sistema (código e banco de dados).
    """
    # Diretórios e Arquivos para Backup
    SOURCE_DIR = os.getcwd()
    BACKUP_ROOT = os.path.join(SOURCE_DIR, "backups")
    
    # Itens a incluir
    INCLUDE_FILES = [
        'app.py', 'database.py', 'utils.py', 'requirements.txt', 
        'dados_escritorio.db', 'README.md', 'RECOVERY.md'
    ]
    INCLUDE_DIRS = ['modules', 'assets', '.streamlit']
    
    # Timestamp para nome único
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_folder_name = f"backup_sistema_{timestamp}"
    backup_path = os.path.join(BACKUP_ROOT, backup_folder_name)
    
    # Criar diretório de backup
    if not os.path.exists(BACKUP_ROOT):
        os.makedirs(BACKUP_ROOT)
    
    if not os.path.exists(backup_path):
        os.makedirs(backup_path)
        
    logger.info(f"Iniciando backup em: {backup_path}")
    
    try:
        # 1. Copiar Arquivos
        for filename in INCLUDE_FILES:
            src = os.path.join(SOURCE_DIR, filename)
            dst = os.path.join(backup_path, filename)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                logger.info(f"Arquivo copiado: {filename}")
            else:
                logger.warning(f"Arquivo não encontrado: {filename}")
        
        # 2. Copiar Diretórios
        for dirname in INCLUDE_DIRS:
            src = os.path.join(SOURCE_DIR, dirname)
            dst = os.path.join(backup_path, dirname)
            if os.path.exists(src):
                shutil.copytree(src, dst)
                logger.info(f"Diretório copiado: {dirname}")
            else:
                logger.warning(f"Diretório não encontrado: {dirname}")
        
        # 3. Compactar (Zip)
        zip_filename = os.path.join(BACKUP_ROOT, f"{backup_folder_name}")
        shutil.make_archive(zip_filename, 'zip', backup_path)
        logger.info(f"Arquivo ZIP criado: {zip_filename}.zip")
        
        # 4. Limpeza (Opcional: remover pasta descompactada se quiser apenas o zip)
        # shutil.rmtree(backup_path) 
        
        print(f"\n[SUCESSO] Ponto de recuperacao criado em: {zip_filename}.zip")
        return True
        
    except Exception as e:
        logger.error(f"Falha ao criar backup: {e}")
        print(f"\n[ERRO] Falha ao criar backup. Verifique o log.")
        return False

if __name__ == "__main__":
    create_backup()
