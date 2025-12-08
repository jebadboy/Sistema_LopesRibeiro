import utils as ut
import os

def verificar_hipo():
    print("Iniciando verificação da Declaração de Hipossuficiência...")
    
    dados_teste = {
        'nome': 'Maria da Silva',
        'nacionalidade': 'Brasileira',
        'estado_civil': 'Casada',
        'profissao': 'Do lar',
        'rg': '12.345.678-9',
        'orgao_emissor': 'DETRAN/RJ',
        'cpf_cnpj': '123.456.789-00',
        'endereco': 'Rua das Flores',
        'numero_casa': '123',
        'complemento': 'Apto 101',
        'bairro': 'Centro',
        'cidade': 'Maricá',
        'estado': 'RJ',
        'cep': '24900-000'
    }
    
    try:
        doc_bytes = ut.criar_doc("Hipossuficiencia", dados_teste)
        
        output_file = "teste_hipossuficiencia.docx"
        with open(output_file, "wb") as f:
            f.write(doc_bytes.getvalue())
            
        print(f"[OK] Documento gerado com sucesso: {output_file}")
        print("Verifique se o conteúdo do arquivo corresponde ao modelo esperado.")
        
    except Exception as e:
        print(f"[ERRO] Falha na geração do documento: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verificar_hipo()
