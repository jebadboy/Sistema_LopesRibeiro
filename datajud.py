"""
Módulo de Integração com DataJud (CNJ)

Permite consultar processos judiciais usando a API oficial do CNJ.
Requer token de autenticação configurado em Administração.
"""

import requests
import re
from datetime import datetime
import streamlit as st
import hashlib
import json
import database as db
import ai_gemini as ai

# Mapa de APIs específicas por tribunal (principais)
APIS_TRIBUNAIS = {
    # Tribunais de Justiça Estaduais
    "TJRJ": "https://api-publica.datajud.cnj.jus.br/api_publica_tjrj/_search",
    "TJSP": "https://api-publica.datajud.cnj.jus.br/api_publica_tjsp/_search",
    "TJMG": "https://api-publica.datajud.cnj.jus.br/api_publica_tjmg/_search",
    "TJRS": "https://api-publica.datajud.cnj.jus.br/api_publica_tjrs/_search",
    "TJPR": "https://api-publica.datajud.cnj.jus.br/api_publica_tjpr/_search",
    "TJSC": "https://api-publica.datajud.cnj.jus.br/api_publica_tjsc/_search",
    "TJBA": "https://api-publica.datajud.cnj.jus.br/api_publica_tjba/_search",
    "TJPE": "https://api-publica.datajud.cnj.jus.br/api_publica_tjpe/_search",
    
    # Justiça Federal (TRFs)
    "TRF2": "https://api-publica.datajud.cnj.jus.br/api_publica_trf2/_search",
    
    # Justiça do Trabalho (TRTs)
    "TRT1": "https://api-publica.datajud.cnj.jus.br/api_publica_trt1/_search",
    
    # Tribunais Superiores
    "STJ": "https://api-publica.datajud.cnj.jus.br/api_publica_stj/_search",
}

# Mapa de códigos de tribunal (posição 14-15 do número CNJ)
CODIGOS_TRIBUNAL = {
    "01": "STF",
    "02": "CNJ",
    "03": "STJ",
    "04": "JF",      # Justiça Federal
    "05": "JT",      # Justiça do Trabalho
    "06": "JE",      # Justiça Eleitoral
    "07": "JM",      # Justiça Militar
    "08": "TJ",      # Tribunais de Justiça (Estadual)
    "09": "TR",      # Tribunais Regionais
}

# Mapa de códigos de estado (posição 16-19 do número CNJ)
CODIGOS_ESTADO = {
    "0001": "DF", "0002": "AC", "0003": "AM", "0004": "RR",
    "0005": "PA", "0006": "AP", "0007": "TO", "0008": "MA",
    "0009": "PI", "0010": "CE", "0011": "RN", "0012": "PB",
    "0013": "PE", "0014": "AL", "0015": "SE", "0016": "BA",
    "0017": "MG", "0018": "ES", "0019": "RJ", "0020": "SP",
    "0021": "PR", "0022": "SC", "0023": "RS", "0024": "MS",
    "0025": "MT", "0026": "GO", "0027": "RO",
}

# Mapa de regiões TRF (Justiça Federal)
CODIGOS_TRF = {
    "0018": "TRF2", "0019": "TRF2",  # ES, RJ
}

# Mapa de regiões TRT (Justiça do Trabalho)
CODIGOS_TRT = {
    "0019": "TRT1",  # RJ
}

