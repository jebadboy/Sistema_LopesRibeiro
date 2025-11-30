import sys
sys.path.insert(0, r"g:\Meu Drive\automatizacao\Sistema_LopesRibeiro")
import database as db

texto = """[INSTRUÇÃO: ADICIONAR LOGO "SHEILA LOPES ADVOGADA" NO TOPO CENTRALIZADO]

Atenciosamente,
Dra. Sheila Lopes

CIENTE E DE ACORDO:
_________________________________ Sr. {nome} CPF: {cpf}


PROPOSTA DE HONORARIOS ADVOCATICIOS

({acao})

Data: {data_atual}  Validade: 10 dias corridos

CONTRATANTE: Sr. {nome}

CONTRATADA: Dra. Sheila Lopes Advogada - OAB/RJ no 215691

Endereco: Rodovia Amaral Peixoto, km 22, 5 - Sao Jose, Marica/RJ Contato: (21)970320748

Prezado Sr. {nome},

Conforme nossa conversa, apresento a Vossa Senhoria a proposta de honorarios para a prestacao de servicos juridicos especializados, visando a defesa dos seus interesses em Acao Judicial de Direito de Familia.

1. OBJETO DOS SERVICOS

A presente proposta tem como objeto a prestacao de servicos advocaticios para o ajuizamento e acompanhamento, em Primeira Instancia, de {acao} (podendo, se necessario, ser cumulada com Alimentos, caso aplicavel) referente aos seus 2 filhos menores.

A acao sera movida em face de da Genitora.

2. SERVICOS INCLUIDOS
Os servicos abrangidos por esta proposta incluem:
•  Reunioes e consultoria juridica referente ao caso durante a tramitacao do feito.
•  Analise detalhada da documentacao fornecida pelo Contratante.
•  Elaboracao e distribuicao da Peticao Inicial, com eventual pedido de Tutela de Urgencia (liminar) para fixacao provisoria da guarda e/ou regime de convivencia.
•  Acompanhamento de todos os atos e publicacoes processuais em Primeira Instancia.
•  Elaboracao de peticoes incidentais necessarias (manifestacoes, replicas, etc.).
•  Participacao em audiencias (conciliacao, mediacao e instrucao).
•  Acompanhamento de eventuais estudos psicossociais determinados pelo Juizo.
•  Elaboracao de alegacoes finais.
•  Acompanhamento ate a prolacao da Sentenca pelo Juiz de primeiro grau.

3. SERVICOS NAO INCLUIDOS
Nao estao contemplados nesta proposta de honorarios:
•  Acompanhamento e interposicao de eventuais Recursos para instancias superiores (Tribunal de Justica, STJ, STF).
•  Acoes incidentais autonomas (Ex: Acao de Prestacao de Contas de Alimentos, Cumprimento de Sentenca, Alienacao Parental em autos apartados, etc.).
•  Custas processuais, taxas judiciarias, despesas com pericias (psicossociais, se nao cobertas pela gratuidade), emolumentos de cartorio, honorarios de sucumbencia (pagos a parte contraria em caso de derrota) e outras despesas processuais.
•  Despesas de locomocao para atos fora da Comarca de [Comarca onde a acao tramitara/Marica], caso necessario.

Obs.: A contratacao para eventuais servicos nao incluidos, como Recursos, dependera de nova proposta e contrato especifico.

4. HONORARIOS ADVOCATICIOS (HONORARIOS CONTRATUAIS)

Pelos servicos juridicos descritos no item 2 (atuacao em Primeira Instancia), os honorarios advocaticios ficam ajustados no valor total de R$ 5.000,00 (Cinco mil reais).

5. CONDICOES DE PAGAMENTO

O valor total dos honorarios sera pago pelo Contratante da seguinte forma:
1. ENTRADA: R$ 1.000,00 (Mil reais), a ser pago(a) no ato da assinatura do Contrato de Honorarios e antes do inicio da elaboracao da peticao inicial, via (PIX )
2. SALDO REMANESCENTE: R$ 4.000,00 (Quatro mil reais), divididos em 10 (dez) parcelas mensais e sucessivas de R$ 400,00 (Quatrocentos e reais), com vencimento da primeira parcela em 30 dias apos a entrada e as demais no mesmo dia dos meses subsequentes, via [Boleto / PIX ].

Obs.: O nao pagamento de qualquer parcela na data aprazada implicara em multa de [Ex: 2%] e juros de mora de 1% ao mes sobre o valor devido.

6. HONORARIOS DE SUCUMBENCIA

Eventuais honorarios de sucumbencia (valores pagos pela parte contraria em caso de exito na acao, fixados pelo Juiz) pertencerao exclusivamente a Contratada (Advogada), conforme o Art. 23 da Lei no 8.906/94 (Estatuto da Advocacia e da OAB), nao se confundindo com os honorarios contratuais aqui ajustados.

7. ACEITE

O aceite desta proposta se dara mediante a assinatura do respectivo Contrato de Prestacao de Servicos Advocaticios, que detalhara todas as obrigacoes das partes, e o efetivo pagamento da Entrada (item 5.1).
Coloco-me a disposicao para quaisquer esclarecimentos que se facam necessarios.


(21) 970320748
sheilaadv.contato@gmail.com
Rodovia Amaral Peixoto km 22, no 5,
sobre loja, Sao Jose do Imbassai, Marica/RJ
"""

print("Inserindo modelo...")
db.salvar_modelo_documento("Proposta de Honorarios - Modelo Completo", "Contrato", texto)
print("Modelo inserido!")
df = db.sql_get("modelos_documentos")
print(f"Total: {len(df)}")
