import database as db

texto_proposta = """PROPOSTA DE HONORÁRIOS ADVOCATÍCIOS

({acao})

Data: {data_atual} Validade: 10 dias corridos

CONTRATANTE: {nome}
CPF: {cpf}

CONTRATADA: Dra. Sheila Lopes Advogada – OAB/RJ nº 215691
Endereço: Rodovia Amaral Peixoto, km 22, 5 - São José, Maricá/RJ
Contato: (21) 970320748

Prezado(a) Sr(a). {nome},

Conforme nossa conversa, apresento a Vossa Senhoria a proposta de honorários para a prestação de serviços jurídicos especializados, visando a defesa dos seus interesses em Ação Judicial de Direito de Família.

1. OBJETO DOS SERVIÇOS

A presente proposta tem como objeto a prestação de serviços advocatícios para o ajuizamento e acompanhamento, em Primeira Instância, de {acao} (podendo, se necessário, ser cumulada com Alimentos, caso aplicável) referente aos seus filhos menores.

A ação será movida em face da parte contrária.

2. SERVIÇOS INCLUÍDOS
Os serviços abrangidos por esta proposta incluem:
• Reuniões e consultoria jurídica referente ao caso durante a tramitação do feito.
• Análise detalhada da documentação fornecida pelo Contratante.
• Elaboração e distribuição da Petição Inicial, com eventual pedido de Tutela de Urgência (liminar) para fixação provisória da guarda e/ou regime de convivência.
• Acompanhamento de todos os atos e publicações processuais em Primeira Instância.
• Elaboração de petições incidentais necessárias (manifestações, réplicas, etc.).
• Participação em audiências (conciliação, mediação e instrução).
• Acompanhamento de eventuais estudos psicossociais determinados pelo Juízo.
• Elaboração de alegações finais.
• Acompanhamento até a prolação da Sentença pelo Juiz de primeiro grau.

3. SERVIÇOS NÃO INCLUÍDOS
Não estão contemplados nesta proposta de honorários:
• Acompanhamento e interposição de eventuais Recursos para instâncias superiores (Tribunal de Justiça, STJ, STF).
• Ações incidentais autônomas (Ex: Ação de Prestação de Contas de Alimentos, Cumprimento de Sentença, Alienação Parental em autos apartados, etc.).
• Custas processuais, taxas judiciárias, despesas com perícias (psicossociais, se não cobertas pela gratuidade), emolumentos de cartório, honorários de sucumbência (pagos à parte contrária em caso de derrota) e outras despesas processuais.
• Despesas de locomoção para atos fora da Comarca de [Comarca], caso necessário.
Obs.: A contratação para eventuais serviços não incluídos, como Recursos, dependerá de nova proposta e contrato específico.

4. HONORÁRIOS ADVOCATÍCIOS (HONORÁRIOS CONTRATUAIS)

Pelos serviços jurídicos descritos no item 2 (atuação em Primeira Instância), os honorários advocatícios ficam ajustados no valor total de R$ [VALOR TOTAL].

5. CONDIÇÕES DE PAGAMENTO

O valor total dos honorários será pago pelo Contratante da seguinte forma:
1. ENTRADA: R$ [VALOR ENTRADA] no ato da assinatura do Contrato de Honorários e antes do início da elaboração da petição inicial.
2. SALDO REMANESCENTE: R$ [VALOR SALDO], divididos em [N] parcelas mensais e sucessivas de R$ [VALOR PARCELA], com vencimento da primeira parcela em 30 dias após a entrada.

Obs.: O não pagamento de qualquer parcela na data aprazada implicará em multa de 2% e juros de mora de 1% ao mês sobre o valor devido.

6. HONORÁRIOS DE SUCUMBÊNCIA

Eventuais honorários de sucumbência (valores pagos pela parte contrária em caso de êxito na ação, fixados pelo Juiz) pertencerão exclusivamente à Contratada (Advogada), conforme o Art. 23 da Lei nº 8.906/94 (Estatuto da Advocacia e da OAB), não se confundindo com os honorários contratuais aqui ajustados.

7. ACEITE

O aceite desta proposta se dará mediante a assinatura do respectivo Contrato de Prestação de Serviços Advocatícios, que detalhará todas as obrigações das partes, e o efetivo pagamento da Entrada (item 5.1).
Coloco-me à disposição para quaisquer esclarecimentos que se façam necessários.

Atenciosamente,
Dra. Sheila Lopes

CIENTE E DE ACORDO:
__________________________________________________
{nome}
CPF: {cpf}
"""

try:
    db.salvar_modelo_documento("Proposta de Honorários (Padrão)", "Contrato", texto_proposta)
    print("Modelo inserido com sucesso!")
except Exception as e:
    print(f"Erro ao inserir modelo: {e}")