def identificar_tribunal(numero):
    """Identifica o tribunal pelo número do processo CNJ"""
    numeros = re.sub(r'\D', '', numero)
    
    if len(numeros) != 20:
        return None, None
    
    # Estrutura CNJ: NNNNNNN-DD.AAAA.J.TT.OOOO
    # Posições: 0-6=Nº, 7-8=DV, 9-12=Ano, 13=Segmento(J), 14-15=Tribunal(TT), 16-19=Origem(OOOO)
    segmento = numeros[13]          # 1 dígito: Segmento judiciário
    cod_tribunal = numeros[14:16]   # 2 dígitos: Código do tribunal
    cod_origem = numeros[16:20]     # 4 dígitos: Código da origem
    
    # Mapa de segmentos para tipo
    segmento_map = {
        "1": "STF",
        "2": "CNJ", 
        "3": "STJ",
        "4": "JF",  # Justiça Federal
        "5": "JT",  # Justiça do Trabalho
        "6": "JE",  # Justiça Eleitoral
        "7": "JM",  # Justiça Militar
        "8": "TJ",  # Tribunais de Justiça (Estadual)
        "9": "TR",  # Tribunais Regionais
    }
    
    tipo_tribunal = segmento_map.get(segmento)
    
    # Tribunal de Justiça Estadual (segmento 8)
    if tipo_tribunal == "TJ":
        # Para TJs, o código do tribunal (posições 14-15) normalmente indica o estado
        # Mas vamos usar cod_origem também
        
        # Primeiro tenta mapear pelo cod_tribunal (ex: 19=RJ, 26=SP)
        estado_por_cod = {
            "19": "RJ",
            "26": "SP", 
            "17": "MG",
            "23": "RS",
            "21": "PR",
            "22": "SC",
            "16": "BA",
            "13": "PE",
        }
        
        estado = estado_por_cod.get(cod_tribunal)
        
        if estado:
            sigla = f"TJ{estado}"
            url = APIS_TRIBUNAIS.get(sigla)
            return sigla, url
    
    # Justiça Federal (segmento 4)
    elif tipo_tribunal == "JF":
        trf = CODIGOS_TRF.get(cod_origem)
        if trf:
            url = APIS_TRIBUNAIS.get(trf)
            return trf, url
    
    # Justiça do Trabalho (segmento 5)
    elif tipo_tribunal == "JT":
        trt = CODIGOS_TRT.get(cod_origem)
        if trt:
            url = APIS_TRIBUNAIS.get(trt)
            return trt, url
    
    # Superior Tribunal de Justiça (segmento 3)
    elif tipo_tribunal == "STJ":
        return "STJ", APIS_TRIBUNAIS.get("STJ")
    
    return None, None

def validar_numero_cnj(numero):
    """Valida formato CNJ"""
    numeros = re.sub(r'\D', '', numero)
    
    if len(numeros) != 20:
        return False, f"Número deve ter 20 dígitos (encontrados: {len(numeros)})"
    
    try:
        ano = int(numeros[9:13])
        if ano < 1900 or ano > 2100:
            return False, "Ano inválido no número do processo"
        return True, None
    except:
        return False, "Formato inválido"

def formatar_numero_cnj(numero):
    """Formata número no padrão CNJ"""
    numeros = re.sub(r'\D', '', numero)
    
    if len(numeros) != 20:
        return None
        
    return f"{numeros[0:7]}-{numeros[7:9]}.{numeros[9:13]}.{numeros[13]}.{numeros[14:16]}.{numeros[16:20]}"

def consultar_processo(numero, token=None):
    """Consulta processo na API DataJud do CNJ"""
    
    # Chave pública oficial do DataJud (documentada no Wiki do CNJ)
    # Fonte: https://datajud-wiki.cnj.jus.br/api-publica/acesso
    CHAVE_PUBLICA_CNJ = "cDZHYzlZa0JadVREZDJCendQbXY6SkJlTzNjLV9TRENyQk1RdnFKZGRQdw=="
    
    # Usar chave pública oficial se não for fornecido token customizado
    token_usar = token if (token and token.strip()) else CHAVE_PUBLICA_CNJ
    
    valido, erro = validar_numero_cnj(numero)
    if not valido:
        return None, f"❌ {erro}"
    
    formatado = formatar_numero_cnj(numero)
    if not formatado:
        return None, "❌ Erro ao formatar número do processo"
    
    tribunal, url_api = identificar_tribunal(numero)
    
    if not tribunal or not url_api:
        return None, ("❌ Tribunal não suportado. Atualmente suportamos: "
                     "TJs: TJRJ, TJSP, TJMG, TJRS, TJPR, TJSC, TJBA, TJPE | "
                     "TRF2 (JF) | TRT1 (Trabalho) | STJ")
    
    # CRÍTICO: Limpar número (apenas dígitos) para enviar à API
    # A API espera: 00018667620228190031 (sem pontos/traços)
    numero_limpo = re.sub(r'\D', '', numero)
    
    # Header com chave de autenticação oficial do CNJ
    headers = {
        "Authorization": f"APIKey {token_usar}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "query": {
            "match": {
                "numeroProcesso": numero_limpo  # CORRIGIDO: era 'formatado'
            }
        }
    }
    
    try:
        # Debug: mostrar informações da requisição
        print(f"\n=== DEBUG DataJud ===")
        print(f"Tribunal: {tribunal}")
        print(f"URL: {url_api}")
        print(f"Número formatado (display): {formatado}")
        print(f"Número limpo (API): {numero_limpo}")
        print(f"Token (primeiros 10 chars): {token_usar[:10]}...")
        print(f"Payload: {payload}")
        
        response = requests.post(
            url_api,
            json=payload,
            headers=headers,
            timeout=15
        )
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}...")  # Primeiros 500 chars
        print(f"=== FIM DEBUG ===\n")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('hits', {}).get('total', {}).get('value', 0) > 0:
                processo = data['hits']['hits'][0]['_source']
                return processo, None
            else:
                # Processo não encontrado - explicar melhor
                msg = (f"❌ Processo não encontrado na base DataJud do {tribunal}\n\n"
                       f"**Possíveis motivos:**\n"
                       f"• Processo em segredo de justiça ou sigiloso\n"
                       f"• Dados ainda não sincronizados pelo tribunal\n"
                       f"• Processo muito recente\n\n"
                       f"💡 **Você pode cadastrar manualmente** usando o formulário abaixo!")
                return None, msg
                
        elif response.status_code == 401 or response.status_code == 403:
            return None, "🔑 Token inválido ou expirado. Atualize em Administração."
            
        elif response.status_code == 404:
            return None, f"⚠️ Endpoint do {tribunal} não encontrado."
            
        elif response.status_code == 429:
            return None, "⏱️ Limite de requisições excedido. Aguarde alguns minutos."
            
        else:
            return None, f"⚠️ Erro na API {tribunal}: Código {response.status_code}"
            
    except requests.Timeout:
        return None, "⏱️ Timeout: API demorou muito. Tente novamente."
    except requests.ConnectionError:
        return None, "🌐 Erro de conexão. Verifique sua internet."
    except Exception as e:
        print(f"ERRO EXCEPTION: {str(e)}")
        return None, f"❌ Erro inesperado: {str(e)}"

