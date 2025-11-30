import database as db
import sqlite3

# Texto formatado conforme a imagem do usuário (Eduardo Ribeiro)
texto_proposta = """SHEILA LOPES
ADVOGADA

PROPOSTA DE HONORÁRIOS

Data: {data_atual}                                        Validade: 10 dias corridos

CONTRATANTE: {nome}
CPF: {cpf}

1. OBJETO DOS SERVIÇOS

A presente proposta tem como objeto a prestação de serviços advocatícios para o ajuizamento e acompanhamento, em Primeira Instância, de **{acao}** (podendo, se necessário, ser cumulada com Alimentos, caso aplicável) referente aos seus filhos menores.

2. HONORÁRIOS (INVESTIMENTO)

Pelos serviços jurídicos descritos no item 1 (atuação em Primeira Instância), os honorários advocatícios ficam ajustados no valor total de:
**Valor Total: R$ [VALOR TOTAL]**

3. CONDIÇÕES DE PAGAMENTO

O valor total dos honorários será pago pelo Contratante da seguinte forma:

a) **ENTRADA:** R$ [VALOR ENTRADA] (no ato da assinatura do Contrato).
b) **SALDO REMANESCENTE:** R$ [VALOR SALDO], divididos em [N] parcelas mensais de R$ [VALOR PARCELA], com vencimento da primeira parcela em 30 dias após a entrada.

Obs.: O não pagamento de qualquer parcela na data aprazada implicará em multa de 2% e juros de mora de 1% ao mês sobre o valor devido.

4. SUCUMBÊNCIA

Eventuais honorários de sucumbência (valores pagos pela parte contrária em caso de êxito na ação, fixados pelo Juiz) pertencerão exclusivamente à Contratada (Advogada).

Atenciosamente,

Dra. Sheila Lopes
OAB/RJ nº 215691

CIENTE E DE ACORDO:
__________________________________________________
{nome}
CPF: {cpf}
"""

def fix():
    print("Iniciando correção...")
    try:
        # 1. Limpar tabela de modelos para evitar duplicatas antigas
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM modelos_documentos WHERE titulo LIKE 'Proposta de Honorários%'")
            conn.commit()
            print("Modelos antigos removidos.")

        # 2. Inserir novo modelo
        db.salvar_modelo_documento("Proposta de Honorários (Padrão)", "Contrato", texto_proposta)
        print("Novo modelo inserido com sucesso!")
        
        # 3. Verificar
        df = db.sql_get("modelos_documentos")
        print(f"Total de modelos agora: {len(df)}")
        print(df[['titulo', 'categoria']])
        
    except Exception as e:
        print(f"ERRO CRÍTICO: {e}")

if __name__ == "__main__":
    fix()
