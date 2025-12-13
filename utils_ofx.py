# --- CONCILIAÇÃO BANCÁRIA OFX ---

from datetime import datetime, timedelta
import database as db

def processar_arquivo_ofx(arquivo_bytes, nome_arquivo):
    """
    Processa arquivo OFX e extrai transações bancárias.
    
    Args:
        arquivo_bytes: Bytes do arquivo OFX
        nome_arquivo: Nome do arquivo para registro
    
    Returns:
        list: Lista de dicionários com transações
    """
    try:
        from ofxparse import OfxParser
        from io import BytesIO
        import json
        import re
        import hashlib

        # --- PARSER MANUAL (FALLBACK) ---
        def parse_ofx_manual(conteudo_bytes):
            """
            Parser manual robusto que extrai transações via Regex,
            ignorando validações estritas do ofxparse.
            """
            transacoes_manuais = []
            try:
                try:
                    texto = conteudo_bytes.decode('utf-8')
                except Exception as e:
                    print(f"Erro ao decodificar UTF-8: {e}")
                    texto = conteudo_bytes.decode('latin-1')

                # Encontrar blocos de transação
                # Regex para pegar tudo entre <STMTTRN> e </STMTTRN> ou <STMTTRN> e o próximo <STMTTRN>
                # Simplificado: pegar <STMTTRN>... (até </STMTTRN> ou fim do bloco)
                
                # Normalizar quebras de linha para facilitar regex
                texto = texto.replace('\r', '\n')
                
                # Iterar sobre blocos
                iterador = re.finditer(r'<STMTTRN>(.*?)(?:</STMTTRN>|<STMTTRN>|$)', texto, re.IGNORECASE | re.DOTALL)
                
                for match in iterador:
                    bloco = match.group(1)
                    
                    # Extrair campos
                    dt_match = re.search(r'<DTPOSTED>\s*([-0-9]+)', bloco, re.IGNORECASE)
                    amt_match = re.search(r'<TRNAMT>\s*([-0-9\.]+)', bloco, re.IGNORECASE)
                    fitid_match = re.search(r'<FITID>\s*([^<\n\r]+)', bloco, re.IGNORECASE)
                    memo_match = re.search(r'<MEMO>\s*([^<\n\r]+)', bloco, re.IGNORECASE)
                    name_match = re.search(r'<NAME>\s*([^<\n\r]+)', bloco, re.IGNORECASE)
                    check_match = re.search(r'<CHECKNUM>\s*([^<\n\r]+)', bloco, re.IGNORECASE)
                    type_match = re.search(r'<TRNTYPE>\s*([^<\n\r]+)', bloco, re.IGNORECASE)

                    # Dados essenciais
                    if not dt_match or not amt_match:
                        continue
                        
                    dt_str = dt_match.group(1)[:8] # YYYYMMDD
                    valor = float(amt_match.group(1).replace(',', '.'))
                    
                    # Data
                    try:
                        data_obj = datetime.strptime(dt_str, '%Y%m%d')
                    except:
                        data_obj = datetime.now()
                        
                    # FITID
                    if fitid_match and fitid_match.group(1).strip():
                        fitid = fitid_match.group(1).strip()
                    else:
                        # Gerar Hash com posição no arquivo para garantir unicidade
                        unique_str = f"{dt_str}-{valor}-{memo_match.group(1) if memo_match else ''}-{match.start()}"
                        fitid = hashlib.md5(unique_str.encode('utf-8')).hexdigest()
                        
                    # Descrição
                    memo = memo_match.group(1).strip() if memo_match else ""
                    name = name_match.group(1).strip() if name_match else ""
                    descricao = memo or name or "Sem descrição"
                    
                    # Tipo
                    tipo_trans = 'Crédito' if valor > 0 else 'Débito'
                    
                    transacao_data = {
                        'transaction_id': fitid,
                        'data_transacao': data_obj.strftime('%Y-%m-%d'),
                        'tipo': tipo_trans,
                        'valor': abs(valor),
                        'descricao': descricao,
                        'arquivo_origem': nome_arquivo,
                        'dados_brutos': json.dumps({
                            'payee': name,
                            'memo': memo,
                            'type': type_match.group(1) if type_match else 'OTHER',
                            'checknum': check_match.group(1) if check_match else None
                        })
                    }
                    transacoes_manuais.append(transacao_data)
                    
            except Exception as e:
                print(f"Erro no parser manual: {e}")
                
            return transacoes_manuais

        # --- TENTATIVA 1: OFXPARSE COM SANITIZAÇÃO ---
        transacoes = []
        try:
            # Tenta usar a sanitização anterior (Regex) + OfxParser
            # ... (código de sanitização anterior omitido para brevidade, mas mantido na lógica se necessário)
            # Para simplificar, vamos tentar parsear direto, se der erro, vamos pro manual.
            
            # Mas vamos manter a sanitização regex que fiz antes, pois ela ajuda o OfxParser
            # Vou re-incluir a função sanitizar_ofx aqui dentro para garantir
            
            def sanitizar_ofx_regex(conteudo_bytes):
                try:
                    try: texto = conteudo_bytes.decode('utf-8')
                    except: texto = conteudo_bytes.decode('latin-1')
                    pattern = re.compile(r'(<STMTTRN>)(.*?)(</STMTTRN>)', re.IGNORECASE | re.DOTALL)
                    counter = [0]
                    def fix(m):
                        counter[0] += 1
                        c = m.group(2)
                        if not re.search(r'<FITID>', c, re.IGNORECASE):
                            unique_str = f"{c}-{counter[0]}"
                            h = hashlib.md5(unique_str.encode('utf-8', errors='ignore')).hexdigest()
                            return f"{m.group(1)}\n<FITID>{h}\n{c}{m.group(3)}"
                        return m.group(0)
                    return pattern.sub(fix, texto).encode('utf-8')
                except: return conteudo_bytes

            arquivo_safe = sanitizar_ofx_regex(arquivo_bytes)
            ofx = OfxParser.parse(BytesIO(arquivo_safe))
            
            if hasattr(ofx, 'account') and ofx.account:
                for trans in ofx.account.statement.transactions:
                    tipo = 'Crédito' if trans.amount > 0 else 'Débito'
                    fitid = trans.id
                    if not fitid:
                        unique_str = f"{trans.date}-{trans.amount}-{trans.memo}-{trans.payee}"
                        fitid = hashlib.md5(unique_str.encode('utf-8')).hexdigest()

                    transacao_data = {
                        'transaction_id': fitid,
                        'data_transacao': trans.date.strftime('%Y-%m-%d') if trans.date else datetime.now().strftime('%Y-%m-%d'),
                        'tipo': tipo,
                        'valor': abs(float(trans.amount)),
                        'descricao': trans.memo or trans.payee or 'Sem descrição',
                        'arquivo_origem': nome_arquivo,
                        'dados_brutos': json.dumps({
                            'payee': trans.payee, 'memo': trans.memo, 'type': trans.type,
                            'checknum': trans.checknum if hasattr(trans, 'checknum') else None
                        })
                    }
                    transacoes.append(transacao_data)
                    
        except Exception as e:
            print(f"OfxParser falhou ({e}), tentando parser manual...")
            # --- TENTATIVA 2: PARSER MANUAL ---
            transacoes = parse_ofx_manual(arquivo_bytes)
            
            if not transacoes:
                # Se ambos falharem, relança o erro original
                raise Exception(f"Falha ao processar OFX (Parser e Manual falharam). Erro original: {e}")

        return transacoes

    except Exception as e:
        raise Exception(f"Erro ao processar arquivo OFX: {str(e)}")