def parsear_dados(dados_api):
    """Extrai dados relevantes do JSON"""
    try:
        partes = []
        
        # Tentar buscar em 'polos' (Padrão mais comum da API Pública v1/v2)
        lista_polos = dados_api.get('polos', [])
        if not lista_polos:
            # Fallback para 'partes' (alguns endpoints antigos)
            lista_polos = dados_api.get('partes', [])
            
        for polo in lista_polos:
            tipo_polo = polo.get('polo', 'INDEFINIDO') # Ativo/Passivo
            if tipo_polo == 'AT': tipo_polo = 'AUTOR'
            elif tipo_polo == 'PA': tipo_polo = 'REU'
            elif tipo_polo == 'TC': tipo_polo = 'TERCEIRO'
            
            for parte in polo.get('partes', []): # Lista de partes dentro do polo
                pessoa = parte.get('pessoa', {})
                # As vezes vem direto na parte, as vezes em pessoa
                nome = pessoa.get('nome') or parte.get('nome') or 'Nome não informado'
                cpf = pessoa.get('numeroDocumentoPrincipal') or pessoa.get('cpfCnpj') or parte.get('cpfCnpj') or ''
                
                partes.append({
                    'nome': nome,
                    'tipo': tipo_polo,
                    'cpf_cnpj': cpf,
                    'tipo_pessoa': 'Jurídica' if len(re.sub(r'\D', '', str(cpf))) > 11 else 'Física'
                })
        
        movimentos = []
        for m in dados_api.get('movimentos', [])[-20:]:  # Pega os 20 últimos
            
            # Tentar encontrar a descrição em vários lugares possíveis
            # Estruturas variam muito entre tribunais
            desc = None
            
            # 1. Estrutura Padrão (Nested)
            mov_obj = m.get('movimento')
            if isinstance(mov_obj, dict):
                desc = mov_obj.get('nome')
                if not desc:
                    desc = mov_obj.get('movimentoLocal', {}).get('nome')
                if not desc:
                    desc = mov_obj.get('movimentoNacional', {}).get('nome')
            
            # 2. Estrutura Plana (Alguns TJs)
            if not desc:
                desc = m.get('movimentoLocal', {}).get('nome')
            if not desc:
                desc = m.get('movimentoNacional', {}).get('nome')
            if not desc:
                desc = m.get('nome') # Eventualmente o nome está na raiz
            if not desc:
                desc = m.get('descricao')

            # Fallback final
            if not desc:
                desc = "Movimentação sem descrição"
            
            # Se a descrição for genérica, tentar adicionar o código
            if "Movimentação sem descrição" in desc:
                 cod = m.get('movimento', {}).get('codigo')
                 if cod:
                     desc = f"Movimentação Cód. {cod}"

            # Complementos (Tipo de documento, observações...)
            compl = ""
            for c in m.get('complementosTabelados', []):
                 # CORREÇÃO: Priorizar 'nome' (valor) sobre 'descricao' (label do campo)
                 # Ex: nome="sorteio", descricao="tipo_de_distribuicao" -> Queremos "sorteio"
                 c_valor = c.get('nome')
                 if not c_valor:
                     c_valor = c.get('descricao')
                     
                 if c_valor:
                     compl += f" - {c_valor}"
            
            # Observações (Ouro escondido)
            obs = m.get('observacao')
            if obs:
                compl += f" [Obs: {obs}]"

            movimentos.append({
                'data': m.get('dataHora', ''),
                'descricao': f"{desc}{compl}",
                'complemento': compl
            })
        # Extrair Comarca (Tentativa simples baseada no Órgão)
        orgao = dados_api.get('orgaoJulgador', {}).get('nome', 'Não especificado')
        comarca = "Não identificada"
        if "COMARCA DE " in orgao.upper():
            try:
                comarca = orgao.upper().split("COMARCA DE ")[1].split()[0] # Pega a primeira palavra após Comarca De
            except:
                pass
        elif "VARA" in orgao.upper():
            # Ex: MARICA 1 VARA CIVEL -> MARICA?
            # Tentar pegar a primeira palavra ou palavras antes de "VARA"
            tokens = orgao.split()
            if len(tokens) > 0:
                 # Heurística: se a primeira palavra não for numero, pode ser a comarca
                 if not tokens[0].isdigit():
                     comarca = tokens[0] 

        return {
            'numero': dados_api.get('numeroProcesso', ''),
            'classe': dados_api.get('classe', {}).get('nome', 'Não especificada'),
            'assunto': dados_api.get('assuntos', [{}])[0].get('nome', 'Não especificado') if dados_api.get('assuntos') else 'Não especificado',
            'orgao_julgador': orgao,
            'comarca': comarca.title(),
            'tribunal': dados_api.get('tribunal', 'Não especificado'),
            'data_ajuizamento': dados_api.get('dataAjuizamento', ''),
            'valor_causa': float(dados_api.get('valorCausa', 0) or 0),
            'partes': partes,
            'movimentos': movimentos,
            'sistema': dados_api.get('sistema', {}).get('nome', 'Não especificado')
        }
    except Exception as e:
        return {
            'numero': dados_api.get('numeroProcesso', ''),
            'classe': 'Erro ao parsear dados',
            'partes': [],
            'movimentos': [],
            'erro_parser': str(e)
        }

