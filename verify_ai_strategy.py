
import sys
import os

# Adicionar diretorio raiz ao path
sys.path.append(os.getcwd())

import ai_gemini as ai
from datetime import datetime

# Mock Data
mock_processo = {
    'acao': '0001234-56.2024.8.19.0001',
    'cliente_nome': 'João da Silva',
    'assunto': 'Indenização por Danos Morais',
    'fase_processual': 'Sentença',
    'valor_causa': 50000.00
}

mock_historico = [
    {'data': '2024-12-01', 'descricao': 'Expedição de documento: Mandado de Pagamento'},
    {'data': '2024-11-20', 'descricao': 'Julgada Procedente a Ação'},
    {'data': '2024-10-15', 'descricao': 'Conclusos para Sentença'}
]

print("--- Iniciando Teste de IA Estratégica ---")
try:
    if not ai.inicializar_gemini():
        print("SKIP: IA não configurada (sem chave API).")
        sys.exit(0)

    print("Chamando analisar_estrategia_completa...")
    resultado = ai.analisar_estrategia_completa(mock_processo, mock_historico)
    
    print("\nRESULTADO OBTIDO:")
    print(resultado)
    
    if "erro" in resultado:
        print("FALHA: Erro retornado pela IA")
    else:
        print("SUCESSO: Análise gerada")
        if "sugestao_financeira" in resultado:
            print(f"Sugestão Financeira: {resultado['sugestao_financeira']}")

except Exception as e:
    print(f"ERRO CRÍTICO: {e}")