def verificar_transacao_duplicada(transaction_id):
    """
    Verifica se transação já foi importada anteriormente.
    
    Args:
        transaction_id: FITID da transação
    
    Returns:
        bool: True se já existe, False caso contrário
    """
    try:
        import database_adapter as adapter
        query = "SELECT COUNT(*) as count FROM transacoes_bancarias WHERE transaction_id = ?"
        if adapter.USE_POSTGRES:
            query = query.replace('?', '%s')
        result = db.run_query(query, (transaction_id,))
        
        if result and len(result) > 0:
            return result[0].get('count', 0) > 0
        
        return False
    except Exception as e:
        print(f"Erro ao verificar duplicidade: {e}")
        return False

def salvar_transacao_bancaria(transacao_data):
    """
    Salva transação bancária no banco de dados.
    
    Args:
        transacao_data: Dicionário com dados da transação
    
    Returns:
        int: ID da transação salva
    """
    try:
        return db.crud_insert(
            'transacoes_bancarias',
            transacao_data,
            f"Transação bancária importada: {transacao_data.get('descricao', '')}"
        )
    except Exception as e:
        raise Exception(f"Erro ao salvar transação: {str(e)}")

def buscar_matches_inteligente(transacao):
    """
    Busca lançamentos financeiros que podem corresponder à transação bancária.
    Algoritmo de matching:
    - Valor exato
    - Data próxima (±5 dias)
    - Status Pendente
    - Tipo Entrada (apenas para créditos)
    
    Args:
        transacao: Dicionário com dados da transação bancária
    
    Returns:
        list: Lista de possíveis matches com score de confiança
    """
    try:
        # Apenas processar créditos (pagamentos recebidos)
        if transacao.get('tipo') != 'Crédito':
            return []
        
        valor = transacao.get('valor', 0)
        data_trans = transacao.get('data_transacao')
        
        # Calcular janela de datas (±5 dias)
        data_obj = datetime.strptime(data_trans, '%Y-%m-%d')
        data_ini = (data_obj - timedelta(days=5)).strftime('%Y-%m-%d')
        data_fim = (data_obj + timedelta(days=5)).strftime('%Y-%m-%d')
        
        # Buscar lançamentos financeiros pendentes
        query = """
        SELECT f.*, c.nome as cliente_nome, p.numero as processo_numero
        FROM financeiro f
        LEFT JOIN clientes c ON f.id_cliente = c.id
        LEFT JOIN processos p ON f.id_processo = p.id
        WHERE f.tipo = 'Entrada'
        AND f.status_pagamento = 'Pendente'
        AND f.valor = ?
        AND f.vencimento BETWEEN ? AND ?
        ORDER BY f.vencimento ASC
        """
        
        import database_adapter as adapter
        if adapter.USE_POSTGRES:
            query = query.replace('?', '%s')
        
        lancamentos = db.run_query(query, (valor, data_ini, data_fim))
        
        # Calcular score para cada match
        matches = []
        for lanc in lancamentos:
            vencimento = lanc.get('vencimento')
            if not vencimento:
                continue
            
            # Calcular diferença de dias
            venc_obj = datetime.strptime(vencimento, '%Y-%m-%d')
            diff_dias = abs((data_obj - venc_obj).days)
            
            # Calcular score
            if diff_dias == 0:
                score = 100
            elif diff_dias <= 1:
                score = 90
            elif diff_dias <= 3:
                score = 80
            elif diff_dias <= 5:
                score = 70
            else:
                score = 60
            
            match_data = dict(lanc)
            match_data['score'] = score
            match_data['diff_dias'] = diff_dias
            
            matches.append(match_data)
        
        # Ordenar por score (maior primeiro)
        matches.sort(key=lambda x: x['score'], reverse=True)
        
        return matches
        
    except Exception as e:
        print(f"Erro ao buscar matches: {e}")
        return []