def mapear_fase_processual(classe):
    """Mapeia classe do processo para fase do sistema"""
    mapeamentos = {
        'Procedimento Comum': 'Em Andamento',
        'Procedimento Ordinário': 'Em Andamento',
        'Procedimento Sumário': 'Em Andamento',
        'Execução': 'Sentença',
        'Execução de Título Extrajudicial': 'Sentença',
        'Cumprimento de Sentença': 'Sentença',
        'Busca e Apreensão': 'Aguardando Liminar',
        'Ação de Cobrança': 'Em Andamento',
        'Ação de Indenização': 'Em Andamento',
        'Ação Declaratória': 'Em Andamento',
        'Mandado de Segurança': 'Aguardando Liminar',
    }
    
    return mapeamentos.get(classe, 'A Ajuizar')

def formatar_data_br(data_iso):
    """Formata data ISO para formato brasileiro"""
    try:
        if not data_iso:
            return ""
            
        if 'T' in data_iso:
            dt = datetime.fromisoformat(data_iso.replace('Z', '+00:00'))
        else:
            dt = datetime.strptime(data_iso, '%Y-%m-%d')
            
        return dt.strftime('%d/%m/%Y')
    except:
        return data_iso

def testar_conexao(token):
    """Testa se o token é válido"""
    if not token or token.strip() == "":
        return False, "Token vazio"
    
    headers = {
        "Authorization": f"APIKey {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "size": 1,
        "query": {
            "match_all": {}
        }
    }
    
    try:
        response = requests.post(
            APIS_TRIBUNAIS.get("TJRJ"),
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return True, "✅ Token válido e conectado!"
        elif response.status_code == 401 or response.status_code == 403:
            return False, "❌ Token inválido ou sem permissões"
        elif response.status_code == 404:
            return False, "⚠️ Erro 404: Endpoint não encontrado"
        else:
            return False, f"⚠️ Erro {response.status_code}"
    except Exception as e:
        return False, f"❌ Erro: {str(e)}"

def gerar_hash_movimentacao(data, descricao, processo_ref):
    """Gera hash único com processo + data + desc para evitar colisão entre processos diferentes"""
    texto = f"{processo_ref}|{data}|{descricao}"
    return hashlib.md5(texto.encode()).hexdigest()

def atualizar_processo_ia(processo_id, numero_cnj, token):
    """Atualiza andamentos e analisa com IA"""
    # Forçar recarga da IA (garante uso da chave mais recente)
    try:
        ai.reset_gemini()
    except:
        pass

    novos = 0
    analisados = 0
    
    # 1. Consultar DataJud
    dados, erro = consultar_processo(numero_cnj, token)
    if erro: return {"erro": erro}
    
    dados_limpos = parsear_dados(dados)
    movimentos = dados_limpos.get('movimentos', [])
    
    # 2. Buscar hashes existentes
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # 2. Buscar hashes existentes e suas análises
            cursor.execute("SELECT hash_id, analise_ia FROM andamentos WHERE id_processo = ?", (processo_id,))
            rows = cursor.fetchall()
            # Mapa: hash -> analise_anterior
            existentes_map = {row[0]: row[1] for row in rows if row[0]}
            
            # 3. Processar Movimentos
            
            # Contexto para IA
            nome_cliente = ""
            try:
                df_proc = db.sql_get_query(f"SELECT * FROM processos WHERE id={processo_id}")
                proc_dict = df_proc.iloc[0].to_dict() if not df_proc.empty else {}
                contexto = f"Processo: {proc_dict.get('numero')} - Ação: {proc_dict.get('acao')}"
                nome_cliente = proc_dict.get('cliente_nome', '')
            except:
                contexto = f"Processo CNJ: {numero_cnj}"
    
            for mov in movimentos:
                # CORREÇÃO: Incluir numero_cnj no hash para ser único globalmente
                h_id = gerar_hash_movimentacao(mov['data'], mov['descricao'], numero_cnj)
                
                # Critério: Novo OU Anterior com Erro
                processar = False
                mode = 'INSERT'
                
                if h_id not in existentes_map:
                    processar = True
                    print(f"DEBUG: Novo Movimento {h_id} -> PROCESSAR")
                else:
                    # Verifica se anterior foi erro
                    prev_analise = existentes_map[h_id]
                    
                    should_reprocess = False
                    reason = ""
                    
                    if not prev_analise:
                        should_reprocess = True
                        reason = "Vazio"
                    else:
                        try:
                            # Tentar entender o que tem lá
                            pa_json = json.loads(prev_analise)
                            
                            # 1. É um dicionário de erro explícito?
                            if "erro" in pa_json or "error" in pa_json:
                                should_reprocess = True
                                reason = "JSON com erro"
                                
                            # 2. O resumo indica erro?
                            resumo = pa_json.get('resumo', '').lower()
                            if "erro" in resumo or "falha" in resumo or not resumo:
                                should_reprocess = True
                                reason = f"Resumo inválido: {resumo}"
                                
                        except json.JSONDecodeError:
                            # Não é JSON, verificar se é string de erro plana
                            pa_lower = prev_analise.lower()
                            if "erro" in pa_lower or "falha" in pa_lower:
                                should_reprocess = True
                                reason = "Texto de erro"
                            # Se for texto válido mas antigo/formato ruim, talvez manter? 
                            # Mas se chegou aqui, provavelmente é lixo.
                            # Vamos ser conservadores: Se não é JSON, reprocessa para garantir padrão.
                            should_reprocess = True 
                            reason = "Não é JSON válido"

                    if should_reprocess:
                        processar = True
                        mode = 'UPDATE'
                        print(f"DEBUG: Reprocessando {h_id}. Motivo: {reason}")
                    else:
                         print(f"DEBUG: Análise OK -> Manter. (Hash: {h_id})")
                
                if processar:
                    # Análise de IA com 3 regras inteligentes
                    print(f"DEBUG: Iniciando análise IA para {mov['descricao'][:20]}...")
                    analise = ai.analisar_andamento(mov['descricao'], contexto, nome_cliente)
                    
                    # Salvar
                    analise_json = json.dumps(analise, ensure_ascii=False)
                    urgente = 1 if analise.get('urgente') else 0
                    
                    try:
                        if mode == 'INSERT':
                            cursor.execute("""
                                INSERT INTO andamentos (id_processo, data, descricao, tipo, hash_id, analise_ia, urgente, data_analise)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (processo_id, mov['data'], mov['descricao'], 'DataJud', h_id, analise_json, urgente, datetime.now().isoformat()))
                            novos += 1
                        else:
                            # Update existing record
                            cursor.execute("""
                                UPDATE andamentos 
                                SET analise_ia = ?, urgente = ?, data_analise = ?
                                WHERE hash_id = ? AND id_processo = ?
                            """, (analise_json, urgente, datetime.now().isoformat(), h_id, processo_id))
                        
                        analisados += 1
                    except Exception as e_ins:
                        print(f"Erro ao salvar movimento: {e_ins}")
                        pass
            
            conn.commit()
            
        return {"novos": novos, "analisados": analisados}
    except Exception as e:
        return {"erro": str(e)}
