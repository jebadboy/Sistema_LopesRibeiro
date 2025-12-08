import utils as ut
import os
from datetime import datetime

def testar_geracao_docs():
    print("Iniciando teste de geração de documentos...")
    
    # Dados fictícios para teste
    dados = {
        'nome': 'Fulano de Tal',
        'cpf_cnpj': '123.456.789-00',
        'endereco': 'Rua das Flores',
        'numero_casa': '100',
        'complemento': 'Apto 101',
        'bairro': 'Centro',
        'cidade': 'Maricá',
        'estado': 'RJ',
        'cep': '24900-000',
        'estado_civil': 'Casado',
        'profissao': 'Empresário',
        'proposta_objeto': 'Ação de Divórcio Consensual',
        'proposta_valor': 5000.00,
        'proposta_entrada': 1000.00,
        'proposta_parcelas': 4,
        'proposta_pagamento': 'Parcelado Mensal',
        'proposta_data_pagamento': datetime.now().strftime('%Y-%m-%d')
    }
    
    # Teste Procuração
    print("Gerando Procuração...")
    try:
        doc_proc = ut.criar_doc("Procuracao", dados, opcoes={'poderes_especiais': True})
        with open("teste_procuracao.docx", "wb") as f:
            f.write(doc_proc.getvalue())
        print("✅ Procuração gerada: teste_procuracao.docx")
    except Exception as e:
        print(f"❌ Erro ao gerar Procuração: {e}")

    # Teste Hipossuficiência
    print("Gerando Hipossuficiência...")
    try:
        doc_hipo = ut.criar_doc("Hipossuficiencia", dados)
        with open("teste_hipossuficiencia.docx", "wb") as f:
            f.write(doc_hipo.getvalue())
        print("✅ Hipossuficiência gerada: teste_hipossuficiencia.docx")
    except Exception as e:
        print(f"❌ Erro ao gerar Hipossuficiência: {e}")

if __name__ == "__main__":
    testar_geracao_docs()
