import database as db

# Modelo completo baseado nas imagens fornecidas pelo usuário
texto_proposta_completa = """[INSTRUÇÃ: ADICIONAR LOGO "SHEILA LOPES ADVOGADA" NO TOPO CENTRALI ZADO]

Atenciosamente,
Dra. Sheila Lopes

CIENTE E DE ACORDO:
_________________________________ Sr. {nome} CPF: {cpf}


═══════════════════════════════════════════════════════════

PROPOSTA DE HONORÁRIOS ADVOCATÍCIOS

({acao})

Data: {data_atual}  Validade: 10 dias corridos

CONTRATANTE: Sr. {nome}

CONTRATADA: Dra. Sheila Lopes Advogada – OAB/RJ nº 215691

Endereço: Rodovia Amaral Peixoto, km 22, 5 - São José, Maricá/RJ Contato: (21)970320748

Prezado Sr. {nome},

Conforme nossa conversa, apresento a Vossa Senhoria a proposta de honorários para a prestação de serviços jurídicos especializados, visando a defesa dos seus interesses em Ação Judicial de Direito de Família.

1. OBJETO DOS SERVIÇOS

A presente proposta tem como objeto a prestação de serviços advocatícios para o ajuizamento e acompanhamento, em Primeira Instância, de {acao} (podendo, se necessário, ser cumulada com Alimentos, caso aplicável) referente aos seus 2 filhos menores.

A ação será movida em face de da Genitora.

2. SERVIÇOS INCLUÍDOS
Os serviços abrangidos por esta proposta incluem:
•  Reuniões e consultoria jurídica referente ao caso durante a tramitação do feito.
•  Análise detalhada da documentação fornecida pelo Contratante.
•  Elaboração e distribuição da Petição Inicial, com eventual pedido de Tutela de Urgência (liminar) para fixação provisória da guarda e/ou regime de convivência.
•  Acompanhamento de todos os atos e publicações processuais em Primeira Instância.
•  Elaboração de petições incidentais necessárias (manifestações, réplicas, etc.).
•  Participação em audiências (conciliação, mediação e instrução).
•  Acompanhamento de eventuais estudos psicossociais determinados pelo Juízo.
•  Elaboração de alegações finais.
•  Acompanhamento até a prolação da Sentença pelo Juiz de primeiro grau.

3. SERVIÇOS NÃO INCLUÍDOS
Não estão contemplados nesta proposta de honorários:
•  Acompanhamento e interposição de eventuais Recursos para instâncias superiores (Tribunal de Justiça, STJ, STF).
•  Ações incidentais autônomas (Ex: Ação de Prestação de Contas de Alimentos, Cumprimento de Sentença, Alienação Parental em autos apartados, etc.).
•  Custas processuais, taxas judiciárias, despesas com perícias (psicossociais, se não cobertas pela gratuidade), emolumentos de cartório, honorários de sucumbência (pagos à parte contrária em caso de derrota) e outras despesas processuais.
•  Despesas de locomoção para atos fora da Comarca de [Comarca onde a ação tramitará/Maricá], caso necessário.

Obs.: A contratação para eventuais serviços não incluídos, como Recursos, dependerá de nova proposta e contrato específico.

4. HONORÁRIOS ADVOCATÍCIOS (HONORÁRIOS CONTRATUAIS)

Pelos serviços jurídicos descritos no item 2 (atuação em Primeira Instância), os honorários advocatícios ficam ajustados no valor total de R$ 5.000,00 (Cinco mil reais).

5. CONDIÇÕES DE PAGAMENTO

O valor total dos honorários será pago pelo Contratante da seguinte forma:
1. ENTRADA: R$ 1.000,00 (Mil reais), a ser pago(a) no ato da assinatura do Contrato de Honorários e antes do início da elaboração da petição inicial, via (PIX )
2. SALDO REMANESCENTE: R$ 4.000,00 (Quatro mil reais), divididos em 10 (dez) parcelas mensais e sucessivas de R$ 400,00 (Quatrocentos e reais), com vencimento da primeira parcela em 30 dias após a entrada e as demais no mesmo dia dos meses subsequentes, via [Boleto / PIX ].

Obs.: O não pagamento de qualquer parcela na data aprazada implicará em multa de [Ex: 2%] e juros de mora de 1% ao mês sobre o valor devido.

6. HONORÁRIOS DE SUCUMBÊNCIA

Eventuais honorários de sucumbência (valores pagos pela parte contrária em caso de êxito na ação, fixados pelo Juiz) pertencerão exclusivamente à Contratada (Advogada), conforme o Art. 23 da Lei nº 8.906/94 (Estatuto da Advocacia e da OAB), não se confundindo com os honorários contratuais aqui ajustados.

7. ACEITE

O aceite desta proposta se dará mediante a assinatura do respectivo Contrato de Prestação de Serviços Advocatícios, que detalhará todas as obrigações das partes, e o efetivo pagamento da Entrada (item 5.1).
Coloco-me à disposição para quaisquer esclarecimentos que se façam necessários.


═══════════════════════════════════════════════════════════

(21) 970320748
sheilaadv.contato@gmail.com
Rodovia Amaral Peixoto km 22, nº5,
sobre loja, São José do Imbassaí, Maricá/RJ
"""

def criar_modelo_completo():
    print("Iniciando criacao do modelo completo...")
    try:
        # Limpar modelos antigos
        with db.get_connection() as conn:
            c = conn.cursor()
            c.execute("DELETE FROM modelos_documentos")
            conn.commit()
            print("[OK] Modelos antigos removidos.")

        # Inserir modelo completo
        db.salvar_modelo_documento(
            "Proposta de Honorarios - Modelo Completo",
            "Contrato",
            texto_proposta_completa
        )
        print("[OK] Modelo completo inserido com sucesso!")
        
        # Verificar
        df = db.sql_get("modelos_documentos")
        print(f"[OK] Total de modelos no banco: {len(df)}")
        if not df.empty:
            print(f"[OK] Modelo salvo: '{df.iloc[0]['titulo']}'")
        
    except Exception as e:
        print(f"[ERRO] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    criar_modelo_completo()
