import google_drive
import os
import datetime

def test_drive():
    print("--- Iniciando Teste de Integracao Google Drive ---")
    
    # 1. Autenticacao
    print("1. Tentando autenticar...")
    service = google_drive.autenticar()
    if not service:
        print("[ERRO] Falha na autenticacao.")
        return
    print("[OK] Autenticacao realizada com sucesso.")
    
    # 2. Usar Pasta Configurada
    folder_id = google_drive.PASTA_ALVO_ID
    print(f"2. Usando pasta configurada ID: {folder_id}")
    
    if not folder_id:
        print("[ERRO] PASTA_ALVO_ID nao configurada.")
        return

    # 2.1 Tentar LISTAR arquivos (Teste de Leitura e ID)
    print("2.1 Testando acesso de LEITURA...")
    try:
        results = service.files().list(
            q=f"'{folder_id}' in parents",
            fields="files(id, name)"
        ).execute()
        files = results.get('files', [])
        print(f"[OK] Leitura bem sucedida! Encontrados {len(files)} arquivos na pasta.")
    except Exception as e:
        print(f"[ERRO] Falha na leitura: {e}")
        return

    # 3. Upload de Arquivo Dummy (Com conteudo)
    print("3. Testando ESCRITA (Arquivo com dados)...")
    dummy_filename = "teste_dados.txt"
    with open(dummy_filename, "w") as f:
        f.write("Teste de cota de armazenamento.")
        
    file_id, web_link = google_drive.upload_file(service, dummy_filename, folder_id)
    
    if file_id:
        print(f"[OK] Upload realizado com sucesso!")
        print(f"   ID do Arquivo: {file_id}")
        print(f"   Link: {web_link}")
        try:
            os.remove(dummy_filename)
        except:
            pass
    else:
        print("[ERRO] Falha no upload.")

if __name__ == "__main__":
    test_drive()
