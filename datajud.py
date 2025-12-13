"""
Módulo de Integração com DataJud (CNJ)

Permite consultar processos judiciais usando a API oficial do CNJ.
Requer token de autenticação configurado em Administração.

Features Sprint 3:
- Retry automático com exponential backoff para falhas de conexão
- Tratamento robusto de timeouts e erros 503
"""

import requests
import re
import time
import logging
from datetime import datetime
from functools import wraps
import streamlit as st
import hashlib
import json
import database as db
import ai_gemini as ai

logger = logging.getLogger(__name__)

# ==================== RETRY COM EXPONENTIAL BACKOFF ====================

def retry_with_backoff(max_retries: int = 3, base_delay: float = 2.0, exceptions: tuple = (requests.RequestException,)):
    """
    Decorator para retry automático com exponential backoff.
    
    Args:
        max_retries: Número máximo de tentativas (default: 3)
        base_delay: Delay base em segundos (default: 2)
        exceptions: Tuple de exceções que disparam retry
    
    Uso:
        @retry_with_backoff(max_retries=3)
        def consultar_api():
            ...
    
    Comportamento:
        - Tentativa 1: imediata
        - Tentativa 2: espera 2s
        - Tentativa 3: espera 4s
        - Após 3 falhas: levanta exceção original
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            f"[DataJud] Tentativa {attempt + 1}/{max_retries} falhou: {e}. "
                            f"Aguardando {delay}s antes de retry..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"[DataJud] Todas as {max_retries} tentativas falharam. "
                            f"Último erro: {e}"
                        )
            
            # Após todas as tentativas, levantar última exceção
            raise last_exception
        
        return wrapper
    return decorator



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

# ==================== DICIONÁRIO DE TRADUÇÃO DE MOVIMENTOS ====================
# Traduz códigos "secos" da API em textos ricos para a IA entender
# Estrutura: codigo ou nome -> {texto_ia, flags[], gatilho_financeiro}

DICIONARIO_MOVIMENTOS = {
    # === SENTENÇAS ===
    "procedência": {
        "texto": "✅ Sentença FAVORÁVEL ao autor - Pedido PROCEDENTE",
        "flags": ["sentenca_favoravel", "fase_sentenca"],
        "gatilho_financeiro": True,
        "urgencia": "alta"
    },
    "procedência em parte": {
        "texto": "⚖️ Sentença PARCIALMENTE favorável ao autor",
        "flags": ["sentenca_parcial", "fase_sentenca"],
        "gatilho_financeiro": True,
        "urgencia": "alta"
    },
    "improcedência": {
        "texto": "❌ Sentença DESFAVORÁVEL ao autor - Pedido IMPROCEDENTE",
        "flags": ["sentenca_desfavoravel", "fase_sentenca"],
        "gatilho_financeiro": False,
        "urgencia": "alta"
    },
    "julgamento": {
        "texto": "⚖️ Decisão judicial proferida",
        "flags": ["fase_julgamento"],
        "gatilho_financeiro": False,
        "urgencia": "media"
    },
    
    # === LIMINARES ===
    "antecipação de tutela": {
        "texto": "🚨 LIMINAR CONCEDIDA - Tutela antecipada deferida",
        "flags": ["liminar", "urgente"],
        "gatilho_financeiro": False,
        "urgencia": "critica"
    },
    "tutela de urgência": {
        "texto": "🚨 TUTELA DE URGÊNCIA - Medida urgente deferida",
        "flags": ["liminar", "urgente"],
        "gatilho_financeiro": False,
        "urgencia": "critica"
    },
    
    # === RECURSOS ===
    "remessa": {
        "texto": "📤 Processo REMETIDO ao tribunal superior",
        "flags": ["fase_recursal"],
        "gatilho_financeiro": False,
        "urgencia": "media"
    },
    "apelação": {
        "texto": "📋 RECURSO DE APELAÇÃO interposto",
        "flags": ["fase_recursal", "recurso"],
        "gatilho_financeiro": False,
        "urgencia": "media"
    },
    "agravo": {
        "texto": "📋 AGRAVO interposto",
        "flags": ["fase_recursal", "recurso"],
        "gatilho_financeiro": False,
        "urgencia": "media"
    },
    
    # === CONCLUSÕES ===
    "conclusão": {
        "texto": "📁 Processo CONCLUSO para decisão do juiz",
        "flags": ["aguardando_decisao"],
        "gatilho_financeiro": False,
        "urgencia": "baixa"
    },
    "conclusão ao juiz": {
        "texto": "📁 Processo CONCLUSO para decisão do juiz",
        "flags": ["aguardando_decisao"],
        "gatilho_financeiro": False,
        "urgencia": "baixa"
    },
    
    # === EXPEDIÇÕES (gatilho financeiro) ===
    "expedição de certidão": {
        "texto": "📄 Certidão EXPEDIDA",
        "flags": ["certidao"],
        "gatilho_financeiro": True,
        "urgencia": "media"
    },
    "expedição de mandado": {
        "texto": "📄 Mandado EXPEDIDO - Verificar cumprimento",
        "flags": ["mandado"],
        "gatilho_financeiro": True,
        "urgencia": "alta"
    },
    "expedida/certificada": {
        "texto": "📄 Documento EXPEDIDO/CERTIFICADO",
        "flags": ["certidao"],
        "gatilho_financeiro": True,
        "urgencia": "media"
    },
    
    # === INTIMAÇÕES ===
    "intimação": {
        "texto": "📬 INTIMAÇÃO - Prazo para manifestação",
        "flags": ["intimacao", "prazo"],
        "gatilho_financeiro": False,
        "urgencia": "alta"
    },
    "citação": {
        "texto": "📬 CITAÇÃO realizada",
        "flags": ["citacao"],
        "gatilho_financeiro": False,
        "urgencia": "media"
    },
    
    # === AUDIÊNCIAS ===
    "audiência": {
        "texto": "🎤 AUDIÊNCIA designada/realizada",
        "flags": ["audiencia"],
        "gatilho_financeiro": False,
        "urgencia": "alta"
    },
    "audiência de conciliação": {
        "texto": "🤝 AUDIÊNCIA DE CONCILIAÇÃO designada",
        "flags": ["audiencia", "conciliacao"],
        "gatilho_financeiro": False,
        "urgencia": "alta"
    },
    
    # === TRÂNSITO EM JULGADO ===
    "trânsito em julgado": {
        "texto": "✅ TRÂNSITO EM JULGADO - Decisão definitiva",
        "flags": ["transito_julgado", "fase_final"],
        "gatilho_financeiro": True,
        "urgencia": "critica"
    },
    
    # === DISTRIBUIÇÃO ===
    "distribuição": {
        "texto": "📋 Processo DISTRIBUÍDO",
        "flags": ["inicio"],
        "gatilho_financeiro": False,
        "urgencia": "baixa"
    },
}

# Complementos que indicam fase recursal
COMPLEMENTOS_RECURSO = [
    "em grau de recurso",
    "recurso",
    "apelação",
    "agravo",
    "tribunal"
]

def enriquecer_movimento(movimento: dict) -> dict:
    """
    Transforma movimento "seco" da API em texto rico para IA.
    
    Args:
        movimento: Dict com 'nome', 'descricao', 'complementosTabelados', 'codigo'
    
    Returns:
        Dict enriquecido com 'texto_ia', 'flags', 'gatilho_financeiro', 'urgencia'
    """
    nome_original = movimento.get('descricao', movimento.get('nome', '')).lower().strip()
    complementos = movimento.get('complemento', '')
    codigo = movimento.get('codigo')
    
    # Resultado padrão
    resultado = {
        'texto_original': movimento.get('descricao', ''),
        'texto_ia': movimento.get('descricao', nome_original),
        'flags': [],
        'gatilho_financeiro': False,
        'urgencia': 'baixa',
        'data': movimento.get('data', '')
    }
    
    # Buscar no dicionário (match parcial)
    for chave, traducao in DICIONARIO_MOVIMENTOS.items():
        if chave in nome_original:
            resultado['texto_ia'] = traducao['texto']
            resultado['flags'] = traducao['flags'].copy()
            resultado['gatilho_financeiro'] = traducao['gatilho_financeiro']
            resultado['urgencia'] = traducao['urgencia']
            break
    
    # Verificar complementos que indicam fase recursal
    if complementos:
        compl_lower = complementos.lower()
        for termo in COMPLEMENTOS_RECURSO:
            if termo in compl_lower:
                if 'fase_recursal' not in resultado['flags']:
                    resultado['flags'].append('fase_recursal')
                resultado['texto_ia'] += f" [Em grau de recurso]"
                break
        
        # Adicionar complemento ao texto se não estiver vazio
        if complementos.strip() and complementos.strip() not in resultado['texto_ia']:
            resultado['texto_ia'] += f" - {complementos.strip()}"
    
    return resultado


def enriquecer_movimentos_lista(movimentos: list) -> list:
    """
    Enriquece lista de movimentos para análise da IA.
    
    Args:
        movimentos: Lista de dicts de movimentos
    
    Returns:
        Lista de movimentos enriquecidos + resumo de flags
    """
    enriquecidos = []
    todas_flags = set()
    tem_gatilho_financeiro = False
    
    for mov in movimentos:
        enriquecido = enriquecer_movimento(mov)
        enriquecidos.append(enriquecido)
        todas_flags.update(enriquecido['flags'])
        if enriquecido['gatilho_financeiro']:
            tem_gatilho_financeiro = True
    
    return {
        'movimentos': enriquecidos,
        'flags_encontradas': list(todas_flags),
        'gatilho_financeiro': tem_gatilho_financeiro,
        'total': len(enriquecidos)
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
        # Mapeamento de Regiões (cod_tribunal = 2 dígitos) para APIs
        # CORREÇÃO: Usar cod_tribunal (Região), NÃO cod_origem (Vara)
        mapa_trt = {
            "01": "TRT1",   # Rio de Janeiro
            "02": "TRT2",   # SP Capital
            "15": "TRT15",  # SP Interior
            # Adicionar outros conforme necessidade futura
        }
        
        sigla = mapa_trt.get(cod_tribunal)
        if sigla:
            url = APIS_TRIBUNAIS.get(sigla)
            return sigla, url
    
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
    
    # Função interna com retry automático
    @retry_with_backoff(max_retries=3, base_delay=2.0, exceptions=(requests.Timeout, requests.ConnectionError))
    def _fazer_requisicao():
        """Faz requisição HTTP com retry automático em caso de falha."""
        logger.info(f"[DataJud] Consultando {tribunal}: {numero_limpo}")
        return requests.post(
            url_api,
            json=payload,
            headers=headers,
            timeout=20  # Aumentado de 15 para 20s
        )
    
    try:
        # Debug: mostrar informações da requisição
        print(f"\n=== DEBUG DataJud ===")
        print(f"Tribunal: {tribunal}")
        print(f"URL: {url_api}")
        print(f"Número formatado (display): {formatado}")
        print(f"Número limpo (API): {numero_limpo}")
        print(f"Token (primeiros 10 chars): {token_usar[:10]}...")
        print(f"Payload: {payload}")
        
        # Usar função com retry
        response = _fazer_requisicao()
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:500]}...")  # Primeiros 500 chars
        print(f"=== FIM DEBUG ===\n")
        
        if response.status_code == 200:
            data = response.json()
            
            total_hits = data.get('hits', {}).get('total', {}).get('value', 0)
            
            if total_hits > 0:
                hits = data['hits']['hits']
                
                # CORREÇÃO: API pode retornar múltiplos registros (1ª e 2ª instância)
                # Priorizar: 1) Mais movimentos, 2) Não ser Apelação, 3) Ter partes
                print(f"DEBUG: {total_hits} registro(s) encontrado(s). Selecionando o melhor...")
                
                melhor_processo = None
                melhor_score = -1
                
                for i, hit in enumerate(hits):
                    proc = hit.get('_source', {})
                    
                    # Calcular score de prioridade
                    score = 0
                    
                    # Critério 1: Quantidade de movimentos (mais = melhor)
                    qtd_movimentos = len(proc.get('movimentos', []))
                    score += qtd_movimentos * 10
                    
                    # Critério 2: Evitar classes de 2ª instância
                    classe = proc.get('classe', {}).get('nome', '').lower()
                    classes_evitar = ['apelação', 'apelacao', 'recurso', 'agravo', 'embargos']
                    if not any(c in classe for c in classes_evitar):
                        score += 500  # Bônus grande para 1ª instância
                    
                    # Critério 3: Ter partes (bônus)
                    qtd_partes = len(proc.get('polos', proc.get('partes', [])))
                    score += qtd_partes * 50
                    
                    # Critério 4: Grau "G1" (1ª instância) vs "G2" (2ª instância)
                    grau = proc.get('grau', '')
                    if grau == 'G1':
                        score += 300
                    elif grau == 'G2':
                        score -= 100
                    
                    print(f"  [{i}] Classe: {classe[:30]}... | Movs: {qtd_movimentos} | Grau: {grau} | Score: {score}")
                    
                    if score > melhor_score:
                        melhor_score = score
                        melhor_processo = proc
                
                if melhor_processo:
                    print(f"DEBUG: Selecionado registro com score {melhor_score}")
                    return melhor_processo, None
                else:
                    # Fallback para o primeiro se nenhum passou
                    return hits[0]['_source'], None
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
        if not lista_polos:
            # Outro fallback: 'polo' (singular)
            polo_singular = dados_api.get('polo')
            if polo_singular:
                lista_polos = [polo_singular] if isinstance(polo_singular, dict) else polo_singular
        
        for polo in lista_polos:
            if not isinstance(polo, dict):
                continue
                
            tipo_polo = polo.get('polo', 'INDEFINIDO') # Ativo/Passivo
            if tipo_polo == 'AT': tipo_polo = 'AUTOR'
            elif tipo_polo == 'PA': tipo_polo = 'REU'
            elif tipo_polo == 'TC': tipo_polo = 'TERCEIRO'
            elif tipo_polo == 'ATIVO': tipo_polo = 'AUTOR'
            elif tipo_polo == 'PASSIVO': tipo_polo = 'REU'
            
            # Lista de partes pode estar em 'partes' ou 'parte'
            partes_polo = polo.get('partes', polo.get('parte', []))
            if not isinstance(partes_polo, list):
                partes_polo = [partes_polo] if partes_polo else []
            
            for parte in partes_polo:
                if not isinstance(parte, dict):
                    continue
                    
                pessoa = parte.get('pessoa', {})
                if not isinstance(pessoa, dict):
                    pessoa = {}
                    
                # Buscar nome em vários lugares
                nome = (pessoa.get('nome') or 
                        parte.get('nome') or 
                        pessoa.get('nomeCompleto') or
                        parte.get('nomeCompleto') or
                        'Nome não informado')
                
                # Buscar CPF/CNPJ em vários lugares
                cpf = (pessoa.get('numeroDocumentoPrincipal') or 
                       pessoa.get('cpfCnpj') or 
                       pessoa.get('cpf') or
                       pessoa.get('cnpj') or
                       parte.get('cpfCnpj') or 
                       parte.get('documento') or
                       '')
                
                # Determinar tipo de pessoa
                tipo_pessoa = 'Física'
                if cpf and len(re.sub(r'\D', '', str(cpf))) > 11:
                    tipo_pessoa = 'Jurídica'
                elif parte.get('tipoPessoa') == 'Jurídica' or pessoa.get('tipoPessoa') == 'Jurídica':
                    tipo_pessoa = 'Jurídica'
                
                partes.append({
                    'nome': nome,
                    'tipo': tipo_polo,
                    'cpf_cnpj': cpf,
                    'tipo_pessoa': tipo_pessoa
                })
                
                # Também capturar advogados se disponíveis
                advogados = parte.get('advogados', parte.get('representantes', []))
                if isinstance(advogados, list):
                    for adv in advogados[:3]:  # Limitar a 3 advogados por parte
                        if isinstance(adv, dict):
                            nome_adv = adv.get('nome', '')
                            if nome_adv:
                                partes.append({
                                    'nome': f"Adv. {nome_adv}",
                                    'tipo': f'ADVOGADO_{tipo_polo}',
                                    'cpf_cnpj': adv.get('inscricao', adv.get('oab', '')),
                                    'tipo_pessoa': 'Física'
                                })
        
        movimentos = []
        # CORREÇÃO: Remover limite de 20, pegar TODOS os movimentos
        for m in dados_api.get('movimentos', []):
            
            # Tentar encontrar a descrição em vários lugares possíveis
            # Estruturas variam muito entre tribunais
            desc = None
            codigo_mov = None
            
            # 1. Estrutura Padrão (Nested)
            mov_obj = m.get('movimento')
            if isinstance(mov_obj, dict):
                desc = mov_obj.get('nome')
                codigo_mov = mov_obj.get('codigo')
                if not desc:
                    desc = mov_obj.get('movimentoLocal', {}).get('nome')
                    if not codigo_mov:
                        codigo_mov = mov_obj.get('movimentoLocal', {}).get('codigo')
                if not desc:
                    desc = mov_obj.get('movimentoNacional', {}).get('nome')
                    if not codigo_mov:
                        codigo_mov = mov_obj.get('movimentoNacional', {}).get('codigo')
            
            # 2. Estrutura Plana (Alguns TJs)
            if not desc:
                mov_local = m.get('movimentoLocal', {})
                if isinstance(mov_local, dict):
                    desc = mov_local.get('nome')
                    codigo_mov = mov_local.get('codigo') or codigo_mov
            if not desc:
                mov_nac = m.get('movimentoNacional', {})
                if isinstance(mov_nac, dict):
                    desc = mov_nac.get('nome')
                    codigo_mov = mov_nac.get('codigo') or codigo_mov
            if not desc:
                desc = m.get('nome') # Eventualmente o nome está na raiz
            if not desc:
                desc = m.get('descricao')
            
            # 3. Tentar extrair de 'tipoDocumento' (comum em alguns tribunais)
            tipo_doc = m.get('tipoDocumento', {})
            if isinstance(tipo_doc, dict) and tipo_doc.get('nome'):
                if not desc or desc == "Movimentação sem descrição":
                    desc = tipo_doc.get('nome')
                else:
                    desc = f"{desc} - {tipo_doc.get('nome')}"

            # Fallback final com código
            if not desc:
                if codigo_mov:
                    desc = f"Movimentação Cód. {codigo_mov}"
                else:
                    desc = "Movimentação processual"

            # Complementos (Tipo de documento, observações...)
            compl = ""
            for c in m.get('complementosTabelados', []):
                 # CORREÇÃO: Priorizar 'nome' (valor) sobre 'descricao' (label do campo)
                 c_valor = c.get('nome')
                 if not c_valor:
                     c_valor = c.get('descricao')
                     
                 if c_valor and c_valor not in compl and c_valor not in desc:
                     compl += f" - {c_valor}"
            
            # Observações (Ouro escondido - contém detalhes importantes)
            obs = m.get('observacao')
            if obs and len(obs) > 5:
                compl += f" [Obs: {obs}]"
            
            # Tipo de decisão
            tipo_dec = m.get('tipoDecisao', {})
            if isinstance(tipo_dec, dict) and tipo_dec.get('nome'):
                compl += f" ({tipo_dec.get('nome')})"

            movimentos.append({
                'data': m.get('dataHora', ''),
                'descricao': f"{desc}{compl}".strip(),
                'complemento': compl.strip(),
                'codigo': codigo_mov
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

        # Enriquecer movimentos para IA
        movimentos_enriquecidos = enriquecer_movimentos_lista(movimentos)
        
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
            'movimentos_enriquecidos': movimentos_enriquecidos,  # Para IA
            'flags_processo': movimentos_enriquecidos.get('flags_encontradas', []),
            'gatilho_financeiro': movimentos_enriquecidos.get('gatilho_financeiro', False),
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
        # Distribuição -> Nova fase "Distribuído"
        'Distribuição': 'Distribuído',
    }
    
    # Default para "Distribuído" para processos recém-criados
    return mapeamentos.get(classe, 'Distribuído')

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
                    
                    # --- ALTERAÇÃO: ANÁLISE AUTOMÁTICA DESATIVADA ---
                    # Motivo: Evitar erro 429 (Quota Exceeded) na API Gemini
                    # A análise agora é sob demanda (botão na interface)
                    
                    # analise = ai.analisar_andamento(mov['descricao'], contexto, nome_cliente)
                    # analise_json = json.dumps(analise, ensure_ascii=False)
                    # urgente = 1 if analise.get('urgente') else 0
                    
                    # Placeholders para inserção sem IA
                    analise_json = None
                    urgente = 0
                    
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
                        
                        analisados += 0 # Não contamos como analisado pois foi apenas salvo

                    except Exception as e_ins:
                        print(f"Erro ao salvar movimento: {e_ins}")
                        pass
            
            conn.commit()
            
        return {"novos": novos, "analisados": analisados}
    except Exception as e:
        return {"erro": str(e)}