def conciliar_transacao(id_transacao_bancaria, id_financeiro, usuario):
    """
    Realiza conciliação entre transação bancária e lançamento financeiro.
    
    Args:
        id_transacao_bancaria: ID da transação bancária
        id_financeiro: ID do lançamento financeiro
        usuario: Nome do usuário que está conciliando
    
    Returns:
        dict: {'sucesso': bool, 'erro': str}
    """
    try:
        # 1. Buscar dados da transação bancária
        query_trans = "SELECT * FROM transacoes_bancarias WHERE id = ?"
        import database_adapter as adapter
        if adapter.USE_POSTGRES:
            query_trans = query_trans.replace('?', '%s')
        
        transacao = db.run_query(query_trans, (id_transacao_bancaria,))
        if not transacao or len(transacao) == 0:
            return {'sucesso': False, 'erro': 'Transação bancária não encontrada'}
        
        transacao = transacao[0]
        data_pagamento = transacao.get('data_transacao')
        
        # 2. Atualizar transação bancária
        db.crud_update(
            'transacoes_bancarias',
            {
                'id_financeiro': id_financeiro,
                'status_conciliacao': 'Conciliado',
                'conciliado_por': usuario,
                'data_conciliacao': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'id = ?',
            (id_transacao_bancaria,),
            f'Conciliação realizada por {usuario}'
        )
        
        # 3. Atualizar lançamento financeiro
        db.crud_update(
            'financeiro',
            {
                'status_pagamento': 'Pago',
                'data_pagamento': data_pagamento
            },
            'id = ?',
            (id_financeiro,),
            f'Baixa automática via conciliação bancária'
        )
        
        return {'sucesso': True}
        
    except Exception as e:
        return {'sucesso': False, 'erro': str(e)}
