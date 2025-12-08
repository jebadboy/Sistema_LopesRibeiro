import database as db
import utils as ut
import google_drive
import os
from datetime import datetime

def verify_upload():
    print("Iniciando verificação de upload automático...")
    
    # 1. Criar dados de teste
    dados = {
        'id': 999, # ID fictício
        'nome': 'Cliente Teste Auto Upload',
        'cpf_cnpj': '123.456.789-00',
        'nacionalidade': 'Brasileira',
        'profissao': 'Tester',
        'estado_civil': 'Solteiro',
        'rg': '12.345.678-9',
        'orgao_emissor': 'DETRAN/RJ',
        'endereco': 'Rua Teste',
        'numero_casa': '123',
        'complemento': 'Apto 1',
        'bairro': 'Centro',
        'cidade': 'Maricá',
        'estado': 'RJ',
        'link_drive': ''
    }
    
    try:
        # 2. Gerar Documento
        print("Gerando documento...")
        doc_bytes = ut.criar_doc("Hipossuficiencia", dados)
        
        # 3. Conectar ao Drive
        print("Conectando ao Drive...")
        service = google_drive.autenticar()
        
        if service:
            # 4. Criar Pasta
            print("Criando/Buscando pasta...")
            nome_pasta = f"{dados['nome']} - {dados['cpf_cnpj']}"
            id_pasta = google_drive.create_folder(service, nome_pasta, google_drive.PASTA_ALVO_ID)
            
            if id_pasta:
                print(f"Pasta ID: {id_pasta}")
                
                # 5. Salvar Temporário
                nome_arq = f"Hipossuficiencia_{dados['nome']}.docx"
                with open(nome_arq, "wb") as f:
                    f.write(doc_bytes.getvalue())
                
                # 6. Upload
                print("Fazendo upload...")
                file_id, web_link = google_drive.upload_file(service, nome_arq, id_pasta)
                
                # 7. Limpar
                if os.path.exists(nome_arq):
                    os.remove(nome_arq)
                
                if web_link:
                    print(f"[OK] Upload realizado com sucesso!")
                    print(f"Link: {web_link}")
                    return True
                else:
                    print("[ERRO] Falha ao obter link.")
            else:
                print("[ERRO] Falha ao criar pasta.")
        else:
            print("[ERRO] Falha na autenticação.")
            
    except Exception as e:
        print(f"[ERRO] Exceção durante verificação: {e}")
        
    return False

if __name__ == "__main__":
    verify_upload()
