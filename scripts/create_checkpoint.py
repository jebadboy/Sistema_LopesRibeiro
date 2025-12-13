import os
import shutil
import zipfile
import datetime

# Configuração
ROOT_DIR = r"g:\Meu Drive\automatizacao\Sistema_LopesRibeiro"
BACKUPS_DIR = os.path.join(ROOT_DIR, "backups")

# Arquivos críticos para backup
FILES_TO_BACKUP = [
    "dados_escritorio.db",
    "data.db",
    "ai_cache.db",
    "sistema.db", # Se existir
    ".env",
    "credentials.json",
    "token.json",
    "client_secret.json",
    "railway.json",
    "Procfile",
    "requirements.txt"
]

# Diretórios para zipar
DIRS_TO_ZIP = [
    "modules",
    "scripts"
]

def create_checkpoint():
    # Nome da pasta de backup com Timestamp
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y_%m_%d_%H_%M")
    checkpoint_name = f"checkpoint_{timestamp}"
    destination_dir = os.path.join(BACKUPS_DIR, checkpoint_name)
    
    if not os.path.exists(destination_dir):
        os.makedirs(destination_dir)
        print(f"Diretório criado: {destination_dir}")
        
    # Copiar arquivos
    print("Copiando arquivos criticos...")
    for filename in FILES_TO_BACKUP:
        src = os.path.join(ROOT_DIR, filename)
        dst = os.path.join(destination_dir, filename)
        
        if os.path.exists(src) and os.path.isfile(src):
            try:
                shutil.copy2(src, dst)
                print(f"[OK] Copiado: {filename}")
            except Exception as e:
                print(f"[ERROR] Erro ao copiar {filename}: {e}")
        else:
            print(f"[INFO] Ignorado (arquivo nao encontrado): {filename}")
            
    # Zipar diretórios de código
    print("Compactando codigo fonte...")
    for dirname in DIRS_TO_ZIP:
        src_dir = os.path.join(ROOT_DIR, dirname)
        if os.path.exists(src_dir):
            zip_filename = os.path.join(destination_dir, f"{dirname}.zip")
            try:
                with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(src_dir):
                        for file in files:
                            # Ignorar __pycache__
                            if "__pycache__" not in root:
                                file_path = os.path.join(root, file)
                                arcname = os.path.relpath(file_path, start=ROOT_DIR)
                                zipf.write(file_path, arcname)
                print(f"[OK] Zipado: {dirname} -> {os.path.basename(zip_filename)}")
            except Exception as e:
                print(f"[ERROR] Erro ao zipar {dirname}: {e}")
                
    print(f"\nBackup concluido com sucesso em: {destination_dir}")
    return destination_dir

if __name__ == "__main__":
    create_checkpoint()
